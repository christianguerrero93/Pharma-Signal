# Pharma Signal — Deployment Manual

A complete, click-by-click runbook to take Pharma Signal from repository to a live,
internet-reachable application, then keep it deploying automatically.

Pharma Signal has **two deployables**:

| Piece | What it is | Where it runs |
| --- | --- | --- |
| **Backend** (`backend/full_dsp_server.py`) | FastAPI DSP API, container (`backend/Dockerfile`) | Render (or any Docker host) |
| **Frontend** (`src/`) | Vite/React "Command OS", static site | Netlify (or any static host) |

The frontend reaches the backend via the build-time variable
`VITE_FULL_DSP_API_URL`. **Deploy the backend first**, then point the frontend at it.

---

## 0. Prerequisites

- The repo on GitHub: `christianguerrero93/Pharma-Signal` ✅
- A **Render** account — https://render.com (sign in with GitHub)
- A **Netlify** account — https://app.netlify.com (sign in with GitHub)
- ~15 minutes

No local tooling is required — both hosts build from the repo.

---

## 1. Backend + database on Render

1. **dashboard.render.com → New + → Blueprint.**
2. Pick the **`Pharma-Signal`** repo → **Connect**. Render reads `render.yaml` and
   proposes: a Postgres database (`pharma-signal-db`) and a Docker web service
   (`pharma-signal-api`).
3. **Apply / Create.** First build runs `backend/Dockerfile` (~3–4 min).
   `DATABASE_URL` and `FULL_DSP_JWT_SECRET` are wired automatically.
4. Open **`pharma-signal-api` → Environment** and set:

   | Key | Value |
   | --- | --- |
   | `FULL_DSP_DEV_PASSWORD` | a password you choose (this is your login) |
   | `PUBLIC_BASE_URL` | the service URL Render shows, e.g. `https://pharma-signal-api.onrender.com` |
   | `CORS_ORIGINS` | `*` for now (locked down in step 3) |

5. **Verify:** open `https://YOUR-API.onrender.com/health` →
   `{"status":"ok","service":"pharma-signal-full-dsp","storage":"postgres"}`.

> **Copy your API URL** — you need it next.

### Alternative: any Docker host (Railway / Fly.io / Cloud Run / VM)
Point it at `backend/Dockerfile` (the host sets `$PORT`). Add a Postgres add-on and set
`DATABASE_URL`. Mount a volume at `FULL_DSP_DB`'s directory only if you stay on SQLite.

---

## 2. Frontend on Netlify

1. **app.netlify.com → Add new site → Import an existing project → GitHub →
   `Pharma-Signal`.**
2. Build settings auto-fill from `netlify.toml` (`npm run build`, publish `dist`). Leave them.
3. **Add environment variable** before deploying:

   | Key | Value |
   | --- | --- |
   | `VITE_FULL_DSP_API_URL` | your Render API URL from step 1, e.g. `https://pharma-signal-api.onrender.com` |

4. **Deploy site.** You'll get `https://YOUR-SITE.netlify.app`.

> `VITE_*` is inlined at **build time** — changing it later requires a redeploy.

---

## 3. Connect the two

1. Render → `pharma-signal-api` → **Environment** → set
   `CORS_ORIGINS = https://YOUR-SITE.netlify.app` (exact origin, `https://`, no trailing
   slash) → **Save** (the API restarts).

---

## 4. Log in & verify

1. Open `https://YOUR-SITE.netlify.app`.
2. Log in:
   - **Email:** `admin@pharmasignal.local`
   - **Password:** your `FULL_DSP_DEV_PASSWORD`
3. Smoke test:
   - **Campaigns** → create a campaign.
   - **Connectors** → **Sync** the "SSP Delivery" connector.
   - **Reporting** → the badge flips to **live**.

Other seeded roles (same password): `trader@pharmasignal.local` (build/buy),
`analyst@pharmasignal.local` (MLR review). Change `FULL_DSP_DEV_PASSWORD` and redeploy
the backend to rotate.

---

## 5. Turn on automatic deploys (CI-gated)

Every merge to `main` runs CI; on green, the **Deploy** workflow redeploys both
services and health-checks the backend. The **Keep-alive** workflow pings `/health`
every ~10 min so the free tier doesn't cold-start.

Add three repo secrets — **GitHub → repo Settings → Secrets and variables → Actions →
New repository secret**:

| Secret | Where to get it |
| --- | --- |
| `RENDER_DEPLOY_HOOK_URL` | Render → `pharma-signal-api` → Settings → **Deploy Hook** |
| `NETLIFY_BUILD_HOOK_URL` | Netlify → Site config → Build & deploy → **Build hooks → Add build hook** |
| `HEALTH_CHECK_URL` | `https://YOUR-API.onrender.com/health` |

Then (recommended) disable the hosts' native auto-deploy so this CI-gated flow is the
single source of truth:
- Render → Settings → Build & Deploy → **Auto-Deploy: No**
- Netlify → Site config → Build & deploy → Continuous deployment → **Stop builds**

Trigger manually anytime: **Actions tab → Deploy → Run workflow**.

---

## 6. Production hardening (recommended)

- **Secrets:** strong `FULL_DSP_DEV_PASSWORD`; let Render generate `FULL_DSP_JWT_SECRET`.
- **CORS:** set `CORS_ORIGINS` to your exact frontend origin(s), never `*` in prod.
- **Database:** use the managed Postgres (the blueprint already does). Take periodic backups.
- **OpenRTB:** set `PUBLIC_BASE_URL` so win-notice (`nurl`) / billing (`burl`) callbacks resolve.
- **Custom domain:** add it in Netlify (frontend) and/or Render (API); update `CORS_ORIGINS`
  and `VITE_FULL_DSP_API_URL` accordingly and redeploy.

---

## 7. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Login spins / "cannot reach API" | `VITE_FULL_DSP_API_URL` wrong/missing → fix in Netlify, **redeploy** |
| Login OK but API calls fail (CORS error in console) | `CORS_ORIGINS` ≠ Netlify origin exactly → fix on Render |
| `/health` shows `"storage":"sqlite"` unexpectedly | `DATABASE_URL` not set → check Render env / blueprint DB |
| First request slow (~30–50s) | Render free tier cold start → keep-alive helps; upgrade to remove |
| Deploy workflow red | health gate failed → check Render deploy logs; the release isn't healthy |

---

## 8. Rollback

- **Render:** service → **Events / Deploys** → pick a previous successful deploy → **Rollback**.
- **Netlify:** **Deploys** → pick a prior deploy → **Publish deploy**.
- **Git:** revert the offending commit on `main`; CI + Deploy will ship the revert.

---

## Reference — environment variables

| Variable | Service | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | backend | Postgres connection (unset = SQLite) |
| `FULL_DSP_DB` | backend | SQLite path when no `DATABASE_URL` |
| `FULL_DSP_DEV_PASSWORD` | backend | Seed users' password |
| `FULL_DSP_JWT_SECRET` | backend | Signs login JWTs |
| `FULL_DSP_JWT_TTL` | backend | JWT lifetime seconds (default 43200) |
| `CORS_ORIGINS` | backend | Allowed browser origins (`*` or CSV) |
| `PUBLIC_BASE_URL` | backend | Base for OpenRTB nurl/burl callbacks |
| `PORT` | backend | Bind port (host-provided) |
| `VITE_FULL_DSP_API_URL` | frontend (build) | Backend URL the UI calls |
| `RENDER_DEPLOY_HOOK_URL` | GitHub secret | Auto-deploy: trigger Render |
| `NETLIFY_BUILD_HOOK_URL` | GitHub secret | Auto-deploy: trigger Netlify |
| `HEALTH_CHECK_URL` | GitHub secret | Deploy health gate + keep-alive |
