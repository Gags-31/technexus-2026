"""Organiser dashboard APIs: registrations, teams, questions, content and settings."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import Actor, client_ip, require_full_admin
from ..models import (
    Administrator, Announcement, AuditLog, MemeContent, Participant, Question,
    QuestionCorrectAnswer, QuestionExplanation, QuestionHint, QuestionOption, Riddle,
    Score, Team, TeamAccessCode, TeamRoundSession, utcnow,
)
from ..realtime import hub
from ..security import hash_password, new_team_code, password_strength
from ..services.core import (
    audit, build_scoreboard, serialize_question, serialize_team, set_setting, settings_map,
)
from ..services.rounds import rounds_overview

router = APIRouter(prefix="/api/admin", tags=["administrator"])


# --------------------------------------------------------------------------- overview
@router.get("/overview")
def overview(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    teams = list(db.scalars(select(Team).options(selectinload(Team.members))))
    participants = list(db.scalars(select(Participant)))
    sessions = list(db.scalars(select(TeamRoundSession)))
    from ..models import Violation
    violations = db.scalar(select(func.count(Violation.id))) or 0
    cfg = settings_map(db)
    return {
        "totals": {
            "teams": len(teams),
            "participants": len(participants),
            "approved_teams": sum(1 for t in teams if t.status == "approved"),
            "pending_teams": sum(1 for t in teams if t.status in ("pending", "confirmed")),
            "rejected_teams": sum(1 for t in teams if t.status == "rejected"),
            "active_teams": len({s.team_id for s in sessions if s.status in ("active", "paused")}),
            "completed_sessions": sum(1 for s in sessions if s.status in ("submitted", "auto_submitted")),
            "violations": violations,
            "open_violations": db.scalar(select(func.count(Violation.id)).where(Violation.reviewed.is_(False))) or 0,
        },
        "current_round": next((r["id"] for r in rounds_overview(db) if r["status"] in ("active", "paused")), None),
        "competition_status": next((r["status"] for r in rounds_overview(db) if r["status"] in ("active", "paused")), "waiting"),
        "event": {
            "date": cfg.get("event_date"), "start_time": cfg.get("event_start_time"),
            "schedule": cfg.get("schedule", []),
        },
        "live_connections": len(hub.active_team_ids()),
        "admin_connections": hub.admin_connections(),
        "rounds": rounds_overview(db),
    }


# --------------------------------------------------------------------------- registrations
@router.get("/registrations")
def registrations(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    teams = db.scalars(select(Team).options(
        selectinload(Team.members), selectinload(Team.registration), selectinload(Team.access_code)
    )).all()
    return [serialize_team(db, t) | {
        "submitted_at": t.registration.submitted_at.isoformat() if t.registration else None,
        "decision": t.registration.decision if t.registration else None,
        "notes": t.registration.notes if t.registration else "",
    } for t in teams]


class Decision(BaseModel):
    notes: str = Field(default="", max_length=500)
    force: bool = False


@router.post("/registrations/{team_id}/approve")
async def approve_registration(
    team_id: int, payload: Decision, actor: Actor = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if len(team.members) != 2:
        raise HTTPException(status_code=409, detail="A team must have exactly two members before approval")
    if not all(p.confirmed_at for p in team.members):
        if not payload.force:
            raise HTTPException(
                status_code=409,
                detail="Both members must confirm before approval. Use the organiser override to approve anyway.",
            )
        for participant in team.members:
            if not participant.confirmed_at:
                participant.confirmed_at = utcnow()
        audit(db, "registration.admin_confirmed", "administrator", actor.id, "team", team_id,
              {"members": len(team.members)})
    team.status = "approved"
    team.approved_at = utcnow()
    team.approved_by_id = actor.id
    if team.registration:
        team.registration.decision = "approved"
        team.registration.notes = payload.notes
        team.registration.reviewed_by_id = actor.id
        team.registration.reviewed_at = utcnow()
    audit(db, "registration.approved", "administrator", actor.id, "team", team_id)
    db.commit()
    await hub.broadcast("announcement", {"title": "Team approved", "body": f"{team.name} is approved."}, channel="administrator")
    return serialize_team(db, team)


@router.post("/registrations/{team_id}/reject")
async def reject_registration(
    team_id: int, payload: Decision, actor: Actor = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team.status = "rejected"
    if team.registration:
        team.registration.decision = "rejected"
        team.registration.notes = payload.notes
        team.registration.reviewed_by_id = actor.id
        team.registration.reviewed_at = utcnow()
    if team.access_code:
        team.access_code.revoked_at = utcnow()
    audit(db, "registration.rejected", "administrator", actor.id, "team", team_id)
    db.commit()
    return serialize_team(db, team)


# --------------------------------------------------------------------------- teams
@router.get("/teams")
def teams(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    rows = db.scalars(select(Team).options(
        selectinload(Team.members), selectinload(Team.access_code), selectinload(Team.registration)
    )).all()
    return [serialize_team(db, t) for t in rows]


@router.post("/teams/{team_id}/regenerate-code")
def regenerate_code(
    team_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    code = new_team_code()
    while db.scalar(select(TeamAccessCode.id).where(TeamAccessCode.code == code)):
        code = new_team_code()
    row = team.access_code
    if not row:
        row = TeamAccessCode(team_id=team.id, code=code)
        db.add(row)
    else:
        row.code = code
        row.revoked_at = None
        row.failed_attempts = 0
        row.locked_until = None
    from datetime import timedelta
    row.expires_at = utcnow() + timedelta(days=365)
    audit(db, "team.code.regenerated", "administrator", actor.id, "team", team_id, {"code": code})
    db.commit()
    return {"code": code, "team_id": team_id}


@router.post("/teams/{team_id}/revoke-code")
def revoke_code(team_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if not team or not team.access_code:
        raise HTTPException(status_code=404, detail="Team or access code not found")
    team.access_code.revoked_at = utcnow()
    audit(db, "team.code.revoked", "administrator", actor.id, "team", team_id)
    db.commit()
    return {"ok": True}


class TeamPatch(BaseModel):
    model_config = {"extra": "forbid"}
    shortlisted: bool | None = None
    status: Literal["pending", "confirmed", "approved", "rejected", "disqualified"] | None = None
    name: str | None = None
    college: str | None = None
    department: str | None = None
    semester: str | None = None


@router.patch("/teams/{team_id}")
def patch_team(
    team_id: int, payload: TeamPatch, actor: Actor = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    for field in ("shortlisted", "status", "name", "college", "department", "semester"):
        value = getattr(payload, field)
        if value is not None:
            setattr(team, field, value)
    audit(db, "team.updated", "administrator", actor.id, "team", team_id, payload.model_dump())
    db.commit()
    return serialize_team(db, team)


@router.patch("/participants/{participant_id}")
def patch_participant(
    participant_id: int, payload: dict = Body(...), actor: Actor = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    p = db.get(Participant, participant_id)
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    allowed = {"full_name", "email", "mobile", "is_active"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if "email" in updates:
        existing = db.scalar(select(Participant.id).where(Participant.email == updates["email"], Participant.id != p.id))
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")
        updates["email"] = updates["email"].strip().lower()
    if "password" in payload:
        ok, message = password_strength(payload["password"])
        if not ok:
            raise HTTPException(status_code=422, detail=message)
        p.password_hash = hash_password(payload["password"])
    for key, value in updates.items():
        setattr(p, key, value)
    audit(db, "participant.updated", "administrator", actor.id, "participant", participant_id, list(updates))
    db.commit()
    return {"id": p.id, "full_name": p.full_name, "email": p.email, "mobile": p.mobile}


# --------------------------------------------------------------------------- questions
class QuestionPayload(BaseModel):
    id: str | None = None
    domain: Literal["Artificial Intelligence", "Cloud Computing", "Operating Systems", "DBMS"]
    round: int = Field(ge=1, le=4)
    difficulty: Literal["Basic", "Intermediate", "Advanced", "Expert"]
    marks: int = Field(default=10, ge=0, le=100)
    question: str = Field(min_length=5)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=5)
    hint: str = Field(min_length=5)
    reference: str = ""


@router.get("/questions")
def questions(
    domain: str | None = None, round: int | None = None, difficulty: str | None = None,
    search: str | None = None, db: Session = Depends(get_db), _: Actor = Depends(require_full_admin),
):
    query = select(Question).options(
        selectinload(Question.options), selectinload(Question.hint),
        selectinload(Question.explanation), selectinload(Question.correct_answer)
    )
    if domain:
        query = query.where(Question.domain == domain)
    if round:
        query = query.where(Question.round == round)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    rows = list(db.scalars(query.order_by(Question.id)))
    if search:
        needle = search.lower()
        rows = [q for q in rows if needle in (q.statement + q.id).lower()]
    return [serialize_question(q, answers=True) for q in rows]


@router.post("/questions", status_code=201)
def create_question(payload: QuestionPayload, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    qid = payload.id or f"CUSTOM-{int(datetime.now().timestamp())}"
    if db.get(Question, qid):
        raise HTTPException(status_code=409, detail="Question ID already exists")
    q = _write_question(db, qid, payload)
    audit(db, "question.created", "administrator", actor.id, "question", qid)
    db.commit()
    return serialize_question(q, answers=True)


@router.put("/questions/{qid}")
def update_question(
    qid: str, payload: QuestionPayload, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q = _write_question(db, qid, payload, existing=q)
    audit(db, "question.updated", "administrator", actor.id, "question", qid)
    db.commit()
    return serialize_question(q, answers=True)


def _write_question(db: Session, qid: str, payload: QuestionPayload, existing: Question | None = None) -> Question:
    q = existing or Question(id=qid)
    q.domain, q.round, q.difficulty = payload.domain, payload.round, payload.difficulty
    q.marks, q.statement, q.scenario_ref = payload.marks, payload.question, payload.reference
    if existing:
        q.options.clear()
    for position, text in enumerate(payload.options):
        q.options.append(QuestionOption(position=position, text=text, is_correct=position == payload.correct_index))
    if q.hint:
        q.hint.text = payload.hint
    else:
        q.hint = QuestionHint(text=payload.hint)
    if q.explanation:
        q.explanation.text = payload.explanation
    else:
        q.explanation = QuestionExplanation(text=payload.explanation)
    if q.correct_answer:
        q.correct_answer.option_position = payload.correct_index
    else:
        q.correct_answer = QuestionCorrectAnswer(option_position=payload.correct_index)
    if not existing:
        db.add(q)
    db.flush()
    return q


@router.delete("/questions/{qid}")
def delete_question(qid: str, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    q = db.get(Question, qid)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.is_active = False
    audit(db, "question.deactivated", "administrator", actor.id, "question", qid)
    db.commit()
    return {"ok": True}


@router.get("/questions/export.csv")
def export_questions_csv(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    rows = db.scalars(select(Question).options(
        selectinload(Question.options), selectinload(Question.hint),
        selectinload(Question.explanation), selectinload(Question.correct_answer)
    ).order_by(Question.id))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["ID", "Domain", "Round", "Difficulty", "Marks", "Question", "A", "B", "C", "D",
                     "Correct Index", "Correct Option", "Explanation", "Hint", "Reference"])
    for q in rows:
        opts = [o.text for o in sorted(q.options, key=lambda o: o.position)]
        ci = q.correct_answer.option_position if q.correct_answer else -1
        writer.writerow([q.id, q.domain, q.round, q.difficulty, q.marks, q.statement, *opts,
                         ci, opts[ci] if 0 <= ci < 4 else "", q.explanation.text if q.explanation else "",
                         q.hint.text if q.hint else "", q.scenario_ref])
    return Response(buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=technexus-question-bank.csv"})


@router.get("/questions/export.pdf")
def export_questions_pdf(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

    rows = list(db.scalars(select(Question).options(
        selectinload(Question.options), selectinload(Question.hint),
        selectinload(Question.explanation), selectinload(Question.correct_answer)
    ).order_by(Question.id)))
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="TECHNEXUS 2026 - Private Answer Key")
    styles = getSampleStyleSheet()
    story = [Paragraph("TECHNEXUS 2026 - PRIVATE QUESTION BANK &amp; ANSWER KEY", styles["Title"]),
             Paragraph("CONFIDENTIAL - Organisers only. Do not distribute to participants.", styles["Normal"]),
             Spacer(1, 8)]
    for index, q in enumerate(rows):
        opts = sorted(q.options, key=lambda o: o.position)
        ci = q.correct_answer.option_position if q.correct_answer else -1
        story.append(Paragraph(f"<b>{q.id}</b> [{q.domain} | R{q.round} | {q.difficulty} | {q.marks} marks]", styles["Heading4"]))
        story.append(Paragraph(q.statement.replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
        for o in opts:
            marker = "&#10004; " if o.position == ci else ""
            story.append(Paragraph(marker + f"{chr(65 + o.position)}. " + o.text.replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
        story.append(Paragraph("<b>Explanation:</b> " + (q.explanation.text if q.explanation else "").replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
        story.append(Paragraph("<b>Hint:</b> " + (q.hint.text if q.hint else "").replace("<", "&lt;").replace(">", "&gt;"), styles["BodyText"]))
        story.append(Spacer(1, 6))
        if index % 4 == 3:
            story.append(PageBreak())
    doc.build(story)
    buffer.seek(0)
    return Response(buffer.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=technexus-answer-key.pdf"})


# --------------------------------------------------------------------------- settings
@router.get("/settings")
def get_settings(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    return settings_map(db)


@router.patch("/settings")
def patch_settings(
    payload: dict = Body(...), actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    allowed = set(settings_map(db).keys())
    changed = {}
    for key, value in payload.items():
        if key not in allowed:
            raise HTTPException(status_code=422, detail=f"Unknown setting: {key}")
        set_setting(db, key, value, actor.id)
        changed[key] = value
    audit(db, "settings.updated", "administrator", actor.id, "competition_settings", "", changed)
    db.commit()
    return settings_map(db)


# --------------------------------------------------------------------------- announcements
@router.get("/announcements")
def get_announcements(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    rows = db.scalars(select(Announcement).order_by(Announcement.created_at.desc()))
    return [{"id": a.id, "title": a.title, "body": a.body, "audience": a.audience,
             "active": a.is_active, "created_at": a.created_at.isoformat()} for a in rows]


class AnnouncementPayload(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=2)
    audience: Literal["all", "participants", "administrators"] = "all"
    is_active: bool = True


@router.post("/announcements", status_code=201)
async def create_announcement(
    payload: AnnouncementPayload, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    a = Announcement(**payload.model_dump(), created_by_id=actor.id)
    db.add(a)
    audit(db, "announcement.created", "administrator", actor.id, "announcement", 0, {"title": payload.title})
    db.commit()
    if payload.audience in ("all", "participants"):
        await hub.broadcast("announcement", {"title": payload.title, "body": payload.body}, channel="participant")
    return {"id": a.id, "title": a.title, "body": a.body}


@router.patch("/announcements/{announcement_id}")
def patch_announcement(announcement_id: int, payload: dict, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    a = db.get(Announcement, announcement_id)
    if not a:
        raise HTTPException(status_code=404, detail="Announcement not found")
    for key in ("title", "body", "audience", "is_active"):
        if key in payload:
            setattr(a, key, payload[key])
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- riddles & memes
@router.get("/riddles")
def get_riddles(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    return [{"id": r.id, "category": r.category, "question": r.question, "answer": r.answer,
             "explanation": r.explanation, "active": r.is_active,
             "duration_seconds": r.duration_seconds} for r in db.scalars(select(Riddle))]


class RiddlePayload(BaseModel):
    id: str | None = None
    category: str
    question: str
    answer: str
    explanation: str = ""
    duration_seconds: int = 300
    is_active: bool = True


@router.post("/riddles", status_code=201)
def create_riddle(payload: RiddlePayload, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    rid = payload.id or f"CR{int(datetime.now().timestamp())}"
    if db.get(Riddle, rid):
        raise HTTPException(status_code=409, detail="Riddle ID exists")
    db.add(Riddle(id=rid, **payload.model_dump(exclude={"id"})))
    audit(db, "riddle.created", "administrator", actor.id, "riddle", rid)
    db.commit()
    return {"id": rid}


@router.put("/riddles/{rid}")
def update_riddle(rid: str, payload: RiddlePayload, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    r = db.get(Riddle, rid)
    if not r:
        raise HTTPException(status_code=404, detail="Riddle not found")
    for key, value in payload.model_dump(exclude={"id"}).items():
        setattr(r, key, value)
    db.commit()
    return {"ok": True}


@router.get("/memes")
def get_memes(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    return [{"id": m.id, "title": m.title, "category": m.category, "top": m.top, "bottom": m.bottom,
             "theme": m.theme, "glyph": m.glyph, "image_url": m.image_url,
             "scheduled_slot": m.scheduled_slot, "enabled": m.is_enabled}
            for m in db.scalars(select(MemeContent))]


class MemePayload(BaseModel):
    id: str | None = None
    title: str
    category: str
    top: str
    bottom: str
    theme: str = "cyan"
    glyph: str = "💡"
    image_url: str = ""
    scheduled_slot: int | None = None
    is_enabled: bool = True


@router.post("/memes", status_code=201)
def create_meme(payload: MemePayload, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    mid = payload.id or f"CM{int(datetime.now().timestamp())}"
    if db.get(MemeContent, mid):
        raise HTTPException(status_code=409, detail="Meme ID exists")
    db.add(MemeContent(id=mid, **payload.model_dump(exclude={"id"})))
    audit(db, "meme.created", "administrator", actor.id, "meme", mid)
    db.commit()
    return {"id": mid}


@router.put("/memes/{mid}")
def update_meme(mid: str, payload: MemePayload, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    m = db.get(MemeContent, mid)
    if not m:
        raise HTTPException(status_code=404, detail="Meme not found")
    for key, value in payload.model_dump(exclude={"id"}).items():
        setattr(m, key, value)
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- results, audit
@router.get("/results")
def results(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    return {"rows": build_scoreboard(db), "published": settings_map(db).get("results_published", False)}


@router.post("/results/publish")
async def publish_results(actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db)):
    set_setting(db, "results_published", True, actor.id)
    audit(db, "results.published", "administrator", actor.id, "competition_settings", "results_published")
    db.commit()
    await hub.broadcast("results.published", {"published": True}, channel="participant")
    return {"ok": True}


def _scoreboard_csv(rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Rank", "Team", "Public ID", "College", "R1", "R2", "R3", "R4", "Total",
                     "Correct", "Incorrect", "Unanswered", "Status", "Active", "Submission Time", "Pending Review"])
    for r in rows:
        writer.writerow([
            r["rank"], r["team_name"], r["public_id"], r["college"],
            *[r["rounds"][str(i)]["score"] for i in (1, 2, 3, 4)],
            r["total"], r["correct"], r["incorrect"], r["unanswered"],
            "completed" if r["completed"] else "in_progress", "yes" if r["active"] else "no",
            r["submission_time"] or "", "yes" if r["pending_review"] else "no",
        ])
    return buffer.getvalue()


@router.get("/export/scoreboard.csv")
def export_scoreboard_csv(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    return Response(_scoreboard_csv(build_scoreboard(db)), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=technexus-scoreboard.csv"})


@router.get("/export/scoreboard.pdf")
def export_scoreboard_pdf(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    rows = build_scoreboard(db)
    data = [["Rank", "Team", "R1", "R2", "R3", "R4", "Total", "Correct", "Wrong", "Unanswered", "Status"]]
    for r in rows:
        data.append([r["rank"], r["team_name"], *[r["rounds"][str(i)]["score"] for i in (1, 2, 3, 4)],
                     r["total"], r["correct"], r["incorrect"], r["unanswered"],
                     "Complete" if r["completed"] else "In progress"])
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1b33")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    doc.build([Paragraph("TECHNEXUS 2026 - OFFICIAL RESULTS", getSampleStyleSheet()["Title"]), table])
    buffer.seek(0)
    return Response(buffer.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=technexus-results.pdf"})


@router.get("/audit-logs")
def audit_logs(limit: int = Query(default=200, le=1000), db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return [{"id": r.id, "actor_type": r.actor_type, "actor_id": r.actor_id, "action": r.action,
             "target_type": r.target_type, "target_id": r.target_id, "metadata": r.details,
             "created_at": r.created_at.isoformat(), "ip": r.ip} for r in rows]
