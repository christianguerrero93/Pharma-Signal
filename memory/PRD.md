# PharmaSignal DSP — PRD

## Original Problem Statement
Build a fully-fledged pharma-native Demand-Side Platform (DSP) + Intelligence Layer that solves real pain points:
- Manual stitching of audience strategy, PMP setup, data costs, match rates, supply quality, GA4 engagement, Rx lift
- Data cost eating working media (working media ratio transparency by line item, audience, partner, PMP)
- Shallow PMP performance reporting ("did it spend?" vs. "did it drive engagement, verified reach, Rx lift?")
- Hidden match rates until too late
- Weak CTR-only optimization (vs. engagement quality, verified reach, audience quality, script lift)
- Disconnected HCP / DTC strategies
- Killer feature: **Outcome-Adjusted Supply Score**

## Architecture
- **Backend**: FastAPI + Motor (async MongoDB), seeded demo data on startup, Claude Sonnet 4.5 via `emergentintegrations` for AI insights, streaming SSE for narrative recommendations.
- **Frontend**: React 19 + React Router 7, Recharts, Shadcn UI, Tailwind. Fonts: Manrope (headings), IBM Plex Sans (body), IBM Plex Mono (numeric). Swiss-inspired "Control Room" design system.
- **Database**: MongoDB collections — campaigns, audiences, pmps, ga4, script_lift, data_cost, vendors, seed_meta

## User Personas
- **Pharma Brand / Marketing Lead** — needs executive view, working media %, Rx lift
- **Programmatic Trader** — needs PMP scorecards, RTB bidder tuning, bid decisions
- **Analytics Lead at Agency** — needs vendor value reports, audience quality forecasts
- **Vendor / Sales** — receives outcome-led conversation (Scale/Hold/Reduce)

## Core Requirements (Static)
- Pharma-specific fields: brand, indication, HCP vs DTC, NPI count, specialty, diagnosis, data partner, outcome KPI, MLR status, frequency cap
- Outcome-Adjusted Supply Score formula: `score = verified_reach·22 + engagement·18 + max(lift,0)·4 + working_media·18 + match·18 − data_drag·25 − fraud·60`
- RTB bid formula: `bid = outcome_prob × audience_quality × supply_quality × rx_lift_weight × engagement_quality / data_cost × base_value`
- AI narrative recommendations grounded in live portfolio data
- CSV ingestion for DSP exports, GA4, PMP reports, Crossix/Swoop, script lift, campaigns

## What's Been Implemented (2026-02-13)
- ✅ Backend `/api/dashboard/overview`, `/campaigns` (GET/POST), `/audiences`, `/pmps`, `/data-cost`, `/ga4`, `/script-lift`, `/vendors`, `/rtb/simulate`, `/ai/recommendations` (streaming Claude Sonnet 4.5), `/upload/{dataset}`, `/admin/reseed`
- ✅ Idempotent seed of 7 campaigns, 8 audiences, 8 PMPs, 7 channels GA4/data-cost, 12-week script lift series, vendor aggregates
- ✅ Executive Dashboard with 8 KPI cards, 12-week Script Lift line chart, Top Supply bar chart, AI tease card
- ✅ Campaigns list + Campaign Builder with HCP/DTC conditional fields, channel multi-select, data partner selector
- ✅ Audience Scorer table with match rate, data CPM, working media, Rx relevance, scale/waste risk badges
- ✅ PMP Scorecard ("killer feature") with composed chart (bar + line) and color-coded recommendation badges
- ✅ Data Cost view with stacked spend composition, working media % per line item
- ✅ GA4 Engagement view: sessions / engaged / quality visits / avg duration / conversions
- ✅ Script Lift: exposed vs control time series + weekly lift % chart
- ✅ RTB Simulator with 6 tunable sliders, live formula display, decision (BID/LOW_BID/NO_BID), win rate, simulated 24-request bid stream
- ✅ AI Recommendations page with streaming Claude Sonnet 4.5 output
- ✅ Vendor Value Reports as cards with Scale/Hold/Reduce recos
- ✅ Data Upload page with dataset selector and CSV drop zone

## Prioritized Backlog
- **P1** Filtering on dashboard by brand / indication / campaign type
- **P1** Detail drill-down (clicking a campaign opens full performance)
- **P1** Persist RTB simulation runs and compare scenarios
- **P2** Authentication (JWT or Emergent Google OAuth)
- **P2** Per-campaign attached audiences/PMPs (relational linking)
- **P2** Export reports as PDF
- **P3** Real OpenRTB integration / live exchange connectors
- **P3** MLR creative review workflow with version history
- **P3** Frequency intelligence per HCP target list

## Test Credentials
N/A — no authentication implemented for MVP (open demo access).
