# Pharma Signal Enterprise DSP CEO Blueprint

## CEO thesis

Pharma Signal should not be sold as another dashboard. It should be positioned as the operating system for pharma media investment: planning, audience quality, supply-path economics, bid decisioning, measurement readiness, approvals, and proof of business impact in one platform.

The executive promise:

> Every dollar should know why it was spent, who it reached, whether it passed compliance, which supply path carried it, what outcome it was expected to influence, and whether the campaign had enough power to prove impact.

## Enterprise product lines

### 1. Control Plane

The control plane is where enterprise clients manage:

- organizations
- brands
- campaigns
- line items
- budgets
- frequency caps
- audience partitions
- creative approval state
- partner routing
- activation status
- audit history

Business value: makes Pharma Signal feel like infrastructure, not a reporting add-on.

### 2. Auction Gateway

The OpenRTB auction gateway should become the real-time decisioning engine.

Before a bid is priced, the gateway checks:

- campaign state
- line item pacing
- audience partition
- creative MLR approval
- no-PHI payload rules
- consent signal
- geo approval
- frequency cap pressure
- supply-path approval
- bid floor economics

Business value: allows pharma teams to scale programmatic buying without losing compliance control.

### 3. Supply Intelligence

Supply intelligence should expose where money is actually creating quality reach and outcome value.

Signals:

- SSP
- PMP deal
- seller path
- viewability
- fraud risk
- match rate
- working-media ratio
- outcome score
- script-lift contribution
- verified HCP/DTC reach

Business value: turns supply from a commodity into a measurable business lever.

### 4. Measurement Readiness

The platform should distinguish between:

- board-ready lift claims
- directional campaign learning
- underpowered studies

Signals:

- expected conversions
- exposed/control sample
- minimum detectable lift
- power score
- control stability
- flight length
- audience reset risk

Business value: prevents overclaiming and helps clients understand when more budget or time is needed.

### 5. Portfolio Optimizer

The optimizer should recommend budget movement across brands and channels based on:

- measurement power
- pacing
- priority
- supply quality
- conversion depth
- compliance constraints
- working-media efficiency

Business value: gives leadership a defensible reason to move dollars, not just a performance table.

### 6. Approval and Audit System

Enterprise pharma cannot operate without governance.

The platform needs:

- role-based access
- approval requests
- MLR/compliance decisions
- activation gating
- immutable audit logs
- vendor share permissions
- client-safe read-only links

Business value: creates trust with brands, legal, compliance, and procurement.

## Moat

The moat is not simply bidding. Generic DSPs can bid.

The moat is the connection between:

1. healthcare-specific audience rules
2. supply quality
3. data-cost visibility
4. outcome measurement
5. compliance approval
6. business-case storytelling

DeepIntent and similar platforms win because they make pharma value easy to explain. Pharma Signal should push further by making the entire investment decision explainable before the campaign launches.

## Technical architecture

### Frontend

- React / Vite now
- Next.js later if server rendering, auth middleware, and enterprise routing become needed
- Role-based dashboards
- Executive, trader, analyst, compliance, client, and vendor views

### Control plane backend

- FastAPI
- MongoDB currently through existing Emergent backend
- Postgres recommended for production campaign configuration
- RBAC
- approvals
- audit logs
- campaign and line-item CRUD

### Bidder

- Current: Python/TypeScript simulation
- Production: Go, Rust, or Java
- OpenRTB request parsing
- sub-120ms decision budget
- Redis/Aerospike for frequency and pacing state
- Kafka/Flink for auction event stream

### Warehouse

- BigQuery or Snowflake
- impression, click, conversion, exposure, control, and measurement tables
- partner delivery files
- GA4 events
- verification feeds
- model features

### ML and optimization

- Python model training
- supply quality prediction
- outcome propensity
- bid shading
- frequency saturation
- budget reallocation
- measurement power forecast

## Commercial packaging

### MVP buyer

- pharma media teams
- healthcare agencies
- brand analytics leaders
- programmatic investment teams

### First commercial wedge

Do not start by selling a full bidder. Start with:

> Pharma DSP Intelligence Layer: outcome-aware planning, supply scoring, measurement readiness, and budget optimization.

Then expand into activation and bidding.

### Enterprise pitch

Pharma Signal helps pharma brands answer:

- Why this audience?
- Why this supply partner?
- Why this budget?
- Why this frequency?
- Can we prove lift?
- What should we scale or cut?
- What can we safely activate?

## Next 90 days

1. Connect frontend to enterprise API client.
2. Persist enterprise v2 API to Mongo/Postgres.
3. Add campaign and line-item creation UI.
4. Add CSV/XLSX ingestion for delivery files.
5. Add SSP deal QA workflow.
6. Build a real auction event table.
7. Add authentication across frontend and backend.
8. Start a low-latency bidder service in Go or Rust.
9. Add warehouse schema and seed SQL.
10. Package the board narrative as an exportable client deck/report.
