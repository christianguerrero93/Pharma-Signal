# Pharma Signal

Pharma Signal is a pharma-native DSP command center prototype focused on the gap between media activation and business impact.

It is not positioned as a generic DSP clone. The product direction is to connect the pieces healthcare media teams usually stitch together manually:

- HCP, DTC, contextual, behavioral, and geography-based audience planning
- Supply path quality across SSPs and curated PMPs
- Data-cost visibility and working-media efficiency
- Outcome-aware bid logic
- GA4 and downstream engagement signals
- Rx / script-lift style measurement planning
- Compliance, audit, and no-PHI guardrails

## Current build

This repository currently contains a Netlify-ready React + Vite MVP dashboard.

### Included modules

- Pharma Signal landing and product narrative
- Campaign intelligence cards
- Supply partner scorecard for PubMatic, Magnite, OpenX, and Index Exchange
- Prototype bid decision formula
- Architecture module cards
- Product roadmap
- Netlify deployment config

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

## Product roadmap

### MVP

- Static command center UI
- Supply path scoring logic
- Campaign intelligence cards
- Bid logic explanation
- Netlify hosting

### Next build

- CSV/XLSX upload for campaign performance and supply reports
- Measurement planner for conversions, exposed/control sizing, and statistical confidence
- Bid simulator with adjustable audience value, supply quality, data cost, frequency, and outcome signal
- GA4 connector scaffold
- SSP deal QA module
- Partner adapter stubs for Swoop/Crossix-style measurement, DeepIntent-style Rx reporting, verification partners, and SSPs

### Long-term DSP architecture

- Next.js or React frontend
- Python FastAPI control plane
- PostgreSQL for campaign, user, and configuration data
- Redis or Aerospike for low-latency bidding state
- ClickHouse or BigQuery for event logs and analytics
- Go/Rust/Java OpenRTB bidder
- Kafka/Flink streaming for impression, click, conversion, and outcome events
- Audit logs, RBAC, privacy-safe measurement, and no PHI storage

## Positioning

Pharma Signal is designed around one commercial question:

> Did this media buy reach the right verified audience, through the right supply path, at the right cost, with enough measurement power to prove business impact?
