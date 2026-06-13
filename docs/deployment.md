# Deploying Pharma Signal

Pharma Signal is two deployables:

1. **Frontend** — the Vite/React Command OS (`src/`), a static site (Netlify, Vercel, or any static host).
2. **Full DSP API** — `backend/full_dsp_server.py`, a FastAPI service packaged as a container (`backend/Dockerfile`).

The frontend reaches the backend through the `VITE_FULL_DSP_API_URL` build-time
environment variable. Deploy the backend first, then point the frontend at it.

---

## 1. Deploy the backend (Full DSP API)

The service is a single FastAPI app with SQLite persistence. It binds to the
host-provided `$PORT`, exposes `GET /health` for health checks, and stores its
database at `FULL_DSP_DB` (default `/data/pharma_signal_dsp.db` in the image).

### Option A — Render (one-click blueprint)

A `render.yaml` blueprint is included. In Render: **New → Blueprint**, pick this
repo, and it provisions a Docker web service with a 1 GB persistent disk mounted
at `/data` (so campaigns/audiences survive redeploys) and a `/health` check.

Set these in the Render dashboard:

| Variable | Value |
| --- | --- |
| `FULL_DSP_DEV_PASSWORD` | a real seed password (replaces `pharma-signal-local`) |
| `FULL_DSP_JWT_SECRET` | a strong random string used to sign login JWTs |
| `FULL_DSP_DB` | `/data/pharma_signal_dsp.db` (already set by the blueprint; ignored if `DATABASE_URL` is set) |
| `DATABASE_URL` | *(optional)* `postgresql://user:pass@host:5432/db` to use Postgres instead of SQLite |

Your API URL will look like `https://pharma-signal-api.onrender.com`.

### Option B — any Docker host (Railway, Fly.io, Cloud Run, ECS, a VM)

```bash
# build from the backend/ directory
docker build -t pharma-signal-api ./backend

# run (the host sets $PORT; defaults to 8090). Mount a volume for persistence.
docker run -p 8090:8090 \
  -e PORT=8090 \
  -e FULL_DSP_DEV_PASSWORD=change-me \
  -e FULL_DSP_DB=/data/pharma_signal_dsp.db \
  -v pharma_signal_data:/data \
  pharma-signal-api
```

- **Railway / Fly.io**: point them at `backend/Dockerfile`; they inject `$PORT` automatically.
- **Persistence**: always mount a volume/disk at the directory holding `FULL_DSP_DB`. Without it, the SQLite file is ephemeral and resets on redeploy.

### Verify

```bash
curl https://YOUR-API-HOST/health
# {"status":"ok","service":"pharma-signal-full-dsp"}
```

---

## 2. Deploy the frontend and point it at the backend

The frontend reads `VITE_FULL_DSP_API_URL` at **build time**, so it must be set
in the host's build environment (not at runtime).

### Netlify (config already in `netlify.toml`)

1. Connect the repo. Build command `npm run build`, publish directory `dist` (already configured).
2. **Site settings → Environment variables**, add:
   - `VITE_FULL_DSP_API_URL = https://pharma-signal-api.onrender.com` (your backend URL)
   - `VITE_FULL_DSP_DEV_PASSWORD = <seed password>` (optional; only prefills the login field)
3. Trigger a deploy. The SPA redirect in `netlify.toml` handles client-side routing.

### Vercel / other static hosts

Same idea: set `VITE_FULL_DSP_API_URL` in the project's environment variables, build with `npm run build`, serve `dist/`.

> Changing `VITE_FULL_DSP_API_URL` requires a **rebuild** — Vite inlines it into the bundle.

---

## 3. Database: SQLite or Postgres

The Full DSP API stores data through a small abstraction (`backend/storage.py`):

- **Default — SQLite.** Zero config. The file lives at `FULL_DSP_DB`; mount a disk there to persist it.
- **Postgres.** Set `DATABASE_URL=postgresql://user:pass@host:5432/db` and the same code runs against Postgres (via `psycopg`, included in the image). Schema is created on first boot. Recommended for multi-instance / production deployments.

On Render you can add a managed Postgres and wire its connection string into `DATABASE_URL`.

## 4. Authentication

Login issues an **HS256 JWT** (signed with `FULL_DSP_JWT_SECRET`, stdlib `hmac` — no
heavy crypto dependency) and passwords are hashed with **bcrypt**. Endpoints enforce
**role-based access** (`admin`, `trader`, `analyst`): campaign/line-item/audience/deal
writes require `admin` or `trader`; MLR creative review requires `admin` or `analyst`.
Always set a strong `FULL_DSP_JWT_SECRET` in production.

## 5. CORS

The backend already sends permissive CORS headers
(`allow_origins=["*"]`), so the static frontend can call it cross-origin from
Netlify/Vercel out of the box. To lock it down, restrict the origins in
`full_dsp_server.py`'s `CORSMiddleware` to your frontend domain(s).

---

## 6. Local full stack

```bash
# backend
cd backend && pip install -r requirements-full-dsp.txt
uvicorn full_dsp_server:app --reload --port 8090

# frontend (in another shell)
npm install && npm run dev   # reads VITE_FULL_DSP_API_URL, defaults to http://localhost:8090
```

Seeded dev logins (password `pharma-signal-local`): `admin@pharmasignal.local`,
`trader@pharmasignal.local`, `analyst@pharmasignal.local`.
