# Pharma Signal DSP Architecture

Pharma Signal is structured as a pharma-native DSP command center first, with clear service boundaries for a production bidder later.

## Product modules

### 1. Campaign control plane

Owns campaign setup, line items, budgets, frequency caps, target KPIs, approval state, partner routing, and audit history.

Recommended production stack:

- FastAPI or Node API
- PostgreSQL for campaign and user configuration
- Role-based access control
- Immutable audit log table
- Approval workflow for sensitive campaign changes

### 2. Audience intelligence

Owns HCP target lists, modeled DTC audiences, contextual taxonomy, GA4 engagement pools, geography, and frequency eligibility.

Guardrails:

- No PHI storage
- Keep HCP and consumer audiences partitioned
- Store activation metadata, not sensitive patient attributes
- Require audience source, refresh date, owner, and use-case notes

### 3. OpenRTB bidder

The frontend currently includes a typed bid-scoring engine. In production this should move into a low-latency bidder.

Recommended production stack:

- Go, Rust, or Java service
- OpenRTB 2.5 / 2.6 parser
- Redis or Aerospike for frequency and pacing state
- Kafka for bid, impression, click, and conversion events
- Feature flags for campaign-specific bid logic

Bid model inputs:

- Base CPM
- Audience match
- Supply score
- Working-media ratio
- Floor CPM
- Viewability / fraud risk
- Frequency pressure
- Outcome signal
- Contextual relevance

### 4. Supply path optimization

Scores supply before scale. The current app models PubMatic, Magnite, OpenX, Index Exchange, and endemic health inventory.

Production checks:

- ads.txt / app-ads.txt validation
- sellers.json validation
- SupplyChain Object parsing
- Deal ID QA
- Seat / wseat QA
- Domain and app bundle quality
- Viewability, fraud, IVT, and brand safety feeds

### 5. Measurement planner

Forecasts whether the campaign is powered enough to support lift or outcome claims.

Inputs:

- Budget
- Expected CPA
- Base CPM
- Exposed impressions
- Control size
- Observed conversion rate
- Minimum detectable lift

Output:

- Power score
- Directional vs measurement-ready recommendation
- Whether to increase budget, time, event volume, or control quality

### 6. Partner adapters

Current mocked adapters live in `src/connectors/partnerAdapters.ts`. Replace them with real connectors as the product matures.

Priority connectors:

- GA4 Data API
- SSP delivery files / APIs
- Swoop-style audience import
- Crossix-style outcome measurement
- IAS / DoubleVerify verification feeds
- BigQuery / Snowflake warehouse sync

## Data flow

1. Planner creates campaign and audience strategy.
2. Supply partners and deals are QA-scored.
3. Bidder receives OpenRTB bid request.
4. Bid engine checks audience match, supply score, floor price, frequency, and outcome signal.
5. Winning bid events stream into Kafka.
6. Warehouse stores aggregated spend, impressions, clicks, conversions, and outcome reads.
7. Measurement planner determines whether lift claims are statistically credible.
8. Optimization model updates bid multipliers, supply routes, and pacing rules.

## Production hardening checklist

- Add auth and RBAC
- Add backend API
- Add persistent database
- Add audit logs
- Add CI/CD build validation
- Add unit tests for bid logic
- Add real GA4 connector
- Add CSV/XLSX ingestion
- Add warehouse sink
- Add OpenRTB bidder service
- Add privacy review before any healthcare audience activation
