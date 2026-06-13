# Pharma Signal

Pharma Signal is a pharma-native DSP command center prototype focused on the gap between media activation and business impact.

It is not positioned as a generic DSP clone. The product direction is to connect the pieces healthcare media teams usually stitch together manually:

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

## What is included now

This repository contains a Netlify-ready React + Vite application with a typed DSP simulation layer.

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

- `src/types.ts` — DSP domain types
- `src/data/dsp.ts` — modeled campaign, audience, supply, pacing, compliance, and integration data
- `src/data/openRtbSamples.ts` — sample pharma OpenRTB auction requests
- `src/lib/dspEngine.ts` — supply scoring, working-media ratio, bid decisioning, pacing, and measurement logic
- `src/lib/openRtb.ts` — pharma-safe OpenRTB auction simulator and bid response builder
- `src/lib/budgetOptimizer.ts` — portfolio budget recommendation engine
- `src/lib/controlPlane.ts` — approval and audit-trail logic
- `src/connectors/partnerAdapters.ts` — mocked GA4, SSP delivery, and outcome-measurement connectors
- `docs/dsp-architecture.md` — production architecture blueprint
- `docs/integration-roadmap.md` — phased build roadmap
- `.env.example` — environment variable template for future live connectors

## Local development

```bash
npm install
npm run dev
```

## Production build

```bash
npm run build
npm run preview
```

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

### Phase 2: Data ingestion

- CSV/XLSX upload for campaign delivery
- GA4 Data API connector
- SSP delivery imports
- Audience metadata validation
- Partner deal QA module

### Phase 3: Backend control plane

- FastAPI or Node API
- PostgreSQL campaign configuration
- Auth and RBAC
- Audit logs
- Approval workflow

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
