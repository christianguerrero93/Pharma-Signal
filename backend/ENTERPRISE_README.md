# Pharma Signal Enterprise Backend

This backend layer turns Pharma Signal from a strong DSP prototype into an enterprise-style full-stack platform foundation.

There are now two backend entry points:

1. `server.py` — the existing Emergent/Mongo backend with auth, seeded demo data, dashboard APIs, RTB simulation, live bid stream, CSV upload, AI recommendations, MLR/creative review, frequency intelligence, and vendor share links.
2. `enterprise_server.py` — a CEO-level enterprise API surface for the next product stage: multi-tenant control plane, OpenRTB auctioning, approvals, audit, measurement readiness, portfolio optimization, and board narrative endpoints.

## Run the existing backend

```bash
cd backend
uvicorn server:app --reload --port 8001
```

Required environment values for `server.py`:

```bash
MONGO_URL=mongodb://localhost:27017
DB_NAME=pharma_signal
JWT_SECRET=replace-me
ADMIN_EMAIL=admin@pharmasignal.io
ADMIN_PASSWORD=Admin@2026
```

## Run the enterprise backend

```bash
cd backend
uvicorn enterprise_server:app --reload --port 8080
```

The enterprise API is intentionally in-memory for now so it can run instantly while modeling the production service boundaries.

## Enterprise API modules

### Executive operating layer

- `GET /health`
- `GET /api/v2/executive-dashboard`
- `GET /api/v2/board/narrative`

### Control plane

- `GET /api/v2/campaigns`
- `POST /api/v2/campaigns`
- `GET /api/v2/supply-paths`

### Auction gateway

- `POST /api/v2/auction/evaluate`

Evaluates a pharma-safe OpenRTB-style request across:

- campaign state
- line item state
- audience match
- supply path approval
- creative MLR approval
- PHI blocking
- geo approval
- consent signal
- frequency cap pressure
- bid floor economics

### Measurement and optimization

- `GET /api/v2/measurement/plans`
- `GET /api/v2/optimizer/portfolio`

### Approvals and audit

- `POST /api/v2/approvals`
- `POST /api/v2/approvals/decision`
- `GET /api/v2/audit`

Role is passed through the `x-pharma-role` header. Example:

```bash
curl -H "x-pharma-role: ceo" http://localhost:8080/api/v2/executive-dashboard
```

## Production migration path

The enterprise backend should become the stable API contract while implementation moves from in-memory services to production infrastructure:

- FastAPI control plane
- Postgres for campaign configuration, users, approvals, and audit logs
- Redis/Aerospike for pacing and frequency state
- Kafka/Flink for auction and event streaming
- BigQuery/Snowflake for measurement and reporting
- Go/Rust low-latency OpenRTB bidder
- Partner-specific SSP adapters for PubMatic, Magnite, OpenX, Index Exchange, and endemic/private marketplace partners
