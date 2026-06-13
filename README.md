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

1. A Netlify-ready React + Vite frontend.
2. The existing Emergent/Mongo backend with auth, seeded data, dashboard APIs, RTB simulation, CSV upload, live bid stream, AI recommendations, MLR/creative review, frequency intelligence, and vendor shares.
3. A new enterprise API layer with CEO dashboard, board narrative, OpenRTB auction evaluation, portfolio optimizer, measurement plans, approvals, and audit.
4. Warehouse schema and sample executive queries.
5. Docker Compose stack for local enterprise development.
6. GitHub Actions CI for frontend and enterprise backend smoke testing.

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

## Netlify deployment

Connect this repository to Netlify and use:

- Build command: `npm run build`
- Publish directory: `dist`

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
