"""Shared domain helpers: settings, serialisation, scoring and scoreboard."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import DEFAULT_SETTINGS
from ..models import (
    AnswerHistory, AuditLog, CompetitionRound, CompetitionSetting, Question,
    QuestionCorrectAnswer, Score, Team, TeamRoundSession, utcnow,
)


# --------------------------------------------------------------------------- settings
def settings_map(db: Session) -> dict[str, Any]:
    result = dict(DEFAULT_SETTINGS)
    for row in db.scalars(select(CompetitionSetting)):
        result[row.key] = row.value
    return result


def setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(CompetitionSetting, key)
    return row.value if row else DEFAULT_SETTINGS.get(key, default)


def set_setting(db: Session, key: str, value: Any, admin_id: int | None = None) -> None:
    row = db.get(CompetitionSetting, key)
    if not row:
        row = CompetitionSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    row.updated_at = utcnow()
    row.updated_by_id = admin_id


def audit(
    db: Session,
    action: str,
    actor_type: str = "system",
    actor_id: int | None = None,
    target_type: str = "",
    target_id: str = "",
    metadata: dict | None = None,
    ip: str = "",
) -> None:
    db.add(AuditLog(
        action=action, actor_type=actor_type, actor_id=actor_id,
        target_type=target_type, target_id=str(target_id),
        details=metadata or {}, ip=ip,
    ))


# --------------------------------------------------------------------------- serialisers
def team_status(team: Team) -> str:
    if team.status == "approved" and all(p.confirmed_at for p in team.members) and len(team.members) == 2:
        return "approved"
    return team.status


def serialize_team(db: Session, team: Team, *, include_code: bool = True) -> dict[str, Any]:
    members = [
        {"id": p.id, "full_name": p.full_name, "email": p.email, "role": p.role,
         "confirmed": bool(p.confirmed_at), "mobile": p.mobile}
        for p in sorted(team.members, key=lambda p: 0 if p.role == "leader" else 1)
    ]
    code_row = team.access_code
    data: dict[str, Any] = {
        "id": team.id,
        "public_id": team.public_id,
        "name": team.name,
        "college": team.college,
        "department": team.department,
        "semester": team.semester,
        "status": team_status(team),
        "shortlisted": team.shortlisted,
        "members": members,
        "member_count": len(members),
        "approved_at": team.approved_at.isoformat() if team.approved_at else None,
        "registration_decision": team.registration.decision if team.registration else None,
    }
    if include_code and code_row:
        data["code"] = {
            "value": code_row.code,
            "revoked": bool(code_row.revoked_at),
            "expires_at": code_row.expires_at.isoformat() if code_row.expires_at else None,
        }
    return data


def serialize_question(q: Question, *, answers: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": q.id,
        "domain": q.domain,
        "round": q.round,
        "difficulty": q.difficulty,
        "marks": q.marks,
        "question": q.statement,
        "options": [o.text for o in sorted(q.options, key=lambda o: o.position)],
        "reference": q.scenario_ref,
    }
    if answers:
        data.update({
            "correct_index": q.correct_answer.option_position if q.correct_answer else None,
            "correct_option": (
                next((o.text for o in q.options if o.position == q.correct_answer.option_position), "")
                if q.correct_answer else ""
            ),
            "explanation": q.explanation.text if q.explanation else "",
            "hint": q.hint.text if q.hint else "",
        })
    return data


def question_with_hint(q: Question) -> dict[str, Any]:
    data = serialize_question(q)
    data["hint"] = q.hint.text if q.hint else ""
    return data


def round_summary(r: CompetitionRound) -> dict[str, Any]:
    return {
        "id": r.id, "name": r.name, "short_name": r.short_name,
        "description": r.description, "duration_minutes": r.duration_minutes,
        "status": r.status,
        "server_start_at": r.server_start_at.isoformat() if r.server_start_at else None,
        "ends_at": r.ends_at.isoformat() if r.ends_at else None,
        "paused_at": r.paused_at.isoformat() if r.paused_at else None,
        "paused_seconds": r.paused_seconds,
        "question_count": len(r.question_ids or []),
    }


# --------------------------------------------------------------------------- scoring
def score_session(db: Session, session: TeamRoundSession, *, cfg: dict[str, Any] | None = None) -> None:
    """Server-side authoritative scoring. Never callable by participants."""
    cfg = cfg or settings_map(db)
    correct_marks = int(cfg.get("marks_correct", 10))
    incorrect_marks = int(cfg.get("marks_incorrect", 0))
    hint_cost = int(cfg.get("hint_cost_marks", 0))
    q_ids = list(session.round.question_ids or [])
    id_set = set(q_ids)
    correct_records = {
        row.question_id: row.option_position
        for row in db.scalars(select(QuestionCorrectAnswer).where(QuestionCorrectAnswer.question_id.in_(id_set)))
    } if id_set else {}
    answers = {a.question_id: a for a in session.answers}
    total = correct = incorrect = unanswered = 0
    for qid in q_ids:
        answer = answers.get(qid)
        right = correct_records.get(qid)
        if not answer or not answer.submitted or answer.selected_index is None:
            unanswered += 1
            if answer:
                answer.is_correct = False
                answer.marks_awarded = 0
            continue
        is_correct = right is not None and answer.selected_index == right
        answer.is_correct = is_correct
        marks = correct_marks if is_correct else incorrect_marks
        if hint_cost and answer.hint_count:
            marks -= hint_cost * answer.hint_count
        answer.marks_awarded = marks
        total += marks
        if is_correct:
            correct += 1
        else:
            incorrect += 1
    session.total_score = total
    session.correct_count = correct
    session.incorrect_count = incorrect
    session.unanswered_count = unanswered
    if session.round.server_start_at:
        end = session.completed_at or utcnow()
        completion = max(0, int((end - session.round.server_start_at).total_seconds() - session.round.paused_seconds))
    else:
        completion = 0
    existing = db.scalar(select(Score).where(Score.team_id == session.team_id, Score.round_id == session.round_id))
    if not existing:
        existing = Score(team_id=session.team_id, round_id=session.round_id, session_id=session.id)
        db.add(existing)
    existing.correct, existing.incorrect, existing.unanswered = correct, incorrect, unanswered
    existing.marks = total
    existing.completion_seconds = completion
    existing.pending = session.review_required
    existing.session_id = session.id


def complete_session(
    db: Session, session: TeamRoundSession, *, auto: bool = False, cfg: dict | None = None
) -> None:
    if session.status in ("submitted", "auto_submitted", "disqualified"):
        return
    now = utcnow()
    for answer in session.answers:
        if not answer.submitted and answer.selected_index is not None:
            answer.submitted = True
            answer.submitted_at = now
            db.add(AnswerHistory(
                session_id=session.id, question_id=answer.question_id, actor_id=None,
                action="auto_submit", previous_index=None, new_index=answer.selected_index,
            ))
    session.status = "auto_submitted" if auto else "submitted"
    session.completed_at = now
    score_session(db, session, cfg=cfg)


# --------------------------------------------------------------------------- scoreboard
def build_scoreboard(db: Session) -> list[dict[str, Any]]:
    teams = db.scalars(select(Team).options(selectinload(Team.members))).all()
    sessions = db.scalars(
        select(TeamRoundSession).options(selectinload(TeamRoundSession.answers))
    ).all()
    by_team: dict[int, list[TeamRoundSession]] = {}
    for s in sessions:
        by_team.setdefault(s.team_id, []).append(s)
    rows: list[dict[str, Any]] = []
    for team in teams:
        team_sessions = by_team.get(team.id, [])
        per_round = {s.round_id: s for s in team_sessions}
        rounds = {}
        total = correct = incorrect = unanswered = 0
        for rid in (1, 2, 3, 4):
            s = per_round.get(rid)
            rounds[str(rid)] = {
                "score": s.total_score if s else 0,
                "status": s.status if s else "not_started",
                "correct": s.correct_count if s else 0,
                "completed_at": s.completed_at.isoformat() if s and s.completed_at else None,
            }
            if s:
                total += s.total_score
                correct += s.correct_count
                incorrect += s.incorrect_count
                unanswered += s.unanswered_count
        last = max((s.completed_at for s in team_sessions if s.completed_at), default=None)
        active = any(s.status in ("active", "paused") for s in team_sessions)
        pending = any(s.review_required for s in team_sessions)
        rows.append({
            "team_id": team.id,
            "team_name": team.name,
            "public_id": team.public_id,
            "college": team.college,
            "rounds": rounds,
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "unanswered": unanswered,
            "active": active,
            "completed": all(per_round.get(r) and per_round[r].status in ("submitted", "auto_submitted") for r in (1, 2, 3, 4)),
            "status": team.status,
            "shortlisted": team.shortlisted,
            "submission_time": last.isoformat() if last else None,
            "pending_review": pending,
            "violations": sum(s.violation_count for s in team_sessions),
        })
    # Tie-breakers: final round score, then earlier completion time.
    rows.sort(key=lambda r: (
        -r["total"],
        -r["rounds"]["4"]["score"],
        r["submission_time"] or "9999",
        r["team_name"].lower(),
    ))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows
