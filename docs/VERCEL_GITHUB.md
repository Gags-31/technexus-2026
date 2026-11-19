# Deploy to Vercel from GitHub

This repository is ready for Vercel Git integration. The root `vercel.json` defines two services in one Vercel project:

| Service | Root | Purpose |
| --- | --- | --- |
| `web` | `frontend/` | Vite + React participant/organiser UI |
| `api` | `backend/` | FastAPI + WebSockets + PostgreSQL |

Both services are exposed on the same domain, so the browser uses same-origin `/api` and `/ws` calls. No CORS configuration is required for the app itself.

## Import steps

1. Push the latest commit to `master`.
2. In Vercel, choose **Add New → Project** and import `Gags-31/technexus-2026`.
3. Keep Team = **Gagan's projects**, Project Name = `technexus-2026`, Root Directory = repository root.
4. Vercel will detect **Services**. Choose **Import multi-service project**.
5. Add environment variables before deploying (see below).
6. Click **Deploy**. Every future push to `master` will redeploy automatically.

## Required environment variables (Production)

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
SECRET_KEY=<long-random-secret>
ENVIRONMENT=production
TRUSTED_HOSTS=<your-vercel-domain>,*.vercel.app
CORS_ORIGINS=https://<your-vercel-domain>
```

Use a pooled Neon/PostgreSQL URL for `DATABASE_URL`. Do **not** use SQLite on Vercel: the filesystem is read-only except `/tmp`.

After the first deployment, set `CORS_ORIGINS` and `TRUSTED_HOSTS` to your real Vercel domain and redeploy.

## One-time database and admin setup

Vercel has no persistent shell, so run these from your own machine using the production database URL:

```powershell
# From backend/
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m setup_admins
```

`setup_admins` writes the two temporary passwords to `backend/.admin_credentials.txt` locally. Copy them into a private password manager; they are gitignored. Log in at `/organiser/login` and change both passwords at `/change-password`.

If the accounts already exist and the passwords are lost:

```powershell
.\.venv\Scripts\python.exe -m reset_admin_passwords --yes
```

## Important production notes

- Vercel WebSockets are supported, but a connection is pinned to one function instance and closes at the function `maxDuration`. The participant client already reconnects automatically.
- The authoritative competition state is in PostgreSQL, but live WebSocket fan-out currently uses an in-memory hub. If Vercel scales to multiple instances, add Redis pub/sub so all participants receive the same events. For a single-institution event with modest concurrency, one instance is usually sufficient.
- Use a paid/always-on database provider. Free Postgres instances may sleep and break live timing.
- Keep `render.yaml` for reference; Vercel ignores it.
