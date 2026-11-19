# TECHNEXUS 2026 — Database, Schema and Backup

## Engine

- **Local default:** SQLite at `backend/technexus.db`, with `foreign_keys=ON`, `journal_mode=WAL` and `busy_timeout=10000`.
- **Production:** PostgreSQL via `DATABASE_URL=postgresql+psycopg://...`. The ORM uses portable SQLAlchemy types; no SQLite-specific SQL is required.
- **Migrations:** Alembic configuration in `backend/alembic.ini`, initial revision in `backend/migrations/versions/`.

## Key entities

| Table | Purpose |
| --- | --- |
| `administrators` | Two independent organiser accounts with bcrypt hashes and forced password change flag |
| `teams` | Team identity, approval status, shortlist flag, unique public ID |
| `participants` | Individual leader/member accounts, confirmation timestamp, role |
| `team_memberships` | Explicit two-member mapping; enforces exactly one Leader and one Member |
| `registrations` | Application details and organiser decision/notes |
| `team_access_codes` | Unique `TNX-...` code, expiry, revocation, failed attempts, lockout |
| `competition_rounds` | Round definitions, authoritative start/end/pause timestamps, question ID list |
| `questions`, `question_options`, `question_correct_answers`, `question_hints`, `question_explanations` | Normalised question bank; answers/hints/explanations are private to organisers |
| `team_round_sessions` | Per-team per-round session, status, timer, violation count, totals |
| `team_answers`, `answer_history` | Current shared answer plus full change/submission history |
| `scores` | Server-authoritative per-team per-round scores and tie-breakers |
| `riddles`, `riddle_attempts`, `meme_content` | Break content and guesses |
| `violations` | Browser monitoring events with action taken and review status |
| `announcements` | Organiser messages |
| `sessions` | Server-side session tokens (hashed), actor type, expiry, IP, user agent |
| `password_resets` | One-time reset tokens (hashed) |
| `audit_logs` | Full action trail with actor, target, metadata and IP |
| `competition_settings` | Editable event, hint, scoring, break and anti-cheating configuration |

All timestamp columns use a UTC-aware type decorator so SQLite and PostgreSQL behave identically.

## Constraints and safety

- Unique constraints on team public ID, access code, participant email, team+round session, team+question answer and team+round score.
- Strict two-member validation is enforced in both the API schema and the database membership model.
- Correct answers, explanations and hints are stored in separate tables and are never serialised into participant responses during competition.
- Session tokens and reset tokens are stored only as SHA-256 hashes.

## Backup (SQLite)

Stop the application or use SQLite's online backup API so WAL content is included.

```powershell
cd backend
.\.venv\Scripts\python.exe ..\scripts\backup_db.py --db technexus.db --output ..\backups\technexus-pre-event.db
```

## Restore (SQLite)

```powershell
cd backend
.\.venv\Scripts\python.exe ..\scripts\restore_db.py --db technexus.db --input ..\backups\technexus-pre-event.db
```

Always stop the application before restoring and take a fresh backup first.

## Backup (PostgreSQL)

Use the platform's standard tooling, for example:

```powershell
pg_dump -Fc -f technexus.dump "$env:DATABASE_URL"
pg_restore -c -d "$env:DATABASE_URL" technexus.dump
```

Store backups encrypted and outside the web root. Verify a restore before event day.

## Backup schedule recommendation

- Before registration opens.
- After registration closes and approvals are complete.
- Immediately before the first round.
- After final results are published.
- Retain at least two copies in separate locations.
