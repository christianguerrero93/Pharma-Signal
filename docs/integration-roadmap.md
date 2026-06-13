# Integration Roadmap

This roadmap turns Pharma Signal from a hostable prototype into a production-grade pharma DSP platform.

## Phase 1: Hosted MVP

Status: included in this repository.

- React + Vite command center
- Campaign, audience, supply, bid, pacing, measurement, and compliance modules
- Mock partner adapters
- Netlify deployment config
- Typed bid-scoring and measurement-planning logic

## Phase 2: Data ingestion

Add the first real data inputs.

- CSV/XLSX campaign delivery uploads
- GA4 Data API connector
- SSP delivery-file import
- Manual audience upload with metadata validation
- Partner deal QA screen
- Basic warehouse export

## Phase 3: Control plane

Add a backend that manages the operational layer.

- Campaign CRUD
- Line items
- Budget and pacing settings
- Frequency cap settings
- Partner/deal routing
- User roles
- Audit logs
- Approval workflow

## Phase 4: Bidder service

Move bid scoring into a real-time service.

- OpenRTB endpoint
- Bid request validation
- Supply QA lookup
- Audience eligibility lookup
- Pacing and frequency lookup
- Bid price calculation
- Bid response generation
- Kafka event logging

## Phase 5: Measurement and optimization

Connect media activation to business impact.

- Outcome partner imports
- Exposed/control planning
- Lift-readiness forecast
- Rx / conversion proxy ingestion
- Supply-path lift comparison
- Bid multiplier recommendations
- Automated under/over-pacing alerts

## Phase 6: Production hardening

Prepare for serious use.

- Authentication and RBAC
- Secrets management
- Observability
- Unit and integration tests
- Data retention rules
- Privacy review
- MLR and compliance workflow
- Security review
- Disaster recovery plan

## Connector priority

| Priority | Connector | Why it matters |
| --- | --- | --- |
| 1 | GA4 Data API | Pulls engagement and conversion proxy signals into planning and retargeting. |
| 2 | SSP delivery files | Makes supply-path decisions based on actual spend, viewability, IVT, and deal performance. |
| 3 | Measurement partner import | Connects media exposure to downstream outcome and lift reads. |
| 4 | Warehouse sink | Gives the platform a durable analytics layer for optimization and reporting. |
| 5 | Verification partner | Adds brand safety, fraud, and viewability as bidding features. |
