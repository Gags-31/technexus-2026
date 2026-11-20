"""Server-authoritative round lifecycle. All transitions are admin-only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    AnswerHistory, AuditLog, CompetitionRound, Question, RiddleAttempt, Score,
    Team, TeamAnswer, TeamRoundSession, Violation, utcnow,
)
from .core import audit, complete_session, round_summary, set_setting, settings_map


class RoundError(HTTPException):
    pass


def eligible_teams(db: Session, round_id: int, cfg: dict[str, Any] | None = None) -> list[Team]:
    cfg = cfg or settings_map(db)
    teams = list(db.scalars(
        select(Team).options(selectinload(Team.members)).where(Team.status == "approved")
    ).all())
    teams = [t for t in teams if len(t.members) == 2 and all(p.confirmed_at for p in t.members)]
    if round_id == 4 and cfg.get("final_shortlist_enabled", True):
        teams = [t for t in teams if t.shortlisted]
    return teams


def round_with_counts(db: Session, r: CompetitionRound) -> dict[str, Any]:
    data = round_summary(r)
    sessions = list(db.scalars(
        select(TeamRoundSession).where(TeamRoundSession.round_id == r.id)
    ))
    data.update({
        "registered_teams": len(eligible_teams(db, r.id)),
        "active_teams": sum(1 for s in sessions if s.status in ("active", "paused")),
        "completed_teams": sum(1 for s in sessions if s.status in ("submitted", "auto_submitted")),
        "total_sessions": len(sessions),
    })
    return data


def rounds_overview(db: Session) -> list[dict[str, Any]]:
    rounds = db.scalars(select(CompetitionRound).order_by(CompetitionRound.id)).all()
    return [round_with_counts(db, r) for r in rounds]


def reset_event_state(db: Session, admin_id: int) -> dict[str, Any]:
    """Return the event to a clean pre-competition state without deleting registrations.

    Teams, participants, questions, riddles, memes, settings and audit history are
    preserved. Runtime data (answers, scores, violations, break guesses and all
    round clocks) is removed so the event can be run again from Round 1.
    """
    # Order matters: scores reference sessions and violations reference sessions.
    for model in (
        AnswerHistory, TeamAnswer, Score, Violation, RiddleAttempt, TeamRoundSession,
    ):
        db.query(model).delete(synchronize_session=False)

    for r in db.scalars(select(CompetitionRound)):
        r.status = "locked"
        r.server_start_at = None
        r.ends_at = None
        r.paused_at = None
        r.paused_seconds = 0
        r.question_ids = []
        r.started_by_id = None
        r.ended_at = None

    for team in db.scalars(select(Team)):
        team.shortlisted = False

    set_setting(db, "results_published", False, admin_id)
    audit(
        db, "event.reset", "administrator", admin_id,
        "event", "all", {"rounds": 4, "scope": "runtime_state"},
    )
    db.commit()
    return {"reset": True, "rounds": rounds_overview(db)}


def restart_event(db: Session, admin_id: int) -> dict[str, Any]:
    """Reset runtime state, then immediately launch Round 1 with a fresh clock."""
    reset_event_state(db, admin_id)
    state = start_round(db, 1, admin_id)
    audit(db, "event.restarted", "administrator", admin_id, "event", "all", {"round_id": 1})
    db.commit()
    return state


def pick_questions(db: Session, round_id: int, count: int) -> list[str]:
    rows = list(db.scalars(
        select(Question).where(Question.is_active.is_(True), Question.round == round_id)
    ).all())
    # Rotate domains so every team receives a balanced paper in an identical order.
    domains = ["Artificial Intelligence", "Cloud Computing", "Operating Systems", "DBMS"]
    ordered: list[Question] = []
    for domain in domains:
        ordered.extend(sorted([q for q in rows if q.domain == domain], key=lambda q: q.id))
    selected = [q.id for q in ordered[:count]]
    if len(selected) < count:
        raise RoundError(status_code=409, detail=f"Not enough active questions for round {round_id} ({len(selected)}/{count})")
    return selected


def start_round(db: Session, round_id: int, admin_id: int) -> dict[str, Any]:
    cfg = settings_map(db)
    r = db.get(CompetitionRound, round_id)
    if not r:
        raise RoundError(status_code=404, detail="Round not found")
    if r.status == "active":
        raise RoundError(status_code=409, detail="This round is already running")
    if r.status in ("submitted", "ended"):
        raise RoundError(status_code=409, detail="This round has already ended")
    if round_id > 1:
        previous = db.get(CompetitionRound, round_id - 1)
        if not previous or previous.status != "ended":
            raise RoundError(status_code=409, detail="Complete the previous round first - rounds cannot be skipped")
    count = int(cfg.get("questions_per_round", {}).get(str(round_id), 8))
    # An already-paused round may be restarted from its saved question set.
    r.question_ids = pick_questions(db, round_id, count)
    now = utcnow()
    r.status = "active"
    r.server_start_at = now
    r.ends_at = now + timedelta(minutes=r.duration_minutes)
    r.paused_at = None
    r.paused_seconds = 0
    r.ended_at = None
    r.started_by_id = admin_id
    teams = eligible_teams(db, round_id, cfg)
    for team in teams:
        existing = db.scalar(
            select(TeamRoundSession).where(
                TeamRoundSession.team_id == team.id, TeamRoundSession.round_id == round_id
            )
        )
        if not existing:
            existing = TeamRoundSession(team_id=team.id, round_id=round_id)
            db.add(existing)
        existing.status = "active"
        existing.completed_at = None
        existing.total_score = existing.correct_count = existing.incorrect_count = 0
        existing.unanswered_count = existing.violation_count = 0
        existing.review_required = False
        existing.answers.clear()
    audit(db, f"round.{round_id}.started", "administrator", admin_id, "competition_round", round_id,
          {"teams": len(teams), "questions": count})
    db.commit()
    return round_summary(r)


def pause_round(db: Session, round_id: int, admin_id: int) -> dict[str, Any]:
    r = db.get(CompetitionRound, round_id)
    if not r or r.status != "active":
        raise RoundError(status_code=409, detail="Only an active round can be paused")
    r.status = "paused"
    r.paused_at = utcnow()
    for s in db.scalars(select(TeamRoundSession).where(TeamRoundSession.round_id == round_id)):
        s.status = "paused"
    audit(db, f"round.{round_id}.paused", "administrator", admin_id, "competition_round", round_id)
    db.commit()
    return round_summary(r)


def resume_round(db: Session, round_id: int, admin_id: int) -> dict[str, Any]:
    r = db.get(CompetitionRound, round_id)
    if not r or r.status != "paused":
        raise RoundError(status_code=409, detail="Only a paused round can be resumed")
    now = utcnow()
    if r.paused_at:
        delta = int((now - r.paused_at).total_seconds())
        r.paused_seconds += max(0, delta)
        if r.ends_at:
            r.ends_at = r.ends_at + timedelta(seconds=max(0, delta))
    r.paused_at = None
    r.status = "active"
    for s in db.scalars(select(TeamRoundSession).where(TeamRoundSession.round_id == round_id)):
        s.status = "active"
    audit(db, f"round.{round_id}.resumed", "administrator", admin_id, "competition_round", round_id)
    db.commit()
    return round_summary(r)


def end_round(db: Session, round_id: int, admin_id: int | None, *, auto: bool = False) -> dict[str, Any]:
    r = db.get(CompetitionRound, round_id)
    if not r or r.status not in ("active", "paused"):
        raise RoundError(status_code=409, detail="Only an active or paused round can be ended")
    cfg = settings_map(db)
    now = utcnow()
    r.status = "ended"
    r.ended_at = now
    r.paused_at = None
    sessions = list(db.scalars(
        select(TeamRoundSession).options(selectinload(TeamRoundSession.answers))
        .where(TeamRoundSession.round_id == round_id)
    ))
    for s in sessions:
        complete_session(db, s, auto=auto, cfg=cfg)
    audit(db, f"round.{round_id}.ended", "administrator" if admin_id else "system", admin_id,
          "competition_round", round_id, {"auto": auto, "sessions": len(sessions)})
    db.commit()
    return round_summary(r)


def check_auto_end(db: Session) -> list[int]:
    """Called by the background scheduler; returns round IDs that were auto-ended."""
    now = utcnow()
    due = list(db.scalars(
        select(CompetitionRound).where(CompetitionRound.status == "active")
    ))
    ended: list[int] = []
    for r in due:
        if r.ends_at and r.ends_at <= now:
            try:
                end_round(db, r.id, None, auto=True)
                ended.append(r.id)
            except RoundError:
                continue
    return ended


def participant_state(db: Session, team_id: int, participant_id: int) -> dict[str, Any]:
    """Build the participant-safe state. Never includes correct answers or explanations."""
    cfg = settings_map(db)
    rounds = db.scalars(select(CompetitionRound).order_by(CompetitionRound.id)).all()
    result: dict[str, Any] = {
        "rounds": [round_summary(r) for r in rounds],
        "hints_enabled": bool(cfg.get("hints_enabled", True)),
        "hints_auto_show": bool(cfg.get("hints_auto_show", False)),
        "break_enabled": bool(cfg.get("break_enabled", True)),
        "violation_threshold": int(cfg.get("violation_threshold", 3)),
        "server_time": utcnow().isoformat(),
        "results_published": bool(cfg.get("results_published", False)),
        "participant_score_visibility": bool(cfg.get("participant_score_visibility", False)),
    }
    active = next((r for r in rounds if r.status in ("active", "paused")), None)
    if active:
        session = db.scalar(
            select(TeamRoundSession).options(selectinload(TeamRoundSession.answers))
            .where(TeamRoundSession.team_id == team_id, TeamRoundSession.round_id == active.id)
        )
        if session and not session.disqualified:
            questions = []
            answer_map = {a.question_id: a for a in session.answers}
            for qid in active.question_ids or []:
                q = db.get(Question, qid)
                if not q:
                    continue
                item = {
                    "id": q.id, "domain": q.domain, "difficulty": q.difficulty,
                    "marks": q.marks, "question": q.statement,
                    "options": [o.text for o in sorted(q.options, key=lambda o: o.position)],
                    "reference": q.scenario_ref,
                }
                answer = answer_map.get(q.id)
                item["answer"] = {
                    "selected_index": answer.selected_index if answer else None,
                    "submitted": bool(answer.submitted) if answer else False,
                    "hint_used": bool(answer.hint_used) if answer else False,
                    "hint_count": answer.hint_count if answer else 0,
                    "hint": (q.hint.text if q.hint and answer and (answer.hint_used or cfg.get("hints_auto_show")) else None),
                }
                questions.append(item)
            result["active_round"] = {
                **round_summary(active),
                "questions": questions,
                "session": {
                    "status": session.status,
                    "violation_count": session.violation_count,
                    "review_required": session.review_required,
                },
            }
    latest_ended = next((r for r in reversed(rounds) if r.status == "ended"), None)
    result["latest_ended_round"] = latest_ended.id if latest_ended else None
    return result
