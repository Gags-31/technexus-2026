"""Round control, private live scoreboard, monitoring and violation review."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..deps import Actor, require_full_admin
from ..models import (
    CompetitionRound, Team, TeamRoundSession, Violation, utcnow,
)
from ..realtime import hub
from ..services.core import audit, build_scoreboard, settings_map
from ..services.rounds import (
    end_round, pause_round, reset_event_state, restart_event, resume_round,
    rounds_overview, start_round,
)

router = APIRouter(prefix="/api/admin", tags=["administrator"])


@router.get("/rounds")
def get_rounds(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    return rounds_overview(db)


class DurationPatch(BaseModel):
    duration_minutes: int = Field(ge=1, le=180)


@router.patch("/rounds/{round_id}")
def patch_round(
    round_id: int, payload: DurationPatch, actor: Actor = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    r = db.get(CompetitionRound, round_id)
    if not r:
        raise HTTPException(status_code=404, detail="Round not found")
    if r.status in ("active", "paused"):
        raise HTTPException(status_code=409, detail="Duration cannot be changed while the round is running")
    r.duration_minutes = payload.duration_minutes
    audit(db, f"round.{round_id}.duration_updated", "administrator", actor.id,
          "competition_round", round_id, {"minutes": payload.duration_minutes})
    db.commit()
    return rounds_overview(db)


@router.post("/rounds/{round_id}/start")
async def api_start_round(
    round_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    state = start_round(db, round_id, actor.id)
    await hub.broadcast("round.started", {
        "round_id": round_id, "name": state["name"],
        "message": f"{state['name']} has started. Good luck!",
    }, channel="participant")
    await hub.broadcast("round.changed", {"round": state}, channel="administrator")
    return state


@router.post("/rounds/{round_id}/pause")
async def api_pause_round(
    round_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    state = pause_round(db, round_id, actor.id)
    await hub.broadcast("round.paused", {"round_id": round_id, "message": "The round is paused. Stay on this page."},
                        channel="participant")
    await hub.broadcast("round.changed", {"round": state}, channel="administrator")
    return state


@router.post("/rounds/{round_id}/resume")
async def api_resume_round(
    round_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    state = resume_round(db, round_id, actor.id)
    await hub.broadcast("round.resumed", {"round_id": round_id, "message": "The round has resumed."},
                        channel="participant")
    await hub.broadcast("round.changed", {"round": state}, channel="administrator")
    return state


@router.post("/rounds/{round_id}/end")
async def api_end_round(
    round_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    state = end_round(db, round_id, actor.id)
    await hub.broadcast("round.ended", {
        "round_id": round_id, "name": state["name"],
        "message": f"{state['name']} has ended. Saved answers were submitted automatically.",
    }, channel="participant")
    await hub.broadcast("round.changed", {"round": state}, channel="administrator")
    await hub.broadcast("scoreboard.updated", {"round_id": round_id}, channel="administrator")
    return state


# --------------------------------------------------------------------------- event reset / restart
@router.post("/event/reset")
async def api_reset_event(
    actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    """Clear all competition runtime data while keeping registrations and content."""
    result = reset_event_state(db, actor.id)
    await hub.broadcast("event.reset", {
        "message": "The event has been reset by the organisers. Reloading the competition state.",
    }, channel="participant")
    await hub.broadcast("round.changed", {"rounds": result["rounds"]}, channel="administrator")
    await hub.broadcast("scoreboard.updated", {}, channel="administrator")
    return result


@router.post("/event/restart")
async def api_restart_event(
    actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    """Reset runtime state and immediately start Round 1 from a fresh server clock."""
    state = restart_event(db, actor.id)
    await hub.broadcast("event.restarted", {
        "message": "TECHNEXUS 2026 has restarted. Round 1 is now active.",
    }, channel="participant")
    await hub.broadcast("round.started", {
        "round_id": state["id"], "name": state["name"],
        "message": f"{state['name']} has started. Good luck!",
    }, channel="participant")
    await hub.broadcast("round.changed", {
        "round": state, "rounds": rounds_overview(db),
    }, channel="administrator")
    await hub.broadcast("scoreboard.updated", {}, channel="administrator")
    return {"restarted": True, "round": state}


# --------------------------------------------------------------------------- scoreboard
@router.get("/scoreboard")
def scoreboard(
    sort: Literal["rank", "name", "total"] = "rank",
    round: int | None = None,
    status: Literal["all", "completed", "in_progress"] = "all",
    search: str | None = None,
    db: Session = Depends(get_db), _: Actor = Depends(require_full_admin),
):
    rows = build_scoreboard(db)
    if round:
        rows = [r for r in rows if r["rounds"][str(round)]["status"] != "not_started"]
    if status == "completed":
        rows = [r for r in rows if r["completed"]]
    elif status == "in_progress":
        rows = [r for r in rows if not r["completed"]]
    if search:
        needle = search.lower()
        rows = [r for r in rows if needle in (r["team_name"] + r["college"] + r["public_id"]).lower()]
    if sort == "name":
        rows.sort(key=lambda r: r["team_name"].lower())
    elif sort == "total":
        rows.sort(key=lambda r: -r["total"])
    for index, row in enumerate(rows, start=1):
        row["filtered_rank"] = index
    return {"rows": rows, "updated_at": utcnow().isoformat()}


# --------------------------------------------------------------------------- live monitor
@router.get("/monitor")
def monitor(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    teams = db.scalars(select(Team).options(selectinload(Team.members), selectinload(Team.access_code))).all()
    sessions = list(db.scalars(select(TeamRoundSession).options(selectinload(TeamRoundSession.answers))))
    session_map = {s.team_id: s for s in sessions if s.status in ("active", "paused")}
    connected = hub.active_team_ids()
    cards = []
    for team in teams:
        s = session_map.get(team.id)
        cards.append({
            "team_id": team.id, "team_name": team.name, "status": team.status,
            "members": [m.full_name for m in team.members],
            "connected": team.id in connected,
            "active_session": s.status if s else None,
            "round_id": s.round_id if s else None,
            "answers_saved": sum(1 for a in s.answers if a.selected_index is not None) if s else 0,
            "answers_submitted": sum(1 for a in s.answers if a.submitted) if s else 0,
            "violations": s.violation_count if s else 0,
            "review_required": s.review_required if s else False,
        })
    cards.sort(key=lambda c: (not c["connected"], c["team_name"].lower()))
    return {"teams": cards, "connected_count": len(connected), "admin_connections": hub.admin_connections()}


@router.get("/violations")
def violations(db: Session = Depends(get_db), _: Actor = Depends(require_full_admin)):
    rows = db.scalars(select(Violation).order_by(Violation.created_at.desc()).limit(300))
    return [{"id": v.id, "team_id": v.team_id, "round_id": v.round_id,
             "participant_id": v.participant_id, "kind": v.kind, "detail": v.detail,
             "action": v.action_taken, "reviewed": v.reviewed, "reinstated": v.reinstated,
             "created_at": v.created_at.isoformat()} for v in rows]


class ViolationReview(BaseModel):
    reinstate: bool = False
    note: str = Field(default="", max_length=500)


@router.post("/violations/{violation_id}/review")
def review_violation(
    violation_id: int, payload: ViolationReview, actor: Actor = Depends(require_full_admin),
    db: Session = Depends(get_db),
):
    v = db.get(Violation, violation_id)
    if not v:
        raise HTTPException(status_code=404, detail="Violation not found")
    v.reviewed = True
    v.reinstated = payload.reinstate
    if payload.reinstate and v.session_id:
        s = db.get(TeamRoundSession, v.session_id)
        if s and s.status in ("submitted", "auto_submitted"):
            # Reopening a finished session requires an organiser to restart the round.
            s.review_required = True
    audit(db, "violation.reviewed", "administrator", actor.id, "violation", violation_id,
          {"reinstate": payload.reinstate, "note": payload.note})
    db.commit()
    return {"ok": True}


@router.post("/teams/{team_id}/reinstate")
async def reinstate_team(
    team_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    for s in db.scalars(select(TeamRoundSession).where(TeamRoundSession.team_id == team_id)):
        s.review_required = False
        if s.status == "disqualified":
            s.disqualified = False
    team.status = "approved"
    audit(db, "team.reinstated", "administrator", actor.id, "team", team_id)
    db.commit()
    await hub.notify_team(team_id, "team.reinstated", {"message": "Your team has been reinstated by the organisers."})
    return {"ok": True}


@router.post("/teams/{team_id}/disqualify")
async def disqualify_team(
    team_id: int, actor: Actor = Depends(require_full_admin), db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    for s in db.scalars(select(TeamRoundSession).where(TeamRoundSession.team_id == team_id)):
        s.disqualified = True
    team.status = "disqualified"
    audit(db, "team.disqualified", "administrator", actor.id, "team", team_id)
    db.commit()
    await hub.notify_team(team_id, "team.disqualified", {"message": "Your team has been disqualified pending organiser review."})
    return {"ok": True}
