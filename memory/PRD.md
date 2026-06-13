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

### Iteration 1 — Core MVP
- ✅ Backend `/api/dashboard/overview`, `/campaigns` (GET/POST), `/audiences`, `/pmps`, `/data-cost`, `/ga4`, `/script-lift`, `/vendors`, `/rtb/simulate`, `/ai/recommendations` (streaming Claude Sonnet 4.5), `/upload/{dataset}`, `/admin/reseed`
- ✅ Idempotent seed (7 campaigns, 8 audiences, 8 PMPs, 7 channels GA4/data-cost, 12-week script lift series, vendor aggregates)
- ✅ Executive Dashboard, Campaigns list + Builder, Audience Scorer, PMP Scorecard (killer feature), Data Cost view, GA4 Engagement, Script Lift, RTB Simulator, AI Recommendations, Vendor Reports, Data Upload
- ✅ Bug fix: CSV upload now has per-dataset schema validation (rejects malformed rows with 400) + defensive reads

### Iteration 2 — Next Action Items ("add all")
- ✅ **Dashboard filters** — brand / indication / campaign_type filtering via `/api/dashboard/overview?brand=&indication=&campaign_type=`; UI has pill buttons + dropdowns + clear
- ✅ **Campaign drill-down** — `/api/campaigns/{id}` returns campaign + linked audiences + linked PMPs + creatives + computed performance; UI at `/campaigns/:id` with KPI cards, setup grid, linked-audiences and linked-PMPs sections, creatives gallery
- ✅ **Per-campaign linking** — seeded campaigns include `audience_ids` + `pmp_ids`. PATCH `/api/campaigns/{id}` updates links. UI dialog lets users multi-select audiences & PMPs to link
- ✅ **RTB scenarios save/compare** — `/api/scenarios` CRUD; UI saves named scenarios after a run, lists all in a comparison table, click-to-load, trash to delete
- ✅ **MLR Creative Review workflow** — `/api/creatives` GET/POST and PATCH for status; UI `/mlr` page with Pending/Approved/Rejected tabs and inline approve/reject + reviewer notes
- ✅ **Live OpenRTB Bid Stream (simulated)** — `/api/live/bid-stream` SSE endpoint streams ~40 realistic bid events; UI `/live` page shows live table with vendor/channel/audience/match/decision and live KPIs (status, requests, win rate, avg bid)
- ✅ **Vendor PDF export** — `/vendors` cards now have an Export PDF button that opens a print-friendly scorecard with deal-level table and strategic note, triggers `window.print()` for save-as-PDF

## Prioritized Backlog
- **P1** Filtering on dashboard by brand / indication / campaign type ✅
- **P1** Detail drill-down (clicking a campaign opens full performance) ✅
- **P1** Persist RTB simulation runs and compare scenarios ✅
- **P2** Authentication (JWT or Emergent Google OAuth) — deferred, needs playbook + user preference
- **P2** Per-campaign attached audiences/PMPs (relational linking) ✅
- **P2** Export reports as PDF ✅ (vendor scorecard)
- **P3** Real OpenRTB integration / live exchange connectors — simulated stream delivered
- **P3** MLR creative review workflow with version history ✅
- **P3** Frequency intelligence per HCP target list

## Test Credentials
N/A — no authentication implemented (open demo access). Auth is the only deferred Next Action Item.
