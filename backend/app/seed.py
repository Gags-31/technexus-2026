"""Idempotent seed loader for questions, rounds, riddles, memes and settings."""
from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import DEFAULT_SETTINGS, DEFAULT_SCHEDULE
from .models import (
    Announcement, CompetitionRound, CompetitionSetting, MemeContent, Question,
    QuestionCorrectAnswer, QuestionExplanation, QuestionHint, QuestionOption, Riddle,
)
from .services.core import set_setting

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONTENT_DIR = Path(os.environ.get("TECHNEXUS_CONTENT_DIR", PROJECT_ROOT / "content"))

ROUND_DEFS = [
    (1, "TECH BLITZ", "TECH BLITZ", "Rapid-fire fundamentals across all four domains.", 25),
    (2, "DECODE THE DOMAIN", "DECODE THE DOMAIN", "Identify models, architectures, schedules, queries and schemas from evidence.", 25),
    (3, "TECH TROUBLESHOOTER", "TECH TROUBLESHOOTER", "Diagnose realistic failures and choose the best technical remedy.", 35),
    (4, "NEXUS SHOWDOWN", "NEXUS SHOWDOWN", "Advanced cross-domain showdown for the finalists.", 30),
]


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def seed_rounds(db: Session) -> None:
    for rid, name, short, desc, duration in ROUND_DEFS:
        row = db.get(CompetitionRound, rid)
        if not row:
            db.add(CompetitionRound(id=rid, name=name, short_name=short, description=desc,
                                    duration_minutes=duration, status="locked"))
        else:
            row.duration_minutes = duration
    db.flush()


def seed_settings(db: Session) -> None:
    descriptions = {
        "event_date": "Configurable competition date (YYYY-MM-DD)",
        "event_start_time": "Ceremony start time (24h HH:MM)",
        "schedule": "Full configurable event timeline",
        "hints_enabled": "Allow hints",
        "hint_cost_marks": "Marks deducted per hint",
        "hint_mode": "once | multiple",
        "hints_auto_show": "Show hints automatically",
        "marks_correct": "Marks for a correct answer",
        "marks_incorrect": "Marks for an incorrect answer",
        "marks_unanswered": "Marks for an unanswered question",
        "final_shortlist_enabled": "Restrict final round to shortlisted teams",
        "participant_score_visibility": "Allow teams to see their own score",
        "results_published": "Publish final results to participants",
        "violation_threshold": "Violations before automatic submission",
        "violation_auto_submit": "Auto-submit at threshold",
        "violation_disqualify": "Require manual disqualification review",
        "break_enabled": "Enable riddle and meme breaks",
        "riddle_bonus_marks": "Bonus marks for a correct riddle guess",
        "questions_per_round": "Number of questions selected per round",
        "registration_open": "Allow new team registrations",
    }
    for key, value in DEFAULT_SETTINGS.items():
        if not db.get(CompetitionSetting, key):
            set_setting(db, key, value)
            row = db.get(CompetitionSetting, key)
            if row:
                row.description = descriptions.get(key, "")
    db.flush()


def seed_questions(db: Session) -> int:
    files = ["ai.json", "cloud.json", "os.json", "dbms.json"]
    count = 0
    for filename in files:
        for item in _load_json(CONTENT_DIR / "questions" / filename):
            qid = item["id"]
            q = db.get(Question, qid)
            if not q:
                q = Question(id=qid)
                db.add(q)
            q.domain = item["domain"]
            q.round = int(item["round"])
            q.difficulty = item["difficulty"]
            q.marks = int(item.get("marks", 10))
            q.statement = item["question"]
            q.scenario_ref = item.get("reference", "") or ""
            q.is_active = True
            q.options.clear()
            for position, text in enumerate(item["options"]):
                q.options.append(QuestionOption(
                    position=position, text=text,
                    is_correct=position == int(item["correct_index"]),
                ))
            if q.hint:
                q.hint.text = item["hint"]
            else:
                q.hint = QuestionHint(text=item["hint"])
            if q.explanation:
                q.explanation.text = item["explanation"]
            else:
                q.explanation = QuestionExplanation(text=item["explanation"])
            correct = int(item["correct_index"])
            if q.correct_answer:
                q.correct_answer.option_position = correct
            else:
                q.correct_answer = QuestionCorrectAnswer(option_position=correct)
            count += 1
    db.flush()
    return count


def seed_riddles(db: Session) -> int:
    items = _load_json(CONTENT_DIR / "riddles" / "riddles.json")
    for item in items:
        r = db.get(Riddle, item["id"])
        if not r:
            db.add(Riddle(
                id=item["id"], category=item["category"], question=item["question"],
                answer=item["answer"], explanation=item.get("explanation", ""),
                is_active=True, duration_seconds=300,
            ))
    db.flush()
    return len(items)


def seed_memes(db: Session) -> int:
    items = _load_json(CONTENT_DIR / "memes.json")
    for item in items:
        m = db.get(MemeContent, item["id"])
        if not m:
            db.add(MemeContent(
                id=item["id"], title=item["title"], category=item["category"],
                top=item["top"], bottom=item["bottom"], theme=item.get("theme", "cyan"),
                glyph=item.get("glyph", "💡"), is_enabled=True,
                scheduled_slot=item.get("scheduled_slot"),
            ))
    db.flush()
    return len(items)


def seed_announcements(db: Session) -> None:
    if db.scalar(select(Announcement).limit(1)):
        return
    db.add(Announcement(
        title="Welcome to TECHNEXUS 2026",
        body="CONNECT. THINK. CONQUER. Verify your team code, enter the waiting lobby and wait for the organiser to start each round.",
        audience="all", is_active=True,
    ))
    db.flush()


def seed_all(db: Session) -> dict[str, int]:
    seed_settings(db)
    seed_rounds(db)
    questions = seed_questions(db)
    riddles = seed_riddles(db)
    memes = seed_memes(db)
    seed_announcements(db)
    db.commit()
    return {"questions": questions, "riddles": riddles, "memes": memes}
