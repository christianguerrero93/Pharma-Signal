# Pharma Signal

Pharma Signal is a pharma-native enterprise DSP foundation focused on the gap between media activation and business impact.

It is not positioned as a generic dashboard or DSP clone. The product direction is to connect the pieces healthcare media teams usually stitch together manually:

- Campaign and line-item planning
- HCP, DTC, contextual, behavioral, geography, and retargeting audience strategy
- Supply path quality across SSPs, curated PMPs, CTV, endemic health, and open web
- Data-cost visibility and working-media efficiency
- Outcome-aware bid logic
- OpenRTB-style auction decisioning
- Portfolio budget optimization
- GA4 and downstream engagement signals
- Rx / script-lift style measurement planning
- Compliance, audit, approvals, and no-PHI guardrails
- Executive dashboard and board-level operating narrative

## What is included now

This repository now contains a full-stack enterprise DSP build path:

1. A Netlify-ready React + Vite frontend — the **Pharma Signal Command OS**, a tabbed
   workbench wired to a functional backend (login, overview, campaigns, audiences,
   creative/MLR, supply & deals, bidder, measurement, optimization, reporting,
   compliance, and audit).
2. `backend/full_dsp_server.py` — the live, SQLite-backed DSP API powering the
   workbench (see capability list below).
3. The existing Emergent/Mongo backend (`server.py`) and enterprise v2 API
   (`enterprise_server.py`) as parallel reference surfaces.
4. Warehouse schema and sample executive queries.
5. Docker Compose stack for local enterprise development.
6. GitHub Actions CI for frontend and enterprise backend smoke testing.

### Full DSP capabilities (DeepIntent-class + pharma-native)

The `full_dsp_server.py` API and the Command OS frontend implement:

- **Campaign & line-item planning** — flights, budgets, pacing modes, frequency caps,
  bulk edit with dry-run, and an append-only audit trail on every mutation.
- **Audience library** — HCP (NPI-level), DTC, lookalike, contextual, and retargeting
  audiences with match-rate, NPI sizing, and **data-cost / working-media transparency**.
- **Reach & frequency forecasting** — diminishing-returns reach curve, achieved
  frequency, % of addressable audience, and data-vs-media spend split.
- **Outcome-aware bid engine** — weighted bid factors, bid shading, single-impression
  auction evaluation, an **OpenRTB bidstream simulator** (win rate, second-price
  clearing, pacing, frequency capping, PHI blocks), and a real **OpenRTB 2.x
  BidRequest→BidResponse** endpoint with win-notice (nurl) and billing (burl) callbacks.
- **Connectors / live feeds** — GA4, SSP delivery, Crossix measurement, and identity
  connectors ingest delivery/engagement/outcome facts; once SSP feeds are present,
  reporting switches from simulated to **live** data. Real feeds POST to an ingest API.
- **Supply path optimization** — blended SPO score (outcome, viewability, match rate,
  working media, fraud, cost) with prioritize / maintain / reduce recommendations,
  plus a PMP / PG / curated **deal marketplace**.
- **MLR creative review** — Medical-Legal-Regulatory workflow with versioning,
  approve / request-changes / reject decisions, ISI checks, and serve-gating.
- **Measurement power planning + closed loop** — script-lift / diagnosis-lift study
  design with a real two-proportion **statistical power** computation, minimum
  detectable lift, and readiness scoring; plus a **Crossix-style closed loop** that
  ingests observed exposed/control conversions and returns measured incremental lift,
  95% CI, p-value, incremental conversions, cost-per-incremental-conversion, and ROAS.
- **Identity resolution** — dedupe overlapping reach across audiences into unique
  addressable reach (NPI-aware, same-type vs cross-type overlap modeling).
- **Portfolio budget optimizer** — efficiency-ranked increase / hold / decrease
  reallocation recommendations.
- **Reporting** — delivery, pacing status, CTR / CVR / CPA / eCPM, and daily series.
- **Compliance & governance** — no-PHI enforcement, consent-at-auction, MLR gating,
  brand-safety findings, a compliance score, and **cross-channel HCP + DTC frequency
  coordination** (the pain point generic DSPs leave to spreadsheets).
- **Security & persistence** — HS256 JWT auth (stdlib-signed), bcrypt password
  hashing, and enforced role-based access (`admin` / `trader` / `analyst`). Storage
  runs on SQLite by default or **Postgres** when `DATABASE_URL` is set, via a single
  abstraction (`backend/storage.py`).
- **AI insights & friendly UI** — an Insights engine reads campaigns, supply, creative,
  frequency, and measurement state and surfaces prioritized next actions. The UI adds an
  onboarding checklist, toast notifications, loading/empty states, and plain-language
  hints for ad-tech/pharma jargon.
- **Channels & targeting** — a channel taxonomy (Display, Video, CTV, Audio, Native,
  DOOH, EHR) with typical-CPM/device metadata, plus per-line-item targeting: devices,
  geos, dayparting, brand-safety tier, and viewability floor. **Targeting actively
  filters the bidder** — the OpenRTB endpoint and bidstream simulator drop impressions
  that fail device/geo/daypart/brand-safety/viewability rules. Creatives render a visual
  preview in the MLR queue.
- **Media planner** — allocate a budget across channels and forecast impressions,
  blended CPM, and unique reach from the CPM taxonomy.
- **Persistent frequency governance** — per-user frequency is persisted across
  bidstream runs (a `frequency_ledger`), so caps carry over and the same NPI/household
  isn't over-exposed; view and reset the state per line item.
- **CSV export** — one-click export of campaigns, audit log, RTB wins, and delivery facts.

### Product experience

- Pharma Signal landing and product narrative
- Campaign command center
- Supply partner scorecard for PubMatic, Magnite, OpenX, Index Exchange, and endemic health supply
- Audience activation model for HCP, DTC, retargeting, and contextual signals
- Bid-decision simulator with bid / throttle / reject logic
- OpenRTB pharma auction gateway with compliance checks before pricing
- Portfolio budget optimizer with increase / hold / decrease recommendations
- Pacing intelligence by campaign
- Measurement-power planner with expected conversions, exposed/control sizing, and minimum detectable lift
- Partner integration module
- Control-plane approvals and audit stream
- Compliance-control module
- Architecture and roadmap sections

### Engineering modules

- `src/types.ts` — frontend DSP domain types
- `src/data/dsp.ts` — modeled campaign, audience, supply, pacing, compliance, and integration data
- `src/data/openRtbSamples.ts` — sample pharma OpenRTB auction requests
- `src/lib/dspEngine.ts` — supply scoring, working-media ratio, bid decisioning, pacing, and measurement logic
- `src/lib/openRtb.ts` — pharma-safe OpenRTB auction simulator and bid response builder
- `src/lib/budgetOptimizer.ts` — portfolio budget recommendation engine
- `src/lib/controlPlane.ts` — approval and audit-trail logic
- `src/api/enterpriseClient.ts` — frontend client for the enterprise API
- `backend/server.py` — existing Mongo-backed DSP API
- `backend/enterprise_server.py` — enterprise v2 DSP API surface
- `backend/ENTERPRISE_README.md` — backend operating notes
- `warehouse/schema.sql` — analytics warehouse schema
- `warehouse/sample_queries.sql` — CEO / analytics queries
- `infra/docker-compose.enterprise.yml` — full local enterprise stack
- `docs/enterprise-ceo-blueprint.md` — CEO-level product and operating blueprint
- `.env.example` — environment variable template

## Run the full DSP backend (powers the Command OS frontend)

The Vite frontend talks to `full_dsp_server.py` on port `8090`:

```bash
cd backend
pip install -r requirements.txt
uvicorn full_dsp_server:app --reload --port 8090
```

Seeded dev users (password `pharma-signal-local`, override with `FULL_DSP_DEV_PASSWORD`):
`admin@pharmasignal.local` (admin), `trader@pharmasignal.local` (trader),
`analyst@pharmasignal.local` (analyst).

Useful full DSP endpoints:

- `POST /api/full/auth/login`
- `GET /api/full/overview`
- `GET /api/full/workbench`
- `POST /api/full/campaign-build`
- `GET /api/full/audiences` · `POST /api/full/audiences/forecast`
- `GET /api/full/creatives` · `POST /api/full/creatives/{id}/review`
- `GET /api/full/deals` · `GET /api/full/supply-paths/optimize`
- `POST /api/full/auction/evaluate` · `POST /api/full/bidstream/simulate`
- `GET /api/full/measurement/plans` · `POST /api/full/measurement/plan`
- `GET /api/full/optimizer/portfolio`
- `GET /api/full/reporting/performance`
- `GET /api/full/compliance/scan` · `GET /api/full/frequency/governance`
- `GET /api/full/audit`

Point the frontend at a hosted backend with `VITE_FULL_DSP_API_URL`.

## Local frontend development

```bash
npm install
npm run dev
```

## Production frontend build

```bash
npm run build
npm run preview
```

## Run the existing Mongo backend

```bash
cd backend
uvicorn server:app --reload --port 8001
```

## Run the enterprise backend

```bash
cd backend
uvicorn enterprise_server:app --reload --port 8080
```

Useful enterprise endpoints:

- `GET /health`
- `GET /api/v2/executive-dashboard`
- `GET /api/v2/board/narrative`
- `GET /api/v2/campaigns`
- `GET /api/v2/supply-paths`
- `POST /api/v2/auction/evaluate`
- `GET /api/v2/optimizer/portfolio`
- `GET /api/v2/measurement/plans`
- `POST /api/v2/approvals`
- `POST /api/v2/approvals/decision`
- `GET /api/v2/audit`

Role is controlled by header for local development:

```bash
curl -H "x-pharma-role: ceo" http://localhost:8080/api/v2/executive-dashboard
```

## Run the local enterprise stack

```bash
docker compose -f infra/docker-compose.enterprise.yml up
```

This starts:

- MongoDB
- Redis
- existing backend on `8001`
- enterprise API on `8080`
- frontend on `5173`

## Deployment (full stack)

See the **[Deployment Manual](docs/DEPLOY_MANUAL.md)** for the full click-by-click
runbook, or **[`docs/deployment.md`](docs/deployment.md)** for reference detail. In short:

1. **Deploy the backend** (`backend/full_dsp_server.py`) as a container — a
   `backend/Dockerfile` and a Render `render.yaml` blueprint are included. It binds
   to `$PORT`, health-checks at `/health`, and persists SQLite at `FULL_DSP_DB`
   (mount a disk/volume there).
2. **Deploy the frontend** to Netlify (build `npm run build`, publish `dist`; the
   `netlify.toml` is already configured) and set the build env var
   `VITE_FULL_DSP_API_URL` to your deployed backend URL so the Command OS can reach it.

```bash
# build and run the backend container locally
docker build -t pharma-signal-api ./backend
docker run -p 8090:8090 -e PORT=8090 -v pharma_signal_data:/data pharma-signal-api
```

### Netlify (frontend)

Connect this repository to Netlify and use:

- Build command: `npm run build`
- Publish directory: `dist`
- Environment variable: `VITE_FULL_DSP_API_URL=https://<your-backend-host>`

The `netlify.toml` file is already included.

## Production DSP roadmap

### Phase 1: Hosted MVP

- Static Netlify-hosted command center
- Typed bid and measurement logic
- Mock connectors
- Pharma-specific product narrative

### Phase 2: Enterprise control plane

- FastAPI campaign and line-item API
- Auth and RBAC
- Approvals
- Audit logs
- Client/vendor permission layers

### Phase 3: Data ingestion

- CSV/XLSX upload for campaign delivery
- GA4 Data API connector
- SSP delivery imports
- Audience metadata validation
- Partner deal QA module
- Verification feed imports

### Phase 4: OpenRTB bidder

- Go / Rust / Java bidder service
- Redis or Aerospike for pacing and frequency state
- Kafka or Flink event streaming
- Bid response generation
- Partner-specific SSP adapters

### Phase 5: Outcome optimization

- Crossix/Swoop-style measurement imports
- Lift-readiness modeling
- Supply-path incrementality comparison
- Automated bid multiplier recommendations
- Budget and frequency optimization

## Positioning

Pharma Signal is designed around one commercial question:

> Did this media buy reach the right verified audience, through the right supply path, at the right cost, with enough measurement power to prove business impact?
