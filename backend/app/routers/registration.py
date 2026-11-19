"""Two-member team registration with separate accounts and unique access codes."""
from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import Actor, client_ip, require_participant
from ..models import (
    Participant, Registration, Team, TeamAccessCode, TeamMembership, utcnow,
)
from ..security import (
    hash_password, new_public_team_id, new_team_code, password_strength,
    rate_limiter, valid_email, valid_mobile,
)
from ..services.core import audit, serialize_team, setting

router = APIRouter(prefix="/api/registration", tags=["registration"])


class Person(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(max_length=255)
    mobile: str = Field(max_length=32)
    password: str = Field(min_length=10, max_length=200)


class TeamRegistration(BaseModel):
    """Exactly two members: one leader and one member. Extra fields are rejected."""
    model_config = ConfigDict(extra="forbid")
    team_name: str = Field(min_length=2, max_length=120)
    college: str = Field(min_length=2, max_length=200)
    department: str = Field(min_length=2, max_length=120)
    semester: str = Field(min_length=1, max_length=32)
    leader: Person
    member: Person


def _validate_person(person: Person, label: str) -> str:
    email = person.email.strip().lower()
    if not valid_email(email):
        raise HTTPException(status_code=422, detail=f"{label}: invalid email address")
    if not valid_mobile(person.mobile.strip()):
        raise HTTPException(status_code=422, detail=f"{label}: invalid mobile number")
    ok, message = password_strength(person.password)
    if not ok:
        raise HTTPException(status_code=422, detail=f"{label}: {message}")
    return email


@router.post("", status_code=201)
def register_team(payload: TeamRegistration, request: Request, db: Session = Depends(get_db)):
    if not setting(db, "registration_open", True):
        raise HTTPException(status_code=403, detail="Registration is currently closed")
    if not rate_limiter.check(f"register:{client_ip(request)}", limit=6):
        raise HTTPException(status_code=429, detail="Too many registration attempts")

    leader_email = _validate_person(payload.leader, "Team leader")
    member_email = _validate_person(payload.member, "Team member")
    if leader_email == member_email:
        raise HTTPException(status_code=422, detail="Leader and member must use different email addresses")

    existing = db.scalars(
        select(Participant.email).where(Participant.email.in_([leader_email, member_email]))
    ).all()
    if existing:
        raise HTTPException(status_code=409, detail="An account with one of these emails already exists")

    max_id = db.scalar(select(func.max(Team.id))) or 0
    public_id = new_public_team_id(max_id + 1)
    while db.scalar(select(Team.id).where(Team.public_id == public_id)):
        max_id += 1
        public_id = new_public_team_id(max_id + 1)

    team = Team(
        public_id=public_id, name=payload.team_name.strip(), college=payload.college.strip(),
        department=payload.department.strip(), semester=payload.semester.strip(), status="pending",
    )
    db.add(team)
    db.flush()

    for person, email, role in (
        (payload.leader, leader_email, "leader"), (payload.member, member_email, "member")
    ):
        participant = Participant(
            team_id=team.id, full_name=person.full_name.strip(), email=email,
            mobile=person.mobile.strip(), password_hash=hash_password(person.password), role=role,
        )
        db.add(participant)
        db.flush()
        db.add(TeamMembership(team_id=team.id, participant_id=participant.id, role=role))
        if role == "leader":
            leader_id = participant.id

    code = new_team_code()
    while db.scalar(select(TeamAccessCode.id).where(TeamAccessCode.code == code)):
        code = new_team_code()
    db.add(TeamAccessCode(
        team_id=team.id, code=code, expires_at=utcnow() + timedelta(days=365),
    ))
    db.add(Registration(team_id=team.id, submitted_by_id=leader_id, decision="pending"))
    audit(db, "registration.created", "participant", leader_id, "team", team.id,
          {"public_id": public_id, "ip": client_ip(request)})
    db.commit()
    db.refresh(team)
    return {
        "ok": True,
        "message": "Team registered. Both members must sign in and confirm participation.",
        "team": serialize_team(db, team),
    }


@router.post("/confirm")
def confirm_participation(actor: Actor = Depends(require_participant), db: Session = Depends(get_db)):
    participant = actor.record
    if participant.confirmed_at:
        return {"ok": True, "message": "Participation already confirmed"}
    participant.confirmed_at = utcnow()
    team = db.get(Team, participant.team_id)
    if team and team.status == "pending":
        members = db.scalars(
            select(Participant).where(Participant.team_id == team.id)
        ).all()
        if len(members) == 2 and all(m.confirmed_at for m in members):
            team.status = "confirmed"
    audit(db, "registration.confirmed", "participant", participant.id, "team", participant.team_id)
    db.commit()
    return {"ok": True, "message": "Participation confirmed"}
