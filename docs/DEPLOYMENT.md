# TECHNEXUS 2026 — Deployment Guide

No live deployment has been performed, so **no public URL is provided**. The project includes Docker, Docker Compose and Render configuration for a real deployment.

## Production checklist

1. Set a strong `SECRET_KEY` (32+ random characters). Never reuse the development default.
2. Set `ENVIRONMENT=production` so session cookies get the `Secure` flag.
3. Use PostgreSQL, not SQLite: `DATABASE_URL=postgresql+psycopg://user:password@host:5432/technexus`.
4. Restrict `CORS_ORIGINS` and `TRUSTED_HOSTS` to your event domain.
5. Terminate TLS at a reverse proxy or platform load balancer.
6. Run administrator setup once against the production database and store the generated credentials in a private secret store. Delete local copies securely after handover.
7. Back up the database before the event and after registration closes. See `docs/DATABASE.md`.
8. Build the frontend and let FastAPI serve `frontend/dist`, or serve it from a CDN with correct `/api` and `/ws` routing.

## Docker

```powershell
docker build -t technexus-2026 .
docker run --rm -p 8000:8000 `
  -e SECRET_KEY="replace-with-a-long-random-secret" `
  -e ENVIRONMENT=production `
  -e DATABASE_URL="sqlite:////data/technexus.db" `
  -v technexus-data:/data `
  technexus-2026
```

Open <http://localhost:8000>. Inside the image, content lives at `/app/content` and the built frontend at `/app/frontend/dist`.

## Docker Compose

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:CORS_ORIGINS = "https://quiz.example.com"
docker compose up -d --build
```

The SQLite database is persisted in the named volume `event-data`. For PostgreSQL, add a `db` service and set `DATABASE_URL` accordingly, or point to a managed database.

## Render

`render.yaml` defines a Docker web service with `generateValue: true` for `SECRET_KEY` and `sync: false` placeholders for database and domain configuration. Connect the repo, supply the environment values in the Render dashboard, then deploy.

## Generic PaaS

Most platforms can run the included Dockerfile with:

- Build command: `docker build .`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`
- Persistent disk or external PostgreSQL for the database

Ensure WebSocket upgrades are enabled at the reverse proxy and that the proxy forwards the `tnx_session` cookie.

## Migrations

On a production database, apply the Alembic schema before or during first boot:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The app also calls `create_all()` on startup for zero-config local use, which is safe for a fresh database.

## Post-deployment verification

1. `GET /api/health` returns `{"ok": true}`.
2. `GET /api/public/config` shows TECHNEXUS 2026 and the correct schedule.
3. Open `/`, `/register`, `/login`, `/organiser/login`.
4. Run `python -m setup_admins` once and change both passwords at first login.
5. Confirm 120 questions, 22 riddles and 12 memes are seeded.
6. Register a test two-member team, confirm both members, approve it, join the lobby and start a round.
7. Verify CSV/PDF exports and WebSocket updates.
