"""FastAPI authentication and authorisation dependencies."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Administrator, Participant, Session as SessionModel
from .security import token_hash


class Actor:
    def __init__(self, kind: str, record) -> None:
        self.kind = kind
        self.id = record.id
        self.record = record

    @property
    def is_admin(self) -> bool:
        return self.kind == "administrator"

    @property
    def name(self) -> str:
        return self.record.full_name


def resolve_actor(
    request: Request,
    db: Session = Depends(get_db),
    tnx_session: str | None = Cookie(default=None),
) -> Actor | None:
    token = tnx_session or request.query_params.get("token")
    if not token:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
    if not token:
        return None
    row = db.scalar(
        select(SessionModel).where(
            SessionModel.token_hash == token_hash(token),
            SessionModel.revoked_at.is_(None),
            SessionModel.expires_at > datetime.now(timezone.utc),
        )
    )
    if not row:
        return None
    row.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    if row.actor_type == "administrator":
        admin = db.get(Administrator, row.actor_id)
        if admin and admin.is_active:
            return Actor("administrator", admin)
    elif row.actor_type == "participant":
        participant = db.get(Participant, row.actor_id)
        if participant and participant.is_active and participant.team_id:
            return Actor("participant", participant)
    return None


def optional_actor(actor: Actor | None = Depends(resolve_actor)) -> Actor | None:
    return actor


def require_actor(actor: Actor | None = Depends(resolve_actor)) -> Actor:
    if not actor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return actor


def require_participant(actor: Actor = Depends(require_actor)) -> Actor:
    if actor.kind != "participant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Participant access only")
    return actor


def require_admin(actor: Actor = Depends(require_actor)) -> Actor:
    if actor.kind != "administrator":
        # Deliberately identical error for participants and unauthenticated callers
        # is handled by require_actor; here we hide the admin surface completely.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return actor


def require_full_admin(actor: Actor = Depends(require_admin)) -> Actor:
    if actor.record.must_change_password:
        raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="Change your temporary password first")
    return actor


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]
