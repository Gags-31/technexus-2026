"""Environment-driven configuration for TECHNEXUS 2026."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "TECHNEXUS 2026"
    environment: str = "development"
    debug: bool = False
    # SQLite is the zero-configuration default. Set DATABASE_URL to a PostgreSQL
    # URL (postgresql+psycopg://user:pass@host:5432/db) for production deployments.
    database_url: str = "sqlite:///./technexus.db"
    secret_key: str = "dev-only-change-this-secret-before-the-event"
    session_cookie: str = "tnx_session"
    session_ttl_hours: int = 12
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    admin_setup_file: str = str(BASE_DIR / ".admin_credentials.txt")
    rate_limit_per_minute: int = 12
    trusted_hosts: str = "*"
    event_date: str = "2026-12-12"
    event_start_time: str = "11:00"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


DEFAULT_SCHEDULE = [
    {"id": "inauguration", "label": "AWSSBG Inauguration Ceremony", "start": "11:00", "end": "11:20", "kind": "ceremony"},
    {"id": "intro", "label": "TECHNEXUS Introduction and Rules", "start": "11:20", "end": "11:30", "kind": "briefing"},
    {"id": "r1", "label": "Round 1 - TECH BLITZ", "start": "11:30", "end": "11:55", "kind": "round", "round": 1},
    {"id": "break1", "label": "Fun Riddle and Meme Break", "start": "11:55", "end": "12:00", "kind": "break"},
    {"id": "r2", "label": "Round 2 - DECODE THE DOMAIN", "start": "12:00", "end": "12:25", "kind": "round", "round": 2},
    {"id": "break2", "label": "Fun Riddle and Meme Break", "start": "12:25", "end": "12:30", "kind": "break"},
    {"id": "lunch", "label": "Break", "start": "12:30", "end": "12:40", "kind": "break"},
    {"id": "r3", "label": "Round 3 - TECH TROUBLESHOOTER", "start": "12:40", "end": "13:15", "kind": "round", "round": 3},
    {"id": "break3", "label": "Fun Riddle and Meme Break", "start": "13:15", "end": "13:20", "kind": "break"},
    {"id": "r4", "label": "Final Round - NEXUS SHOWDOWN", "start": "13:20", "end": "13:50", "kind": "round", "round": 4},
    {"id": "evaluation", "label": "Final Evaluation", "start": "13:50", "end": "14:00", "kind": "evaluation"},
    {"id": "results", "label": "Results, Prize Distribution and Closing", "start": "14:00", "end": "14:15", "kind": "results"},
]

DEFAULT_SETTINGS: dict[str, object] = {
    "event_date": settings.event_date,
    "event_start_time": settings.event_start_time,
    "schedule": DEFAULT_SCHEDULE,
    "hints_enabled": True,
    "hint_cost_marks": 0,
    "hint_mode": "once",
    "hints_auto_show": False,
    "marks_correct": 10,
    "marks_incorrect": 0,
    "marks_unanswered": 0,
    "final_shortlist_enabled": True,
    "participant_score_visibility": False,
    "results_published": False,
    "violation_threshold": 3,
    "violation_auto_submit": True,
    "violation_disqualify": False,
    "break_enabled": True,
    "riddle_bonus_marks": 0,
    "questions_per_round": {"1": 10, "2": 8, "3": 7, "4": 5},
    "registration_open": True,
}

PUBLIC_SETTING_KEYS = {
    "event_date", "event_start_time", "schedule", "hints_enabled", "hints_auto_show",
    "break_enabled", "riddle_bonus_marks", "registration_open", "violation_threshold",
}


def json_dumps(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
