"""Participant workspace: lobby, synchronised answers, hints, breaks and monitoring."""
from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import Actor, require_participant
from ..models import (
    AnswerHistory, Announcement, CompetitionRound, MemeContent, Participant, Question,
    Riddle, RiddleAttempt, Score, Team, TeamAccessCode, TeamAnswer, TeamRoundSession,
    Violation, utcnow,
)
from ..realtime import hub
from ..security import rate_limiter
from ..services.core import (
    audit, build_scoreboard, complete_session, score_session, serialize_team,
    serialize_question, setting, settings_map,
)
from ..services.rounds import participant_state

router = APIRouter(prefix="/api/participant", tags=["participant"])


class CodePayload(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class AnswerPayload(BaseModel):
    selected_index: int = Field(ge=0, le=3)


class ViolationPayload(BaseModel):
    kind: Literal["tab_hidden", "window_blur", "fullscreen_exit", "multi_session"]
    detail: str = Field(default="", max_length=300)


class GuessPayload(BaseModel):
    guess: str = Field(min_length=1, max_length=200)


def _team(db: Session, actor: Actor) -> Team:
    team = db.get(Team, actor.record.team_id)
    if not team:
        raise HTTPException(status_code=403, detail="No linked team")
    return team


def _active_session(db: Session, team_id: int) -> tuple[CompetitionRound, TeamRoundSession]:
    r = db.scalar(select(CompetitionRound).where(CompetitionRound.status.in_(["active", "paused"])))
    if not r:
        raise HTTPException(status_code=409, detail="No round is currently active")
    s = db.scalar(
        select(TeamRoundSession).options(selectinload(TeamRoundSession.answers))
        .where(TeamRoundSession.team_id == team_id, TeamRoundSession.round_id == r.id)
    )
    if not s:
        raise HTTPException(status_code=403, detail="Your team is not eligible for this round")
    if s.status not in ("active", "paused") or s.disqualified:
        raise HTTPException(status_code=409, detail="Your team's round session is closed")
    return r, s


@router.get("/me")
def participant_me(db: Session = Depends(get_db), actor: Actor = Depends(require_participant)):
    team = _team(db, actor)
    rounds = db.scalars(select(CompetitionRound).order_by(CompetitionRound.id)).all()
    sessions = list(db.scalars(
        select(TeamRoundSession).where(TeamRoundSession.team_id == team.id)
    ))
    return {
        "participant": {
            "id": actor.id, "full_name": actor.record.full_name,
            "email": actor.record.email, "role": actor.record.role,
            "confirmed": bool(actor.record.confirmed_at),
        },
        "team": serialize_team(db, team),
        "rounds": [{
            "id": r.id, "name": r.short_name, "status": r.status,
            "session_status": next((s.status for s in sessions if s.round_id == r.id), "not_eligible"),
        } for r in rounds],
        "competition": {
            "current_round": next((r.id for r in rounds if r.status in ("active", "paused")), None),
            "status": next((r.status for r in rounds if r.status in ("active", "paused")), "waiting"),
        },
    }


@router.post("/lobby")
async def join_lobby(payload: CodePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_participant)):
    team = _team(db, actor)
    key = f"code:{actor.id}"
    if not rate_limiter.check(key, limit=8):
        raise HTTPException(status_code=429, detail="Too many code attempts. Wait a minute and try again.")
    code = payload.code.strip().upper()
    row = db.scalar(select(TeamAccessCode).where(TeamAccessCode.code == code))
    if not row or row.team_id != team.id:
        audit(db, "team.code.invalid", "participant", actor.id, "team", team.id,
              {"submitted_code": code[:4] + "***"})
        db.commit()
        raise HTTPException(status_code=403, detail="This access code is not valid for your team")
    if row.revoked_at:
        raise HTTPException(status_code=403, detail="This access code has been revoked")
    if row.expires_at and row.expires_at <= utcnow():
        raise HTTPException(status_code=403, detail="This access code has expired")
    if team.status != "approved" or not all(p.confirmed_at for p in team.members) or len(team.members) != 2:
        raise HTTPException(status_code=403, detail="Your team must be fully confirmed and approved before joining")
    row.last_used_at = utcnow()
    row.failed_attempts = 0
    audit(db, "lobby.joined", "participant", actor.id, "team", team.id)
    db.commit()
    return {"ok": True, "joined": True, "team_id": team.id, "state": participant_state(db, team.id, actor.id)}


@router.get("/state")
def get_state(db: Session = Depends(get_db), actor: Actor = Depends(require_participant)):
    return participant_state(db, actor.record.team_id, actor.id)


@router.put("/answers/{question_id}")
async def save_answer(
    question_id: str, payload: AnswerPayload,
    db: Session = Depends(get_db), actor: Actor = Depends(require_participant),
):
    r, session = _active_session(db, actor.record.team_id)
    if r.status == "paused":
        raise HTTPException(status_code=409, detail="The round is paused")
    if question_id not in (r.question_ids or []):
        raise HTTPException(status_code=404, detail="Question not found in this round")
    answer = next((a for a in session.answers if a.question_id == question_id), None)
    if answer and answer.submitted:
        raise HTTPException(status_code=409, detail="This answer has already been submitted")
    if not answer:
        answer = TeamAnswer(session_id=session.id, question_id=question_id)
        db.add(answer)
        session.answers.append(answer)
    previous = answer.selected_index
    answer.selected_index = payload.selected_index
    answer.updated_at = utcnow()
    db.add(AnswerHistory(
        session_id=session.id, question_id=question_id, actor_id=actor.id,
        action="autosave", previous_index=previous, new_index=payload.selected_index,
    ))
    db.commit()
    await hub.notify_team(actor.record.team_id, "answer.updated", {
        "question_id": question_id, "selected_index": payload.selected_index,
        "submitted": False, "by": actor.name, "round_id": r.id,
    })
    return {"ok": True, "selected_index": payload.selected_index}


@router.post("/answers/{question_id}/submit")
async def submit_answer(
    question_id: str, payload: AnswerPayload,
    db: Session = Depends(get_db), actor: Actor = Depends(require_participant),
):
    r, session = _active_session(db, actor.record.team_id)
    if r.status == "paused":
        raise HTTPException(status_code=409, detail="The round is paused")
    if question_id not in (r.question_ids or []):
        raise HTTPException(status_code=404, detail="Question not found in this round")
    answer = next((a for a in session.answers if a.question_id == question_id), None)
    if answer and answer.submitted:
        raise HTTPException(status_code=409, detail="This answer was already submitted by your team")
    if not answer:
        answer = TeamAnswer(session_id=session.id, question_id=question_id)
        db.add(answer)
        session.answers.append(answer)
    previous = answer.selected_index
    answer.selected_index = payload.selected_index
    answer.submitted = True
    answer.submitted_at = utcnow()
    answer.submitted_by_id = actor.id
    db.add(AnswerHistory(
        session_id=session.id, question_id=question_id, actor_id=actor.id,
        action="submit", previous_index=previous, new_index=payload.selected_index,
    ))
    score_session(db, session)
    db.commit()
    await hub.notify_team(actor.record.team_id, "answer.submitted", {
        "question_id": question_id, "selected_index": payload.selected_index,
        "by": actor.name, "round_id": r.id,
    })
    await hub.broadcast("scoreboard.updated", {"round_id": r.id, "team_id": actor.record.team_id}, channel="administrator")
    return {"ok": True, "submitted": True}


@router.post("/hints/{question_id}")
def use_hint(question_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_participant)):
    if not setting(db, "hints_enabled", True):
        raise HTTPException(status_code=403, detail="Hints are disabled for this competition")
    r, session = _active_session(db, actor.record.team_id)
    if question_id not in (r.question_ids or []):
        raise HTTPException(status_code=404, detail="Question not found in this round")
    q = db.get(Question, question_id)
    answer = next((a for a in session.answers if a.question_id == question_id), None)
    if not answer:
        answer = TeamAnswer(session_id=session.id, question_id=question_id, hint_count=0, submitted=False)
        db.add(answer)
        session.answers.append(answer)
    mode = setting(db, "hint_mode", "once")
    used = answer.hint_count or 0
    if mode == "once" and used >= 1:
        raise HTTPException(status_code=409, detail="Only one hint is available for this question")
    answer.hint_count = used + 1
    answer.hint_used = True
    if answer.submitted:
        score_session(db, session)
    db.commit()
    return {
        "hint": q.hint.text if q.hint else "",
        "hint_count": answer.hint_count,
        "hint_cost": int(setting(db, "hint_cost_marks", 0)) * answer.hint_count,
    }


@router.post("/violations")
async def report_violation(
    payload: ViolationPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_participant),
):
    team_id = actor.record.team_id
    active = db.scalar(select(TeamRoundSession).where(
        TeamRoundSession.team_id == team_id, TeamRoundSession.status.in_(["active", "paused"])
    ))
    threshold = int(setting(db, "violation_threshold", 3))
    count = (active.violation_count + 1) if active else 1
    action = "warning" if count == 1 else "final_warning" if count < threshold else "auto_submit"
    if count >= threshold and not setting(db, "violation_auto_submit", True):
        action = "review"
    v = Violation(
        session_id=active.id if active else None, participant_id=actor.id,
        team_id=team_id, round_id=active.round_id if active else None,
        kind=payload.kind, detail=payload.detail, action_taken=action,
        reviewed=False,
    )
    db.add(v)
    if active:
        active.violation_count = count
        if action == "auto_submit":
            complete_session(db, active, auto=True)
            active.review_required = True
    audit(db, "violation.recorded", "participant", actor.id, "team", team_id,
          {"kind": payload.kind, "count": count, "action": action})
    db.commit()
    await hub.broadcast("violation.alert", {
        "team_id": team_id, "team_name": _team(db, actor).name, "count": count,
        "kind": payload.kind, "action": action,
    }, channel="administrator")
    if active:
        await hub.notify_team(team_id, "violation.warning", {
            "count": count, "threshold": threshold, "action": action,
        })
        await hub.broadcast("scoreboard.updated", {"team_id": team_id}, channel="administrator")
    return {"count": count, "threshold": threshold, "action": action}


@router.get("/break")
def break_content(db: Session = Depends(get_db), actor: Actor = Depends(require_participant)):
    if not setting(db, "break_enabled", True):
        return {"enabled": False}
    ended = db.scalars(select(CompetitionRound).where(
        CompetitionRound.status == "ended", CompetitionRound.id < 4
    ).order_by(CompetitionRound.id.desc())).first()
    if not ended:
        return {"enabled": True, "riddle": None, "memes": [], "message": "The next round begins shortly."}
    slot = ended.id
    riddle = db.scalar(select(Riddle).where(Riddle.is_active.is_(True)).order_by(Riddle.id))
    all_riddles = list(db.scalars(select(Riddle).where(Riddle.is_active.is_(True)).order_by(Riddle.id)))
    if all_riddles:
        riddle = all_riddles[(slot - 1) % len(all_riddles)]
    memes = list(db.scalars(select(MemeContent).where(
        MemeContent.is_enabled.is_(True)
    ).order_by(MemeContent.id).limit(3)))
    reveal_at = (ended.ended_at or utcnow()) + timedelta(seconds=riddle.duration_seconds if riddle else 300)
    attempt = db.scalar(select(RiddleAttempt).where(
        RiddleAttempt.team_id == actor.record.team_id,
        RiddleAttempt.riddle_id == riddle.id if riddle else False,
        RiddleAttempt.slot == slot,
    ))
    return {
        "enabled": True,
        "slot": slot,
        "riddle": {
            "id": riddle.id, "category": riddle.category, "question": riddle.question,
            "duration_seconds": riddle.duration_seconds,
            "reveal_at": reveal_at.isoformat(),
            "answer": riddle.answer if reveal_at <= utcnow() else None,
            "explanation": riddle.explanation if reveal_at <= utcnow() else None,
            "your_guess": attempt.guess if attempt else None,
            "correct": attempt.is_correct if attempt else None,
        } if riddle else None,
        "memes": [{"id": m.id, "title": m.title, "category": m.category, "top": m.top,
                   "bottom": m.bottom, "theme": m.theme, "glyph": m.glyph,
                   "image_url": m.image_url} for m in memes],
    }


@router.post("/riddle/{riddle_id}/guess")
def guess_riddle(
    riddle_id: str, payload: GuessPayload, db: Session = Depends(get_db),
    actor: Actor = Depends(require_participant),
):
    riddle = db.get(Riddle, riddle_id)
    if not riddle or not riddle.is_active:
        raise HTTPException(status_code=404, detail="Riddle not found")
    ended = db.scalars(select(CompetitionRound).where(
        CompetitionRound.status == "ended", CompetitionRound.id < 4
    ).order_by(CompetitionRound.id.desc())).first()
    if not ended:
        raise HTTPException(status_code=409, detail="No break is active")
    reveal_at = (ended.ended_at or utcnow()) + timedelta(seconds=riddle.duration_seconds)
    if reveal_at <= utcnow():
        raise HTTPException(status_code=409, detail="This riddle has been revealed")
    guess = payload.guess.strip().lower()
    correct = guess == riddle.answer.strip().lower() or (
        len(guess) > 2 and guess in riddle.answer.strip().lower()
    )
    bonus = 0
    attempt = db.scalar(select(RiddleAttempt).where(
        RiddleAttempt.riddle_id == riddle_id,
        RiddleAttempt.team_id == actor.record.team_id,
        RiddleAttempt.slot == ended.id,
    ))
    if not attempt:
        attempt = RiddleAttempt(
            riddle_id=riddle_id, team_id=actor.record.team_id, slot=ended.id,
            guess=payload.guess.strip(), is_correct=correct,
        )
        db.add(attempt)
        if correct:
            bonus = int(setting(db, "riddle_bonus_marks", 0))
            attempt.awarded_marks = bonus
            score = db.scalar(select(Score).where(
                Score.team_id == actor.record.team_id, Score.round_id == ended.id
            ))
            if score and bonus:
                score.marks += bonus
    audit(db, "riddle.guess", "participant", actor.id, "riddle", riddle_id, {"correct": correct})
    db.commit()
    return {"correct": correct, "bonus_marks": bonus}


@router.get("/results")
def own_results(db: Session = Depends(get_db), actor: Actor = Depends(require_participant)):
    cfg = settings_map(db)
    if not cfg.get("results_published") and not cfg.get("participant_score_visibility"):
        return {"available": False, "message": "Results have not been published yet."}
    team_id = actor.record.team_id
    rows = [r for r in build_scoreboard(db) if r["team_id"] == team_id]
    return {"available": True, "results": rows[0] if rows else None}


@router.get("/announcements")
def announcements(db: Session = Depends(get_db), actor: Actor = Depends(require_participant)):
    rows = db.scalars(select(Announcement).where(
        Announcement.is_active.is_(True),
        Announcement.audience.in_(["all", "participants"]),
    ).order_by(Announcement.created_at.desc()).limit(20))
    return [{"id": a.id, "title": a.title, "body": a.body,
             "created_at": a.created_at.isoformat()} for a in rows]
