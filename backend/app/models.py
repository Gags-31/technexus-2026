"""Normalised relational model for the TECHNEXUS 2026 competition platform."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .db import Base


class UTCDateTime(TypeDecorator):
    """Store UTC-naive values but always return timezone-aware UTC datetimes.

    SQLite drops timezone information on round-trip; without this decorator,
    comparisons between freshly generated and database-loaded timestamps fail.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Administrator(TimestampMixin, Base):
    __tablename__ = "administrators"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(24), default="organiser")  # organiser | co-organiser
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    college: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(120))
    semester: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("administrators.id"))
    members: Mapped[list[Participant]] = relationship(back_populates="team")
    access_code: Mapped[TeamAccessCode | None] = relationship(back_populates="team", uselist=False)
    registration: Mapped[Registration | None] = relationship(back_populates="team", uselist=False)


class Participant(TimestampMixin, Base):
    __tablename__ = "participants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    mobile: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))  # leader | member
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    team: Mapped[Team | None] = relationship(back_populates="members")
    membership: Mapped[TeamMembership | None] = relationship(back_populates="participant", uselist=False)


class TeamMembership(TimestampMixin, Base):
    __tablename__ = "team_memberships"
    __table_args__ = (
        UniqueConstraint("team_id", "role", name="uq_membership_team_role"),
        UniqueConstraint("participant_id", name="uq_membership_participant"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))
    team: Mapped[Team] = relationship()
    participant: Mapped[Participant] = relationship(back_populates="membership")


class Registration(TimestampMixin, Base):
    __tablename__ = "registrations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), unique=True)
    submitted_by_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"))
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    decision: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("administrators.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    team: Mapped[Team] = relationship(back_populates="registration")


class TeamAccessCode(TimestampMixin, Base):
    __tablename__ = "team_access_codes"
    __table_args__ = (UniqueConstraint("team_id", name="uq_code_team"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime())
    team: Mapped[Team] = relationship(back_populates="access_code")


class CompetitionRound(Base):
    __tablename__ = "competition_rounds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    short_name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=25)
    status: Mapped[str] = mapped_column(String(20), default="locked", index=True)
    server_start_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    paused_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    paused_seconds: Mapped[int] = mapped_column(Integer, default=0)
    question_ids: Mapped[list] = mapped_column(JSON, default=list)
    started_by_id: Mapped[int | None] = mapped_column(ForeignKey("administrators.id"))
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class Question(TimestampMixin, Base):
    __tablename__ = "questions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    domain: Mapped[str] = mapped_column(String(48), index=True)
    round: Mapped[int] = mapped_column(Integer, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), index=True)
    marks: Mapped[int] = mapped_column(Integer, default=10)
    statement: Mapped[str] = mapped_column(Text)
    scenario_ref: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    options: Mapped[list[QuestionOption]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.position"
    )
    hint: Mapped[QuestionHint | None] = relationship(back_populates="question", uselist=False, cascade="all, delete-orphan")
    explanation: Mapped[QuestionExplanation | None] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan"
    )
    correct_answer: Mapped[QuestionCorrectAnswer | None] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (UniqueConstraint("question_id", "position", name="uq_option_question_position"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    question: Mapped[Question] = relationship(back_populates="options")


class QuestionHint(Base):
    __tablename__ = "question_hints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    question: Mapped[Question] = relationship(back_populates="hint")


class QuestionExplanation(Base):
    __tablename__ = "question_explanations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    question: Mapped[Question] = relationship(back_populates="explanation")


class QuestionCorrectAnswer(Base):
    __tablename__ = "question_correct_answers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    option_position: Mapped[int] = mapped_column(Integer)
    question: Mapped[Question] = relationship(back_populates="correct_answer")


class TeamRoundSession(TimestampMixin, Base):
    __tablename__ = "team_round_sessions"
    __table_args__ = (
        UniqueConstraint("team_id", "round_id", name="uq_session_team_round"),
        Index("ix_session_status", "status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    round_id: Mapped[int] = mapped_column(ForeignKey("competition_rounds.id"))
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0)
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0)
    violation_count: Mapped[int] = mapped_column(Integer, default=0)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    disqualified: Mapped[bool] = mapped_column(Boolean, default=False)
    answers: Mapped[list[TeamAnswer]] = relationship(back_populates="session", cascade="all, delete-orphan")
    team: Mapped[Team] = relationship()
    round: Mapped[CompetitionRound] = relationship()


class TeamAnswer(TimestampMixin, Base):
    __tablename__ = "team_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_answer_session_question"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("team_round_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), index=True)
    selected_index: Mapped[int | None] = mapped_column(Integer)
    hint_used: Mapped[bool] = mapped_column(Boolean, default=False)
    hint_count: Mapped[int] = mapped_column(Integer, default=0)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    submitted_by_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    marks_awarded: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    session: Mapped[TeamRoundSession] = relationship(back_populates="answers")


class AnswerHistory(TimestampMixin, Base):
    __tablename__ = "answer_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("team_round_sessions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"))
    action: Mapped[str] = mapped_column(String(32))
    previous_index: Mapped[int | None] = mapped_column(Integer)
    new_index: Mapped[int | None] = mapped_column(Integer)


class Score(TimestampMixin, Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("team_id", "round_id", name="uq_score_team_round"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    round_id: Mapped[int] = mapped_column(ForeignKey("competition_rounds.id"))
    session_id: Mapped[int] = mapped_column(ForeignKey("team_round_sessions.id"))
    correct: Mapped[int] = mapped_column(Integer, default=0)
    incorrect: Mapped[int] = mapped_column(Integer, default=0)
    unanswered: Mapped[int] = mapped_column(Integer, default=0)
    marks: Mapped[int] = mapped_column(Integer, default=0)
    completion_seconds: Mapped[int] = mapped_column(Integer, default=0)
    pending: Mapped[bool] = mapped_column(Boolean, default=False)


class Riddle(TimestampMixin, Base):
    __tablename__ = "riddles"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(String(200))
    explanation: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=300)


class RiddleAttempt(TimestampMixin, Base):
    __tablename__ = "riddle_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    riddle_id: Mapped[str] = mapped_column(ForeignKey("riddles.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    slot: Mapped[int] = mapped_column(Integer)
    guess: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    awarded_marks: Mapped[int] = mapped_column(Integer, default=0)


class MemeContent(TimestampMixin, Base):
    __tablename__ = "meme_content"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40))
    top: Mapped[str] = mapped_column(Text)
    bottom: Mapped[str] = mapped_column(Text)
    theme: Mapped[str] = mapped_column(String(20), default="cyan")
    glyph: Mapped[str] = mapped_column(String(16), default="💡")
    image_url: Mapped[str] = mapped_column(Text, default="")
    scheduled_slot: Mapped[int | None] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Violation(TimestampMixin, Base):
    __tablename__ = "violations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("team_round_sessions.id", ondelete="SET NULL"), index=True)
    participant_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), index=True)
    round_id: Mapped[int | None] = mapped_column(ForeignKey("competition_rounds.id"))
    kind: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text, default="")
    action_taken: Mapped[str] = mapped_column(String(60), default="warning")
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reinstated: Mapped[bool] = mapped_column(Boolean, default=False)


class Announcement(TimestampMixin, Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(24), default="all")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("administrators.id"))
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(40), default="")
    target_id: Mapped[str] = mapped_column(String(48), default="")
    details: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    ip: Mapped[str] = mapped_column(String(64), default="")


class CompetitionSetting(Base):
    __tablename__ = "competition_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[object] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("administrators.id"))


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), index=True)  # participant | administrator
    actor_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(Text, default="")


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[int] = mapped_column(Integer)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
