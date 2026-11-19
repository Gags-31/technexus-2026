"""Authoritative WebSocket fan-out hub.

Participants are subscribed to their team channel so both members always receive
identical question, timer and answer events. Admin channels never receive
participant-only payloads and the private scoreboard is broadcast only on the
``admin`` channel.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .models import Participant
from .security import token_hash
from .db import SessionLocal
from .models import Session as SessionModel
from datetime import datetime, timezone
from sqlalchemy import select


class Hub:
    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._meta: dict[WebSocket, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        *,
        role: str,
        actor_id: int,
        team_id: int | None,
        session_token: str,
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._channels["all"].add(websocket)
            self._channels[role].add(websocket)
            self._channels[f"{role}:{actor_id}"].add(websocket)
            if team_id is not None:
                self._channels[f"team:{team_id}"].add(websocket)
            self._meta[websocket] = {
                "role": role, "actor_id": actor_id, "team_id": team_id,
                "session_token": session_token,
            }

    async def disconnect(self, websocket: WebSocket) -> None:
        meta = self._meta.pop(websocket, {})
        async with self._lock:
            for channel in (
                "all", meta.get("role", ""), f"{meta.get('role')}:{meta.get('actor_id')}",
                f"team:{meta.get('team_id')}" if meta.get("team_id") is not None else "",
            ):
                if channel:
                    self._channels[channel].discard(websocket)

    async def send(self, websocket: WebSocket, event: str, payload: dict[str, Any]) -> None:
        try:
            await websocket.send_json({"event": event, "payload": payload, "server_time": datetime.now(timezone.utc).isoformat()})
        except Exception:
            await self.disconnect(websocket)

    async def broadcast(
        self,
        event: str,
        payload: dict[str, Any],
        *,
        channel: str = "all",
        exclude_token: str | None = None,
    ) -> None:
        async with self._lock:
            targets = list(self._channels.get(channel, set()))
        for ws in targets:
            if exclude_token and self._meta.get(ws, {}).get("session_token") == exclude_token:
                continue
            await self.send(ws, event, payload)

    async def notify_team(self, team_id: int, event: str, payload: dict[str, Any]) -> None:
        await self.broadcast(event, payload, channel=f"team:{team_id}")

    def active_team_ids(self) -> set[int]:
        return {
            meta["team_id"] for meta in self._meta.values()
            if meta.get("role") == "participant" and meta.get("team_id") is not None
        }

    def admin_connections(self) -> int:
        return len(self._channels.get("administrator", set()))


hub = Hub()


async def authenticate_socket(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    db = SessionLocal()
    try:
        row = db.scalar(
            select(SessionModel).where(
                SessionModel.token_hash == token_hash(token),
                SessionModel.revoked_at.is_(None),
                SessionModel.expires_at > datetime.now(timezone.utc),
            )
        )
        if not row:
            return None
        if row.actor_type == "administrator":
            return {"role": "administrator", "actor_id": row.actor_id, "team_id": None, "session_token": token}
        participant = db.get(Participant, row.actor_id)
        if not participant or not participant.is_active or not participant.team_id:
            return None
        return {
            "role": "participant", "actor_id": participant.id,
            "team_id": participant.team_id, "session_token": token,
        }
    finally:
        db.close()


async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    identity = await authenticate_socket(token)
    if not identity:
        await websocket.close(code=4401)
        return
    await hub.connect(websocket, **identity)
    try:
        while True:
            # Inbound frames are heartbeat only; all mutations use authenticated REST.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)
