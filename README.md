# TECHNEXUS 2026

**CONNECT. THINK. CONQUER.**  
**THE ULTIMATE TECH QUIZ** — organised by the AWS Student Builder Group (AWSSBG).

A complete, production-ready event management and synchronised technical quiz platform with separate participant and organiser portals, server-authoritative rounds, live WebSocket control, private scoring, anti-cheating monitoring, original content, exports, audit logs and deployment configuration.

---

## 1. What is included

| Area | Details |
| --- | --- |
| Event | TECHNEXUS 2026, configurable date and editable 11:00–14:15 default schedule (inauguration, intro, four rounds, riddle/meme breaks, evaluation, results/closing) |
| Domains | Artificial Intelligence, Cloud Computing, Operating Systems, DBMS — open to all engineering branches |
| Teams | Strictly two members: exactly one **Team Leader** and one **Team Member**. One-person and three-person registrations are rejected. Multiple concurrent teams are supported. |
| Rounds | R1 **TECH BLITZ**, R2 **DECODE THE DOMAIN**, R3 **TECH TROUBLESHOOTER**, R4 **NEXUS SHOWDOWN**. Sequential, server-controlled; final restricted to shortlisted teams by default. |
| Content | 120 original questions (30 per domain; 10 Basic/R1, 8 Intermediate/R2, 7 Advanced/R3, 5 Expert/R4 per domain), 22 original riddles, 12 original text meme templates |
| Hint system | Participant-triggered; organiser controls enabled/cost/once-or-multiple/automatic-or-on-request. Default: one hint, zero penalty. |
| Team code | Unique `TNX-...` access code, shown to both members, server-validated, unique DB constraint, rate-limited, expiring, revocable and regenerable. Never a substitute for authentication. |
| Security | Separate participant/admin logins, httpOnly cookie sessions, bcrypt hashing, RBAC, hidden admin surface, in-memory rate limiting, full audit trail, forced admin password change |
| Live control | Central server clock, WebSocket activation, identical questions for eligible teams, global pause/resume/end, auto-submit on timeout, reconnect state restoration, confirmation dialogs, announcements |
| Participant workspace | Shared answers/timer, autosave, either member may submit, one final answer per question, conflict prevention, history, hints, break content, results after publication |
| Scoreboard | Private organiser-only live table with R1–R4, total, correct/incorrect/unanswered, completion, active status, submission time and review flag; CSV/PDF export |
| Admin dashboard | 14 sections: Overview, Participant Registrations, Team Management, Question Bank, Answer Key & Explanations, Round Management, Live Competition Monitor, Live Scoreboard, Anti-Cheating Monitor, Riddle & Meme Management, Results, Announcements, Admin Settings, Audit Logs |
| Anti-cheating | Fullscreen/tab/focus/visibility detection only, warning counter, configurable threshold/auto-submit/disqualification policy, manual review and reinstatement, disclosed policy |
| UI | React + TypeScript + Tailwind + Framer Motion + Lucide; navy/black/electric-blue/neon-cyan/violet glassmorphism, animated gradients, circuit patterns, reduced-motion-aware marquee |
| Stack | FastAPI + SQLAlchemy 2.x, SQLite local default / PostgreSQL-ready, WebSockets, Alembic, ReportLab PDF exports, pytest E2E suite, Docker/Render deployment config |

---

## 2. Quick start (local)

### Prerequisites

- Python 3.12+
- Node.js 20+
- Git

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The app initialises `backend/technexus.db` and seeds all content on first startup.

### Frontend (development)

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). The dev server proxies `/api` and `/ws` to port 8000.

### Frontend (production build served by FastAPI)

```powershell
cd frontend
npm run build
```

Then start the backend only and open <http://localhost:8000>. FastAPI serves `frontend/dist` and falls back to the SPA for client routes.

### Health/config checks

- <http://localhost:8000/api/health> → `{"ok": true}`
- <http://localhost:8000/api/public/config> → event identity, schedule, rounds, team size
- <http://localhost:8000/docs> → interactive API reference

---

## 3. Administrator setup (one-time)

Run from `backend` **after the database has been initialised**:

```powershell
.\.venv\Scripts\python.exe -m setup_admins
```

This creates exactly two independent administrator accounts:

- `organiser`
- `coorganiser`

Securely generated temporary passwords are written **only** to the git-ignored file:

```text
backend/.admin_credentials.txt
```

Both accounts are forced to change their temporary password at first login at <http://localhost:8000/organiser/login>. No password appears in the frontend, public APIs, git history or application logs.

---

## 4. Local URLs

| Purpose | URL |
| --- | --- |
| Landing / about / schedule | <http://localhost:8000/> |
| Register a team | <http://localhost:8000/register> |
| Participant login | <http://localhost:8000/login> |
| Participant dashboard | <http://localhost:8000/dashboard> |
| Organiser login | <http://localhost:8000/organiser/login> |
| Organiser dashboard | <http://localhost:8000/organiser> |
| Forced password change | <http://localhost:8000/change-password> |
| Reset request | <http://localhost:8000/reset-password> |
| API docs | <http://localhost:8000/docs> |

---

## 5. Operating the event

1. **Before the event** — log in as an organiser, review **Participant Registrations**, approve only teams where both members have confirmed, and generate/distribute each team's `TNX-...` code privately.
2. **Configure** — use **Admin Settings** for event date/time, schedule, hints, scoring, break and anti-cheating policy. Use **Question Bank** and **Answer Key & Explanations** to review content; export privately with CSV/PDF.
3. **Start a round** — open **Round Management** and press **Start**. The server records one authoritative start timestamp, activates WebSockets, creates sessions for eligible teams and locks all later rounds. Every confirmation is explicit.
4. **Monitor** — use **Live Competition Monitor** and the private **Live Scoreboard**. Scores update on each submission; participants cannot see them until results are published.
5. **Breaks** — after each round, **Riddle & Meme Management** supplies a timed riddle and memes. Guesses are recorded; answers reveal only after expiry and do not affect scores unless a bonus is explicitly enabled.
6. **Pause/resume/end** — global controls affect every team at once. Ending auto-submits saved answers. Future rounds remain locked until the previous one ends.
7. **Final** — only shortlisted teams receive a Round 4 session by default.
8. **Publish** — use **Results** to publish official scores. Participants see their result only after publication.
9. **Export** — CSV/PDF scoreboard and answer-key exports are available from the relevant organiser panels and are admin-only.

### Anti-cheating policy

The browser reports tab visibility, window focus and fullscreen exits using browser APIs only. Each active round tracks a violation counter; organisers configure warning threshold and whether violations trigger auto-submit or review. All events are written to **Audit Logs** and shown in **Anti-Cheating Monitor**. Organisers can review and reinstate teams manually. The policy is disclosed in the participant UI.

---

## 6. Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

The suite contains 27 automated end-to-end tests covering event identity, content integrity, two administrators, forced password change, strict two-member registration, duplicate prevention, confirmation, approval, team-code validation/revocation/regeneration, RBAC, answer hiding, sequential round control, identical synchronized questions, hints, shared answer autosave/conflict prevention, server-side scoring, private scoreboard, violations, pause/resume/end, break content, restricted final, result publication, CSV/PDF exports, WebSocket tokens and logout revocation.

Results are documented in `docs/TEST_RESULTS.md`.

---

## 7. Database and migrations

Local development uses SQLite (`backend/technexus.db`) with foreign keys, WAL and busy timeout enabled. Production should set `DATABASE_URL` to PostgreSQL, for example:

```text
postgresql+psycopg://user:password@host:5432/technexus
```

Alembic is configured in `backend/alembic.ini`; the initial schema migration lives in `backend/migrations/versions/`. On a fresh database the application also calls `Base.metadata.create_all()` for zero-config startup, so migrations are optional for first boot but recommended for upgrades:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Backup/restore guidance is in `docs/DATABASE.md`.

---

## 8. Deployment

See `docs/DEPLOYMENT.md`. Docker, Docker Compose and Render configuration are included.

**No public deployment URL is provided in this repository because no live deployment has been performed.** Deploy it yourself using the included configuration.

---

## 9. Repository layout

```text
technexus-2026/
├── backend/            FastAPI application, DB models, routers, services, tests, admin setup
├── content/            Original questions, riddles and meme templates (JSON)
├── docs/               Manuals, deployment, database and test documentation
├── frontend/           React/TypeScript/Tailwind application
├── scripts/            Backup/restore helper scripts
├── Dockerfile
├── docker-compose.yml
├── render.yaml
└── .env.example
```

The AWSSBG logo is preserved at `frontend/public/assets/awssbg-logo.png` and used in the landing page, navigation, about section, footer, both logins, registration, dashboards and certificates.

---

## 10. Security notices

- Never commit `.env`, `backend/.admin_credentials.txt`, database files or logs.
- Rotate the admin temporary passwords immediately and periodically.
- Set a strong `SECRET_KEY` in production.
- Use HTTPS in production so httpOnly session cookies are marked Secure (`ENVIRONMENT=production`).
- Restrict `CORS_ORIGINS` and `TRUSTED_HOSTS` to the event domain.
- Store the database and credentials outside the web root and back them up privately.
