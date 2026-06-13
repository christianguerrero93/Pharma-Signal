# Pharma Signal Product Roadmap

## Product thesis

Pharma Signal should become a pharma-native DSP intelligence layer that helps healthcare media teams make better buying decisions before and during activation.

The platform should answer:

1. Who are we trying to reach?
2. Which supply paths create verified value?
3. How much working media is lost to data and platform costs?
4. Are we bidding toward attention, verified reach, and business impact?
5. Do we have enough measurement power to prove lift?
6. Can the recommendation be explained in a client-safe, MLR-conscious way?

## Core product pillars

### 1. Audience intelligence

Inputs:

- HCP target lists
- NPI specialty and decile metadata
- Predictive patient audiences
- Contextual condition signals
- Geography and retail proximity
- GA4 engagement
- Historical campaign performance

Outputs:

- Audience quality score
- Reachable universe estimate
- Frequency pressure estimate
- Audience expansion recommendation
- HCP vs DTC split guidance

### 2. Supply path optimization

Inputs:

- SSP
- Deal ID
- PMP type
- Placement environment
- Viewability
- Fraud / IVT
- Win rate
- CPM
- Data cost
- Match rate
- Engagement rate

Outputs:

- Supply path score
- Working media efficiency estimate
- Bid multiplier recommendation
- Deal QA warnings
- Scale / hold / suppress recommendation

### 3. Outcome-aware bidding

Prototype decision logic:

```text
Bid = BaseCPM
  × AudienceValue
  × SupplyQuality
  × OutcomeSignal
  × FrequencyControl
  × DataCostGuardrail
```

Longer-term components:

- Brand-level bid settings
- Audience-level value weights
- SSP-level quality weights
- Inventory-level exclusions
- Frequency caps
- Pacing logic
- Rx / conversion signal weighting
- Budget reallocation engine

### 4. Measurement planner

The measurement planner should estimate whether a campaign can credibly prove impact.

Inputs:

- Spend
- CPM
- Expected impressions
- Expected reach
- Baseline conversion rate
- Expected lift
- Exposed group size
- Control group size
- Minimum detectable effect

Outputs:

- Estimated conversions
- Statistical confidence warning
- Recommended budget
- Recommended flight length
- Measurement feasibility score

### 5. Compliance and privacy

Guardrails:

- No PHI storage
- No patient-level reporting in the UI
- Role-based access control
- Audit logs for changes
- Partner-level data contracts
- MLR-safe wording for client-facing exports
- Aggregated reporting thresholds

## Near-term build sequence

### Sprint 1: Hostable MVP

Status: started.

- React/Vite dashboard
- Netlify config
- Product narrative
- Supply partner scoring UI
- Campaign signal cards
- Architecture cards

### Sprint 2: Interactive calculators

- Build measurement planner form
- Build estimated conversions logic
- Build frequency calculator
- Build bid multiplier simulator
- Add CSV export of recommendations

### Sprint 3: Data ingestion

- CSV/XLSX campaign upload
- Schema validation
- Mapping step for spend, impressions, clicks, conversions, supply source, audience, placement, date
- In-browser prototype scoring

### Sprint 4: Backend control plane

- FastAPI service
- PostgreSQL schema
- Campaign, partner, audience, and measurement tables
- API routes for scoring and recommendations

### Sprint 5: DSP simulation layer

- OpenRTB bid request schema
- Bid response simulator
- SSP adapter stubs
- Pacing and budget allocation logic
- Event logging model

## Long-term integrations

- GA4 Data API
- Swoop-style predictive audience imports
- Crossix-style exposed/control measurement imports
- DeepIntent-style Rx lift reporting imports
- PubMatic, Magnite, OpenX, Index Exchange deal QA
- IAS, DoubleVerify, Moat, HUMAN verification imports
- Snowflake / BigQuery warehouse exports
