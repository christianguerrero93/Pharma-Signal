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
- ✅ Dashboard, Campaigns, Audience Scorer, PMP Scorecard (killer feature), Data Cost, GA4, Script Lift, RTB Simulator, AI Recommendations, Vendor Reports, Data Upload
- ✅ Idempotent seed (7 campaigns, 8 audiences, 8 PMPs, channels, 12-week script lift)
- ✅ Bug fix: CSV upload schema validation + defensive reads

### Iteration 2 — "Add all"
- ✅ Dashboard filters (brand / indication / campaign_type)
- ✅ Campaign drill-down `/campaigns/:id` + Link Audiences & PMPs dialog
- ✅ Per-campaign linking (`audience_ids`, `pmp_ids` on campaigns)
- ✅ RTB scenarios save / compare / delete
- ✅ MLR Creative Review workflow with Pending / Approved / Rejected tabs
- ✅ Live OpenRTB Bid Stream (simulated SSE)
- ✅ Vendor PDF export (print-friendly scorecard)

### Iteration 3 — "Add all" + role-based access
- ✅ **JWT email/password authentication** (bcrypt hashing, 12h tokens, Bearer in localStorage)
- ✅ **Role-based access control** with 4 roles seeded (Admin, Trader, Analyst, Vendor with vendor_scope)
- ✅ Backend role guards on POST /campaigns, PATCH /campaigns, PATCH /creatives, POST /upload, /admin/reseed, /shares/vendor; `/auth/users` admin-only
- ✅ Frontend ProtectedRoute wrapper + role-filtered sidebar nav; 403 page for forbidden access
- ✅ Login page with brand-panel split + demo account quick-picker
- ✅ User dropdown with name + role badge + sign out
- ✅ **HCP Frequency Intelligence** (`/api/frequency-intelligence`, `/frequency` page) — overexposure detection per HCP audience with Critical/High/Moderate/Healthy distribution
- ✅ **Share-via-link for vendor scorecards** — `/api/shares/vendor` CRUD (admin/trader), `/api/public/shares/vendor/{token}` public read-only, `/share/v/:token` public scorecard route. Cards have Share Link button → dialog → copy URL → toast. Active shares table with copy & revoke

## Prioritized Backlog
- All P1/P2 items complete ✅
- **P2** Frequency intelligence per HCP target list ✅
- **P2** Authentication + RBAC ✅
- **P3** Real OpenRTB exchange connectors (would need SSP partnerships — current simulated stream is realistic)
- **P3** Password reset / refresh tokens (only access tokens for now)
- **P3** Split server.py into per-resource routers (1170 lines — flagged for refactor)

## Test Credentials
See `/app/memory/test_credentials.md`. Four demo accounts:
- `admin@pharmasignal.io` / `Admin@2026` (admin)
- `trader@pharmasignal.io` / `Trader@2026` (trader)
- `analyst@pharmasignal.io` / `Analyst@2026` (analyst)
- `vendor@pulsepoint.com` / `Vendor@2026` (vendor, scoped to PulsePoint)
