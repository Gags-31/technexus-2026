"""Authentication, sessions and password management."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import Actor, client_ip, optional_actor, require_actor
from ..models import Administrator, Participant, PasswordReset, Session as SessionModel, utcnow
from ..security import (
    hash_password, new_token, password_strength, rate_limiter, token_hash, verify_password,
)
from ..services.core import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ParticipantLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class AdminLogin(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class ForgotPassword(BaseModel):
    email: str
    actor_type: str = "participant"


class ResetPassword(BaseModel):
    token: str
    new_password: str


def _create_session(db: Session, actor_type: str, actor_id: int, request: Request, response: Response) -> str:
    token = new_token()
    db.add(SessionModel(
        token_hash=token_hash(token), actor_type=actor_type, actor_id=actor_id,
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        ip=client_ip(request), user_agent=request.headers.get("user-agent", "")[:500],
    ))
    db.commit()
    response.set_cookie(
        key=settings.session_cookie, value=token, httponly=True,
        samesite="lax", secure=settings.environment == "production",
        max_age=settings.session_ttl_hours * 3600, path="/",
    )
    return token


@router.post("/participant/login")
def participant_login(payload: ParticipantLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    key = f"login:p:{client_ip(request)}"
    if not rate_limiter.check(key, limit=10):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again shortly.")
    user = db.scalar(select(Participant).where(Participant.email == payload.email.strip().lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        audit(db, "auth.login.failed", "participant", None, "participant", payload.email, ip=client_ip(request))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.team_id:
        raise HTTPException(status_code=403, detail="This account is not linked to a team")
    user.last_login_at = utcnow()
    _create_session(db, "participant", user.id, request, response)
    audit(db, "auth.login.success", "participant", user.id, "participant", user.id, ip=client_ip(request))
    return {
        "id": user.id, "name": user.full_name, "role": user.role,
        "team_id": user.team_id, "kind": "participant",
    }


@router.post("/admin/login")
def admin_login(payload: AdminLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    key = f"login:a:{client_ip(request)}"
    if not rate_limiter.check(key, limit=10):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again shortly.")
    username = payload.username.strip().lower()
    admin = db.scalar(
        select(Administrator).where(
            (Administrator.username == username) | (Administrator.email == username)
        )
    )
    if not admin or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        audit(db, "auth.admin_login.failed", "administrator", None, "administrator", payload.username, ip=client_ip(request))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    admin.last_login_at = utcnow()
    _create_session(db, "administrator", admin.id, request, response)
    audit(db, "auth.admin_login.success", "administrator", admin.id, "administrator", admin.id, ip=client_ip(request))
    return {
        "id": admin.id, "username": admin.username, "name": admin.full_name,
        "role": admin.role, "kind": "administrator",
        "must_change_password": admin.must_change_password,
    }


@router.post("/logout")
def logout(
    response: Response,
    request: Request,
    actor: Actor | None = Depends(optional_actor),
    db: Session = Depends(get_db),
):
    token = request.cookies.get(settings.session_cookie) or request.query_params.get("token")
    if token:
        row = db.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash(token)))
        if row:
            row.revoked_at = utcnow()
    if actor:
        audit(db, "auth.logout", actor.kind, actor.id, ip=client_ip(request))
    db.commit()
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}


@router.get("/socket-token")
def socket_token(
    request: Request,
    actor: Actor | None = Depends(optional_actor),
):
    """Issue the current session token to the same-origin browser for WebSocket auth."""
    if not actor:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = request.cookies.get(settings.session_cookie) or request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Session token unavailable")
    return {"token": token, "role": actor.kind}


@router.get("/me")
def me(actor: Actor | None = Depends(optional_actor), db: Session = Depends(get_db)):
    if not actor:
        return {"authenticated": False}
    data: dict[str, object] = {
        "authenticated": True, "kind": actor.kind, "id": actor.id, "name": actor.name,
    }
    if actor.kind == "administrator":
        data["username"] = actor.record.username
        data["role"] = actor.record.role
        data["must_change_password"] = actor.record.must_change_password
    else:
        data["team_id"] = actor.record.team_id
        data["team_role"] = actor.record.role
    return data


@router.post("/change-password")
def change_password(
    payload: ChangePassword, actor: Actor = Depends(require_actor), db: Session = Depends(get_db)
):
    if not verify_password(payload.current_password, actor.record.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    ok, message = password_strength(payload.new_password)
    if not ok:
        raise HTTPException(status_code=422, detail=message)
    if verify_password(payload.new_password, actor.record.password_hash):
        raise HTTPException(status_code=422, detail="Choose a password you have not used before")
    actor.record.password_hash = hash_password(payload.new_password)
    actor.record.must_change_password = False
    audit(db, "auth.password.changed", actor.kind, actor.id, ip="")
    db.commit()
    return {"ok": True, "must_change_password": False}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPassword, request: Request, db: Session = Depends(get_db)):
    if not rate_limiter.check(f"reset:{client_ip(request)}", limit=5):
        raise HTTPException(status_code=429, detail="Too many reset requests")
    email = payload.email.strip().lower()
    if payload.actor_type == "administrator":
        user = db.scalar(select(Administrator).where(Administrator.email == email))
        actor_type = "administrator"
    else:
        user = db.scalar(select(Participant).where(Participant.email == email))
        actor_type = "participant"
    # Always return the same message to avoid account enumeration.
    generic = {"ok": True, "message": "If that account exists, a reset token has been issued."}
    if not user:
        return generic
    token = new_token()
    db.add(PasswordReset(
        actor_type=actor_type, actor_id=user.id, token_hash=token_hash(token),
        expires_at=utcnow() + timedelta(minutes=30),
    ))
    audit(db, "auth.password.reset_requested", actor_type, user.id, ip=client_ip(request))
    db.commit()
    # Offline college event: the organiser can hand over the single-use token.
    # Set INCLUDE_RESET_TOKEN_IN_RESPONSE=false once an email provider is configured.
    if os.environ.get("INCLUDE_RESET_TOKEN_IN_RESPONSE", "true").lower() == "true":
        return {**generic, "reset_token": token, "expires_in_minutes": 30}
    return generic


@router.post("/reset-password")
def reset_password(payload: ResetPassword, db: Session = Depends(get_db)):
    row = db.scalar(select(PasswordReset).where(
        PasswordReset.token_hash == token_hash(payload.token),
        PasswordReset.used_at.is_(None),
        PasswordReset.expires_at > utcnow(),
    ))
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    ok, message = password_strength(payload.new_password)
    if not ok:
        raise HTTPException(status_code=422, detail=message)
    model = Administrator if row.actor_type == "administrator" else Participant
    user = db.get(model, row.actor_id)
    if not user:
        raise HTTPException(status_code=400, detail="Account no longer exists")
    user.password_hash = hash_password(payload.new_password)
    row.used_at = utcnow()
    audit(db, "auth.password.reset_completed", row.actor_type, row.actor_id)
    db.commit()
    return {"ok": True}
