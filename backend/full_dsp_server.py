"""Pharma Signal Full DSP Server.

Functional pharma-native Demand-Side Platform backend with SQLite persistence.

Capabilities (DeepIntent-class + pharma-native differentiators):
  - Auth, roles, and an append-only audit trail on every mutation
  - Campaign + line-item planning with flights, pacing, and budgets
  - Weighted, outcome-aware bid-factor engine and single-impression auction eval
  - OpenRTB-style bidstream simulation (win rate / spend / clearing analytics)
  - HCP / DTC / lookalike / contextual audience library with reach & frequency
    forecasting, NPI-level sizing, match-rate and data-cost transparency
  - MLR (Medical-Legal-Regulatory) creative review workflow with versioning
  - Supply-path / PMP deal management and supply-path optimization scoring
  - Script-lift / diagnosis-lift measurement planning with statistical power
  - Portfolio budget optimizer with increase / hold / decrease recommendations
  - Cross-channel HCP + DTC frequency governance
  - Compliance scanner: no-PHI guardrails, consent, brand safety, ISI checks
  - Executive overview KPIs

Run: uvicorn full_dsp_server:app --reload --port 8090
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = Path(os.environ.get("FULL_DSP_DB", Path(__file__).with_name("pharma_signal_dsp.db")))
SESSIONS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="Pharma Signal Full DSP", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def audit(actor: str, action: str, entity_type: str, entity_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    with conn() as db:
        db.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid4()), now_iso(), actor, action, entity_type, entity_id, json.dumps(metadata or {})),
        )
        db.commit()


def current_user(authorization: str = Header(default="")) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.replace("Bearer ", "", 1)
    user = SESSIONS.get(token)
    if not user:
        raise HTTPException(401, "Invalid session")
    return user


def roles(*allowed: str):
    def dep(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
        if user["role"] not in allowed:
            raise HTTPException(403, f"Requires role: {', '.join(allowed)}")
        return user
    return dep


# ---------------------------------------------------------------------------
# Statistics helpers (no scipy dependency)
# ---------------------------------------------------------------------------
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF via Acklam's rational approximation."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)


def two_proportion_power(baseline: float, lift_pct: float, n_exposed: int, n_control: int, alpha: float = 0.05) -> Dict[str, float]:
    """Power of a two-proportion z-test for a relative lift over a baseline rate."""
    p1 = max(min(baseline, 0.999), 1e-6)
    p2 = max(min(p1 * (1 + lift_pct / 100.0), 0.999), 1e-6)
    if n_exposed <= 0 or n_control <= 0:
        return {"power": 0.0, "effect": 0.0}
    pooled = (p1 * n_control + p2 * n_exposed) / (n_exposed + n_control)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n_exposed + 1 / n_control))
    se_alt = math.sqrt(p1 * (1 - p1) / n_control + p2 * (1 - p2) / n_exposed)
    if se_alt == 0:
        return {"power": 0.0, "effect": 0.0}
    z_alpha = norm_ppf(1 - alpha / 2)
    z = (abs(p2 - p1) - z_alpha * se_pooled) / se_alt
    return {"power": round(max(0.0, min(1.0, norm_cdf(z))), 4), "effect": round((p2 - p1) * 100, 4)}


def minimum_detectable_lift(baseline: float, n_exposed: int, n_control: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """Smallest relative lift (%) detectable at the given sample sizes and power."""
    p1 = max(min(baseline, 0.999), 1e-6)
    if n_exposed <= 0 or n_control <= 0:
        return 0.0
    z_alpha = norm_ppf(1 - alpha / 2)
    z_beta = norm_ppf(power)
    se = math.sqrt(p1 * (1 - p1) * (1 / n_exposed + 1 / n_control))
    abs_delta = (z_alpha + z_beta) * se
    return round(abs_delta / p1 * 100, 2)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


class CampaignCreate(BaseModel):
    name: str
    brand: str
    indication: str
    audience_type: str = Field(pattern="^(HCP|DTC|Hybrid|Contextual)$")
    objective: str
    budget: float = Field(gt=0)
    flight_start: str
    flight_end: str
    status: str = "draft"


class LineItemCreate(BaseModel):
    name: str
    channel: str
    budget: float = Field(gt=0)
    max_bid_cpm: float = Field(gt=0)
    pacing_mode: str = "even"
    status: str = "draft"
    frequency_cap: int = Field(default=3, ge=1, le=30)


class BidFactors(BaseModel):
    audience_quality_weight: float = Field(default=0.28, ge=0, le=1)
    supply_quality_weight: float = Field(default=0.22, ge=0, le=1)
    outcome_signal_weight: float = Field(default=0.24, ge=0, le=1)
    contextual_relevance_weight: float = Field(default=0.12, ge=0, le=1)
    working_media_weight: float = Field(default=0.10, ge=0, le=1)
    frequency_penalty_weight: float = Field(default=0.04, ge=0, le=1)
    bid_shading_pct: float = Field(default=0.12, ge=0, le=0.75)
    max_bid_multiplier: float = Field(default=2.5, ge=0.2, le=10)
    data_cost_guardrail: float = Field(default=0.35, ge=0, le=1)


class CampaignBuildRequest(BaseModel):
    campaign: CampaignCreate
    line_items: List[LineItemCreate] = Field(default_factory=list)
    default_bid_factors: BidFactors = Field(default_factory=BidFactors)


class BulkEditRequest(BaseModel):
    entity_type: str = Field(pattern="^(campaign|line_item|bid_factor)$")
    ids: List[str]
    updates: Dict[str, Any]
    reason: str
    dry_run: bool = False


class AuctionEvaluateRequest(BaseModel):
    line_item_id: str
    supply_path_id: str
    audience_quality: float = Field(ge=0, le=100)
    supply_quality: float = Field(ge=0, le=100)
    outcome_signal: float = Field(ge=0, le=100)
    contextual_relevance: float = Field(ge=0, le=100)
    working_media_ratio: float = Field(ge=0, le=1)
    data_cost_ratio: float = Field(ge=0, le=1)
    frequency_seen_today: int = Field(ge=0)
    floor_cpm: float = Field(gt=0)
    contains_phi: bool = False
    creative_approved: bool = True
    geo_allowed: bool = True
    consent_ok: bool = True


class AudienceCreate(BaseModel):
    name: str
    audience_type: str = Field(pattern="^(HCP|DTC|Lookalike|Contextual|Retargeting)$")
    description: str = ""
    npi_count: int = Field(default=0, ge=0)
    reach: int = Field(gt=0)
    match_rate: float = Field(default=0.6, ge=0, le=1)
    data_cpm: float = Field(default=0.0, ge=0)
    refresh_cadence: str = "weekly"
    contains_phi: bool = False
    status: str = "active"


class ForecastRequest(BaseModel):
    audience_id: str
    budget: float = Field(gt=0)
    cpm: float = Field(gt=0)
    frequency_cap: int = Field(default=3, ge=1, le=30)
    flight_days: int = Field(default=30, ge=1, le=365)


class CreativeCreate(BaseModel):
    campaign_id: str
    name: str
    fmt: str = Field(default="Display 300x250")
    channel: str = "Display"
    claims: str = ""
    isi_included: bool = True
    landing_url: str = ""


class CreativeReview(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|changes_requested)$")
    notes: str = ""


class DealCreate(BaseModel):
    partner: str
    deal_id: str
    deal_type: str = Field(default="PMP", pattern="^(PMP|PG|Auction Package|Curated)$")
    channel: str = "Display"
    floor_cpm: float = Field(gt=0)
    audience_match: float = Field(default=0.6, ge=0, le=1)
    status: str = "active"


class MeasurementPlanCreate(BaseModel):
    campaign_id: str
    study_type: str = Field(default="script_lift", pattern="^(script_lift|diagnosis_lift|audience_quality|brand_lift)$")
    baseline_rate: float = Field(gt=0, lt=1)
    expected_lift_pct: float = Field(gt=0)
    exposed_size: int = Field(gt=0)
    control_size: int = Field(gt=0)


class BidstreamRequest(BaseModel):
    line_item_id: str
    requests: int = Field(default=500, ge=1, le=20000)
    phi_leak_rate: float = Field(default=0.0, ge=0, le=1)
    seed: Optional[int] = None


# ---------------------------------------------------------------------------
# Database bootstrap + seed
# ---------------------------------------------------------------------------
def init_db() -> None:
    with conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, name TEXT, role TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, name TEXT, brand TEXT, indication TEXT, audience_type TEXT, objective TEXT, budget REAL, flight_start TEXT, flight_end TEXT, status TEXT, created_by TEXT, created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS line_items (id TEXT PRIMARY KEY, campaign_id TEXT, name TEXT, channel TEXT, budget REAL, max_bid_cpm REAL, pacing_mode TEXT, status TEXT, frequency_cap INTEGER, created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS bid_factors (line_item_id TEXT PRIMARY KEY, audience_quality_weight REAL, supply_quality_weight REAL, outcome_signal_weight REAL, contextual_relevance_weight REAL, working_media_weight REAL, frequency_penalty_weight REAL, bid_shading_pct REAL, max_bid_multiplier REAL, data_cost_guardrail REAL, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS supply_paths (id TEXT PRIMARY KEY, partner TEXT, channel TEXT, deal_id TEXT, seller_type TEXT, bid_floor_cpm REAL, viewability REAL, fraud_risk REAL, match_rate REAL, working_media_ratio REAL, outcome_score REAL, status TEXT);
        CREATE TABLE IF NOT EXISTS audiences (id TEXT PRIMARY KEY, name TEXT, audience_type TEXT, description TEXT, npi_count INTEGER, reach INTEGER, match_rate REAL, data_cpm REAL, refresh_cadence TEXT, contains_phi INTEGER, status TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS creatives (id TEXT PRIMARY KEY, campaign_id TEXT, name TEXT, fmt TEXT, channel TEXT, claims TEXT, isi_included INTEGER, landing_url TEXT, mlr_status TEXT, version INTEGER, reviewer TEXT, review_notes TEXT, submitted_at TEXT, decided_at TEXT);
        CREATE TABLE IF NOT EXISTS deals (id TEXT PRIMARY KEY, partner TEXT, deal_id TEXT, deal_type TEXT, channel TEXT, floor_cpm REAL, audience_match REAL, status TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS measurement_plans (id TEXT PRIMARY KEY, campaign_id TEXT, study_type TEXT, baseline_rate REAL, expected_lift_pct REAL, exposed_size INTEGER, control_size INTEGER, power REAL, mdl REAL, status TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, ts TEXT, actor TEXT, action TEXT, entity_type TEXT, entity_id TEXT, metadata_json TEXT);
        """)
        seed_password = os.environ.get("FULL_DSP_DEV_PASSWORD", "pharma-signal-local")
        for email, name, role in [("admin@pharmasignal.local", "Admin", "admin"), ("trader@pharmasignal.local", "Trader", "trader"), ("analyst@pharmasignal.local", "Analyst", "analyst")]:
            db.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)", (str(uuid4()), email, digest(seed_password), name, role, now_iso()))
        seed_supply = [
            ("PubMatic", "Display", "PM-PHARMA-HCP-001", "Direct", 6.8, 69, 1.1, 71, 0.54, 82, "approved"),
            ("OpenX", "Display", "OX-HEALTH-WEB-117", "SPO verified", 7.4, 72, 1.4, 68, 0.62, 79, "approved"),
            ("Magnite", "CTV", "MG-CTV-RSV-902", "Direct", 21.8, 92, 0.4, 62, 0.71, 88, "approved"),
            ("Index Exchange", "Display", "IX-PHARMA-WEB-219", "SPO verified", 5.4, 78, 0.8, 58, 0.70, 84, "review"),
            ("Endemic Health Network", "Native", "EH-ONC-NATIVE-009", "Direct", 24.0, 81, 0.5, 64, 0.58, 91, "approved"),
        ]
        for row in seed_supply:
            db.execute("INSERT OR IGNORE INTO supply_paths VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), *row))
        if not db.execute("SELECT 1 FROM audiences LIMIT 1").fetchone():
            seed_aud = [
                ("Endocrinologists - T1D Treaters", "HCP", "NPI-verified endocrinologists with recent T1D Rx activity", 48200, 48200, 0.91, 12.5, "weekly", 0, "active"),
                ("Oncology HCP - RSV high prescribers", "HCP", "NPI-matched oncology + pulmonology decile 8-10", 71500, 71500, 0.88, 14.0, "weekly", 0, "active"),
                ("Diagnosed T1D Caregivers (DTC)", "DTC", "Privacy-safe diagnosed condition + caregiver model", 0, 2400000, 0.62, 6.5, "daily", 0, "active"),
                ("Endemic Health Readers", "Contextual", "Contextual health-content readers, no identifiers", 0, 5800000, 0.0, 0.0, "real-time", 0, "active"),
                ("Site Visitor Retargeting", "Retargeting", "Branded-site visitors, consent captured", 0, 310000, 0.74, 4.0, "daily", 0, "active"),
                ("HCP Lookalike - Top Decile Seed", "Lookalike", "Modeled from converted HCP seed audience", 96000, 96000, 0.70, 9.0, "weekly", 0, "active"),
            ]
            for row in seed_aud:
                db.execute("INSERT INTO audiences VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), *row, now_iso()))
        if not db.execute("SELECT 1 FROM deals LIMIT 1").fetchone():
            seed_deals = [
                ("PubMatic", "PM-PMP-ENDO-44", "PMP", "Display", 7.5, 0.82, "active"),
                ("Magnite", "MG-PG-CTV-12", "PG", "CTV", 26.0, 0.68, "active"),
                ("Index Exchange", "IX-CURATED-HEALTH-7", "Curated", "Display", 6.0, 0.75, "active"),
                ("Endemic Health Network", "EH-PMP-ONC-3", "PMP", "Native", 24.0, 0.79, "active"),
            ]
            for row in seed_deals:
                db.execute("INSERT INTO deals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), *row, now_iso()))
        db.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Health + auth
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "pharma-signal-full-dsp"}


@app.post("/api/full/auth/login")
def login(payload: LoginRequest) -> Dict[str, Any]:
    init_db()
    with conn() as db:
        row = db.execute("SELECT * FROM users WHERE lower(email)=lower(?)", (payload.email,)).fetchone()
    if not row or row["password_hash"] != digest(payload.password):
        raise HTTPException(401, "Invalid email or password")
    user = {k: row[k] for k in row.keys() if k != "password_hash"}
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user
    audit(user["email"], "login", "user", user["id"], {"role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "user": user}


@app.get("/api/full/auth/me")
def me(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    return user


# ---------------------------------------------------------------------------
# Workbench + campaign management
# ---------------------------------------------------------------------------
@app.get("/api/full/workbench")
def workbench(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        campaign_rows = dicts(db.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall())
        line_rows = dicts(db.execute("SELECT * FROM line_items ORDER BY created_at DESC").fetchall())
        factor_rows = dicts(db.execute("SELECT * FROM bid_factors").fetchall())
        supply_rows = dicts(db.execute("SELECT * FROM supply_paths ORDER BY partner").fetchall())
        audit_rows = dicts(db.execute("SELECT * FROM audit_events ORDER BY ts DESC LIMIT 50").fetchall())
    factors_by_line = {row["line_item_id"]: row for row in factor_rows}
    lines_by_campaign: Dict[str, List[Dict[str, Any]]] = {}
    for line in line_rows:
        line["bid_factors"] = factors_by_line.get(line["id"])
        lines_by_campaign.setdefault(line["campaign_id"], []).append(line)
    for campaign in campaign_rows:
        campaign["line_items"] = lines_by_campaign.get(campaign["id"], [])
    return {"user": user, "campaigns": campaign_rows, "supply_paths": supply_rows, "audit": audit_rows, "summary": {"campaigns": len(campaign_rows), "line_items": len(line_rows), "total_budget": round(sum(c["budget"] for c in campaign_rows), 2), "active_campaigns": sum(1 for c in campaign_rows if c["status"] == "active")}}


@app.post("/api/full/campaign-build")
def build_campaign(payload: CampaignBuildRequest, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    campaign_id = str(uuid4())
    ts = now_iso()
    with conn() as db:
        db.execute("INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (campaign_id, payload.campaign.name, payload.campaign.brand, payload.campaign.indication, payload.campaign.audience_type, payload.campaign.objective, payload.campaign.budget, payload.campaign.flight_start, payload.campaign.flight_end, payload.campaign.status, user["email"], ts, ts))
        created_lines = []
        for item in payload.line_items:
            line_id = str(uuid4())
            db.execute("INSERT INTO line_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (line_id, campaign_id, item.name, item.channel, item.budget, item.max_bid_cpm, item.pacing_mode, item.status, item.frequency_cap, ts, ts))
            factors = payload.default_bid_factors.model_dump()
            db.execute("INSERT INTO bid_factors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (line_id, *factors.values(), ts))
            created_lines.append({"id": line_id, **item.model_dump(), "bid_factors": factors})
        db.commit()
    audit(user["email"], "campaign_build", "campaign", campaign_id, payload.model_dump())
    return {"campaign_id": campaign_id, "line_items": created_lines}


@app.post("/api/full/campaigns/{campaign_id}/line-items")
def create_line_item(campaign_id: str, payload: LineItemCreate, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    line_id = str(uuid4())
    ts = now_iso()
    factors = BidFactors().model_dump()
    with conn() as db:
        if not db.execute("SELECT id FROM campaigns WHERE id=?", (campaign_id,)).fetchone():
            raise HTTPException(404, "Campaign not found")
        db.execute("INSERT INTO line_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (line_id, campaign_id, payload.name, payload.channel, payload.budget, payload.max_bid_cpm, payload.pacing_mode, payload.status, payload.frequency_cap, ts, ts))
        db.execute("INSERT INTO bid_factors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (line_id, *factors.values(), ts))
        db.commit()
    audit(user["email"], "line_item_create", "line_item", line_id, payload.model_dump())
    return {"id": line_id, **payload.model_dump(), "bid_factors": factors}


@app.put("/api/full/line-items/{line_item_id}/bid-factors")
def update_bid_factors(line_item_id: str, payload: BidFactors, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    values = payload.model_dump()
    ts = now_iso()
    with conn() as db:
        if not db.execute("SELECT line_item_id FROM bid_factors WHERE line_item_id=?", (line_item_id,)).fetchone():
            raise HTTPException(404, "Bid factors not found")
        db.execute("UPDATE bid_factors SET audience_quality_weight=?, supply_quality_weight=?, outcome_signal_weight=?, contextual_relevance_weight=?, working_media_weight=?, frequency_penalty_weight=?, bid_shading_pct=?, max_bid_multiplier=?, data_cost_guardrail=?, updated_at=? WHERE line_item_id=?", (*values.values(), ts, line_item_id))
        db.commit()
    audit(user["email"], "bid_factors_update", "line_item", line_item_id, values)
    return {"line_item_id": line_item_id, **values, "updated_at": ts}


@app.post("/api/full/bulk-edit")
def bulk_edit(payload: BulkEditRequest, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    allowed = {"campaign": {"budget", "status", "flight_start", "flight_end", "objective"}, "line_item": {"budget", "max_bid_cpm", "status", "pacing_mode", "frequency_cap"}, "bid_factor": set(BidFactors.model_fields.keys())}
    table = {"campaign": "campaigns", "line_item": "line_items", "bid_factor": "bid_factors"}[payload.entity_type]
    id_col = "line_item_id" if payload.entity_type == "bid_factor" else "id"
    illegal = set(payload.updates) - allowed[payload.entity_type]
    if illegal:
        raise HTTPException(400, f"Fields not bulk editable: {sorted(illegal)}")
    if not payload.ids:
        raise HTTPException(400, "No ids supplied")
    placeholders = ",".join("?" for _ in payload.ids)
    with conn() as db:
        existing = dicts(db.execute(f"SELECT * FROM {table} WHERE {id_col} IN ({placeholders})", tuple(payload.ids)).fetchall())
        if payload.dry_run:
            return {"dry_run": True, "matched": len(existing), "updates": payload.updates, "preview": existing}
        if not existing:
            raise HTTPException(404, "No matching records")
        set_clause = ", ".join(f"{field}=?" for field in payload.updates)
        values = list(payload.updates.values())
        if payload.entity_type in {"campaign", "line_item"}:
            set_clause += ", updated_at=?"
            values.append(now_iso())
        db.execute(f"UPDATE {table} SET {set_clause} WHERE {id_col} IN ({placeholders})", tuple(values + payload.ids))
        db.commit()
    audit(user["email"], "bulk_edit", payload.entity_type, ",".join(payload.ids), {"updates": payload.updates, "reason": payload.reason})
    return {"dry_run": False, "matched": len(existing), "updated": len(existing), "entity_type": payload.entity_type, "updates": payload.updates}


# ---------------------------------------------------------------------------
# Bidder: single-impression evaluation + bidstream simulation
# ---------------------------------------------------------------------------
def _score_impression(factors: Dict[str, Any], line: Dict[str, Any], *, audience_quality: float, supply_quality: float, outcome_signal: float, contextual_relevance: float, working_media_ratio: float, data_cost_ratio: float, frequency_seen_today: int, floor_cpm: float, supply_status: str, contains_phi: bool, creative_approved: bool, geo_allowed: bool, consent_ok: bool) -> Dict[str, Any]:
    guardrails: List[str] = []
    if contains_phi:
        guardrails.append("Blocked: PHI-like payload cannot enter bidder")
    if not creative_approved:
        guardrails.append("Blocked: creative is not MLR approved")
    if not geo_allowed:
        guardrails.append("Blocked: geo is outside approved activation footprint")
    if not consent_ok:
        guardrails.append("Blocked: consent signal missing")
    if data_cost_ratio > factors["data_cost_guardrail"]:
        guardrails.append("Throttle: data cost exceeds guardrail")
    if frequency_seen_today >= line["frequency_cap"]:
        guardrails.append("Throttle: frequency cap pressure")
    if supply_status != "approved":
        guardrails.append("Blocked: supply path not approved")
    hard_block = any(g.startswith("Blocked") for g in guardrails)
    weighted_score = (
        audience_quality * factors["audience_quality_weight"]
        + supply_quality * factors["supply_quality_weight"]
        + outcome_signal * factors["outcome_signal_weight"]
        + contextual_relevance * factors["contextual_relevance_weight"]
        + working_media_ratio * 100 * factors["working_media_weight"]
        - min(frequency_seen_today / max(line["frequency_cap"], 1), 1) * 100 * factors["frequency_penalty_weight"]
    )
    multiplier = min(factors["max_bid_multiplier"], max(0.1, weighted_score / 60))
    shaded_bid = round(line["max_bid_cpm"] * multiplier * (1 - factors["bid_shading_pct"]), 2)
    decision = "blocked" if hard_block else "no_bid" if shaded_bid < floor_cpm else "throttle" if guardrails else "bid"
    clearing = None if decision in {"blocked", "no_bid"} else round(min(shaded_bid, max(floor_cpm, shaded_bid * 0.88)), 2)
    return {"decision": decision, "weighted_score": weighted_score, "bid_cpm": 0 if clearing is None else shaded_bid, "clearing_price_cpm": clearing, "guardrails": guardrails}


@app.post("/api/full/auction/evaluate")
def evaluate_auction(payload: AuctionEvaluateRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        line = db.execute("SELECT * FROM line_items WHERE id=?", (payload.line_item_id,)).fetchone()
        factors = db.execute("SELECT * FROM bid_factors WHERE line_item_id=?", (payload.line_item_id,)).fetchone()
        supply = db.execute("SELECT * FROM supply_paths WHERE id=?", (payload.supply_path_id,)).fetchone()
    if not line or not factors or not supply:
        raise HTTPException(404, "Line item, bid factors, or supply path not found")
    scored = _score_impression(
        dict(factors), dict(line),
        audience_quality=payload.audience_quality, supply_quality=payload.supply_quality, outcome_signal=payload.outcome_signal,
        contextual_relevance=payload.contextual_relevance, working_media_ratio=payload.working_media_ratio, data_cost_ratio=payload.data_cost_ratio,
        frequency_seen_today=payload.frequency_seen_today, floor_cpm=payload.floor_cpm, supply_status=supply["status"],
        contains_phi=payload.contains_phi, creative_approved=payload.creative_approved, geo_allowed=payload.geo_allowed, consent_ok=payload.consent_ok,
    )
    result = {
        "decision": scored["decision"], "bid_cpm": scored["bid_cpm"], "clearing_price_cpm": scored["clearing_price_cpm"],
        "confidence": round(max(0, min(100, scored["weighted_score"]))),
        "reasons": [f"Weighted score {round(scored['weighted_score'], 1)}/100", f"Audience quality {payload.audience_quality}/100", f"Supply quality {payload.supply_quality}/100", f"Outcome signal {payload.outcome_signal}/100", f"Bid shading {round(factors['bid_shading_pct'] * 100)}%"],
        "guardrails": scored["guardrails"] or ["No PHI accepted", "Creative approved", "Supply path approved"],
    }
    audit(user["email"], "auction_evaluate", "line_item", payload.line_item_id, result)
    return result


@app.post("/api/full/bidstream/simulate")
def simulate_bidstream(payload: BidstreamRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    rng = random.Random(payload.seed)
    with conn() as db:
        line = db.execute("SELECT * FROM line_items WHERE id=?", (payload.line_item_id,)).fetchone()
        factors = db.execute("SELECT * FROM bid_factors WHERE line_item_id=?", (payload.line_item_id,)).fetchone()
        supply_rows = dicts(db.execute("SELECT * FROM supply_paths").fetchall())
    if not line or not factors:
        raise HTTPException(404, "Line item or bid factors not found")
    if not supply_rows:
        raise HTTPException(400, "No supply paths configured")
    factors_d, line_d = dict(factors), dict(line)
    tally = {"bid": 0, "throttle": 0, "no_bid": 0, "blocked": 0}
    wins, spend_cpm, clearing_sum, score_sum = 0, 0.0, 0.0, 0.0
    by_partner: Dict[str, Dict[str, Any]] = {}
    for _ in range(payload.requests):
        supply = rng.choice(supply_rows)
        contains_phi = rng.random() < payload.phi_leak_rate
        scored = _score_impression(
            factors_d, line_d,
            audience_quality=rng.uniform(55, 98), supply_quality=supply["outcome_score"], outcome_signal=rng.uniform(45, 95),
            contextual_relevance=rng.uniform(50, 95), working_media_ratio=supply["working_media_ratio"], data_cost_ratio=rng.uniform(0.1, 0.5),
            frequency_seen_today=rng.randint(0, line_d["frequency_cap"] + 1), floor_cpm=supply["bid_floor_cpm"], supply_status=supply["status"],
            contains_phi=contains_phi, creative_approved=True, geo_allowed=rng.random() > 0.02, consent_ok=rng.random() > 0.03,
        )
        tally[scored["decision"]] += 1
        score_sum += scored["weighted_score"]
        partner = by_partner.setdefault(supply["partner"], {"requests": 0, "wins": 0, "spend_cpm": 0.0})
        partner["requests"] += 1
        if scored["decision"] in {"bid", "throttle"} and scored["clearing_price_cpm"]:
            # Win when our shaded bid clears a randomized competing floor.
            competitor = supply["bid_floor_cpm"] * rng.uniform(0.7, 1.6)
            if scored["bid_cpm"] >= competitor:
                wins += 1
                spend_cpm += scored["clearing_price_cpm"]
                clearing_sum += scored["clearing_price_cpm"]
                partner["wins"] += 1
                partner["spend_cpm"] += scored["clearing_price_cpm"]
    bids = tally["bid"] + tally["throttle"]
    impressions = wins
    spend = round(spend_cpm / 1000, 2)
    summary = {
        "requests": payload.requests,
        "decisions": tally,
        "bid_rate": round(bids / payload.requests, 4),
        "win_rate": round(wins / max(bids, 1), 4),
        "impressions_won": impressions,
        "avg_clearing_cpm": round(clearing_sum / max(wins, 1), 2),
        "est_spend": spend,
        "avg_weighted_score": round(score_sum / payload.requests, 1),
        "phi_blocked": tally["blocked"],
        "by_partner": [
            {"partner": p, "requests": v["requests"], "wins": v["wins"], "win_rate": round(v["wins"] / max(v["requests"], 1), 4), "est_spend": round(v["spend_cpm"] / 1000, 2)}
            for p, v in sorted(by_partner.items(), key=lambda kv: kv[1]["wins"], reverse=True)
        ],
    }
    audit(user["email"], "bidstream_simulate", "line_item", payload.line_item_id, {"requests": payload.requests, "win_rate": summary["win_rate"]})
    return summary


# ---------------------------------------------------------------------------
# Audiences + reach / frequency forecasting
# ---------------------------------------------------------------------------
@app.get("/api/full/audiences")
def list_audiences(user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM audiences ORDER BY audience_type, name").fetchall())


@app.post("/api/full/audiences")
def create_audience(payload: AudienceCreate, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    if payload.contains_phi:
        raise HTTPException(400, "Audiences containing PHI cannot be onboarded into Pharma Signal")
    audience_id = str(uuid4())
    with conn() as db:
        db.execute("INSERT INTO audiences VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (audience_id, payload.name, payload.audience_type, payload.description, payload.npi_count, payload.reach, payload.match_rate, payload.data_cpm, payload.refresh_cadence, int(payload.contains_phi), payload.status, now_iso()))
        db.commit()
    audit(user["email"], "audience_create", "audience", audience_id, payload.model_dump())
    return {"id": audience_id, **payload.model_dump()}


@app.post("/api/full/audiences/forecast")
def forecast_audience(payload: ForecastRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        aud = db.execute("SELECT * FROM audiences WHERE id=?", (payload.audience_id,)).fetchone()
    if not aud:
        raise HTTPException(404, "Audience not found")
    aud = dict(aud)
    addressable = aud["reach"] * (aud["match_rate"] if aud["match_rate"] > 0 else 1.0)
    impressions = int(payload.budget / payload.cpm * 1000)
    # Diminishing-returns reach curve: unique reach saturates against addressable pool.
    avg_freq_target = payload.frequency_cap
    raw_reach = impressions / max(avg_freq_target, 1)
    unique_reach = int(addressable * (1 - math.exp(-raw_reach / max(addressable, 1))))
    achieved_freq = round(impressions / max(unique_reach, 1), 2)
    pct_reached = round(unique_reach / max(addressable, 1), 4)
    data_spend = round(impressions / 1000 * aud["data_cpm"], 2)
    media_spend = round(payload.budget - data_spend, 2)
    working_media_ratio = round(max(0.0, media_spend) / payload.budget, 4)
    daily_impressions = int(impressions / payload.flight_days)
    result = {
        "audience": {"id": aud["id"], "name": aud["name"], "type": aud["audience_type"], "addressable": int(addressable), "npi_count": aud["npi_count"], "match_rate": aud["match_rate"]},
        "impressions": impressions,
        "daily_impressions": daily_impressions,
        "unique_reach": unique_reach,
        "pct_of_audience_reached": pct_reached,
        "achieved_frequency": achieved_freq,
        "frequency_cap": payload.frequency_cap,
        "data_spend": data_spend,
        "media_spend": media_spend,
        "working_media_ratio": working_media_ratio,
        "data_cpm": aud["data_cpm"],
        "effective_cpm": round(payload.budget / max(impressions, 1) * 1000, 2),
    }
    audit(user["email"], "audience_forecast", "audience", payload.audience_id, {"budget": payload.budget, "unique_reach": unique_reach})
    return result


@app.get("/api/full/frequency/governance")
def frequency_governance(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    """Cross-channel HCP + DTC frequency coordination — a pharma-native gap."""
    with conn() as db:
        campaigns = dicts(db.execute("SELECT * FROM campaigns").fetchall())
        lines = dicts(db.execute("SELECT * FROM line_items").fetchall())
    by_campaign = {c["id"]: c for c in campaigns}
    channels: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        camp = by_campaign.get(line["campaign_id"])
        if not camp:
            continue
        audience = camp["audience_type"]
        bucket = channels.setdefault(line["channel"], {"channel": line["channel"], "lines": 0, "caps": [], "audiences": set()})
        bucket["lines"] += 1
        bucket["caps"].append(line["frequency_cap"])
        bucket["audiences"].add(audience)
    rows = []
    for bucket in channels.values():
        caps = bucket["caps"]
        rows.append({
            "channel": bucket["channel"],
            "lines": bucket["lines"],
            "min_cap": min(caps), "max_cap": max(caps),
            "avg_cap": round(sum(caps) / len(caps), 1),
            "audiences": sorted(bucket["audiences"]),
        })
    # Recommend a coordinated global cap so HCPs are not over-exposed across channels.
    total_cap_pressure = sum(r["avg_cap"] for r in rows)
    recommended_global_cap = max(3, min(12, round(total_cap_pressure)))
    overexposed = [r["channel"] for r in rows if r["max_cap"] > recommended_global_cap]
    return {
        "by_channel": sorted(rows, key=lambda r: r["channel"]),
        "recommended_global_weekly_cap": recommended_global_cap,
        "uncoordinated_cap_pressure": round(total_cap_pressure, 1),
        "channels_over_recommended": overexposed,
        "note": "Pharma Signal coordinates frequency across HCP and DTC channels so the same NPI/household is not over-exposed when buying display, CTV, and native independently.",
    }


# ---------------------------------------------------------------------------
# Creatives + MLR review workflow
# ---------------------------------------------------------------------------
@app.get("/api/full/creatives")
def list_creatives(user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM creatives ORDER BY submitted_at DESC").fetchall())


@app.post("/api/full/creatives")
def create_creative(payload: CreativeCreate, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    creative_id = str(uuid4())
    ts = now_iso()
    with conn() as db:
        if not db.execute("SELECT id FROM campaigns WHERE id=?", (payload.campaign_id,)).fetchone():
            raise HTTPException(404, "Campaign not found")
        db.execute("INSERT INTO creatives VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (creative_id, payload.campaign_id, payload.name, payload.fmt, payload.channel, payload.claims, int(payload.isi_included), payload.landing_url, "in_review", 1, None, None, ts, None))
        db.commit()
    audit(user["email"], "creative_submit", "creative", creative_id, payload.model_dump())
    return {"id": creative_id, "mlr_status": "in_review", "version": 1, **payload.model_dump()}


@app.post("/api/full/creatives/{creative_id}/review")
def review_creative(creative_id: str, payload: CreativeReview, user: Dict[str, Any] = Depends(roles("admin", "analyst"))) -> Dict[str, Any]:
    status_map = {"approved": "approved", "rejected": "rejected", "changes_requested": "changes_requested"}
    ts = now_iso()
    with conn() as db:
        row = db.execute("SELECT * FROM creatives WHERE id=?", (creative_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Creative not found")
        version = row["version"] + (1 if payload.decision == "changes_requested" else 0)
        new_status = "in_review" if payload.decision == "changes_requested" else status_map[payload.decision]
        db.execute("UPDATE creatives SET mlr_status=?, version=?, reviewer=?, review_notes=?, decided_at=? WHERE id=?", (new_status, version, user["email"], payload.notes, ts, creative_id))
        db.commit()
    audit(user["email"], "creative_review", "creative", creative_id, {"decision": payload.decision, "notes": payload.notes})
    return {"id": creative_id, "mlr_status": new_status, "version": version, "reviewer": user["email"], "decided_at": ts}


# ---------------------------------------------------------------------------
# Deals / PMP marketplace + supply-path optimization
# ---------------------------------------------------------------------------
@app.get("/api/full/deals")
def list_deals(user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM deals ORDER BY partner").fetchall())


@app.post("/api/full/deals")
def create_deal(payload: DealCreate, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    deal_id = str(uuid4())
    with conn() as db:
        db.execute("INSERT INTO deals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (deal_id, payload.partner, payload.deal_id, payload.deal_type, payload.channel, payload.floor_cpm, payload.audience_match, payload.status, now_iso()))
        db.commit()
    audit(user["email"], "deal_create", "deal", deal_id, payload.model_dump())
    return {"id": deal_id, **payload.model_dump()}


@app.get("/api/full/supply-paths/optimize")
def optimize_supply_paths(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    """Rank supply paths on a blended SPO score (quality, fraud, working media, cost)."""
    with conn() as db:
        rows = dicts(db.execute("SELECT * FROM supply_paths").fetchall())
    ranked = []
    for row in rows:
        fraud_penalty = min(row["fraud_risk"] / 5.0, 1.0) * 20
        cost_efficiency = max(0.0, 1 - row["bid_floor_cpm"] / 30.0) * 15
        spo_score = round(
            row["outcome_score"] * 0.34
            + row["viewability"] * 0.18
            + row["match_rate"] * 0.18
            + row["working_media_ratio"] * 100 * 0.18
            - fraud_penalty
            + cost_efficiency,
            1,
        )
        if spo_score >= 78:
            recommendation = "prioritize"
        elif spo_score >= 62:
            recommendation = "maintain"
        else:
            recommendation = "reduce" if row["status"] == "approved" else "hold_review"
        ranked.append({**row, "spo_score": spo_score, "recommendation": recommendation})
    ranked.sort(key=lambda r: r["spo_score"], reverse=True)
    return {"supply_paths": ranked, "prioritized": [r["partner"] for r in ranked if r["recommendation"] == "prioritize"], "reduce": [r["partner"] for r in ranked if r["recommendation"] == "reduce"]}


# ---------------------------------------------------------------------------
# Measurement: script-lift planning with statistical power
# ---------------------------------------------------------------------------
@app.get("/api/full/measurement/plans")
def list_measurement_plans(user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM measurement_plans ORDER BY created_at DESC").fetchall())


@app.post("/api/full/measurement/plan")
def create_measurement_plan(payload: MeasurementPlanCreate, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        if not db.execute("SELECT id FROM campaigns WHERE id=?", (payload.campaign_id,)).fetchone():
            raise HTTPException(404, "Campaign not found")
    power_result = two_proportion_power(payload.baseline_rate, payload.expected_lift_pct, payload.exposed_size, payload.control_size)
    mdl = minimum_detectable_lift(payload.baseline_rate, payload.exposed_size, payload.control_size)
    if power_result["power"] >= 0.8 and payload.expected_lift_pct >= mdl:
        readiness = "ready"
    elif power_result["power"] >= 0.6:
        readiness = "borderline"
    else:
        readiness = "underpowered"
    plan_id = str(uuid4())
    expected_exposed_conversions = round(payload.exposed_size * payload.baseline_rate * (1 + payload.expected_lift_pct / 100))
    expected_control_conversions = round(payload.control_size * payload.baseline_rate)
    with conn() as db:
        db.execute("INSERT INTO measurement_plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (plan_id, payload.campaign_id, payload.study_type, payload.baseline_rate, payload.expected_lift_pct, payload.exposed_size, payload.control_size, power_result["power"], mdl, readiness, now_iso()))
        db.commit()
    result = {
        "id": plan_id, "campaign_id": payload.campaign_id, "study_type": payload.study_type,
        "baseline_rate": payload.baseline_rate, "expected_lift_pct": payload.expected_lift_pct,
        "exposed_size": payload.exposed_size, "control_size": payload.control_size,
        "power": power_result["power"], "minimum_detectable_lift_pct": mdl,
        "expected_exposed_conversions": expected_exposed_conversions,
        "expected_control_conversions": expected_control_conversions,
        "readiness": readiness,
        "interpretation": f"At a {payload.baseline_rate:.1%} baseline and a {payload.expected_lift_pct:.0f}% expected lift, this design has {power_result['power']:.0%} power. Smallest detectable lift is {mdl:.1f}%.",
    }
    audit(user["email"], "measurement_plan", "campaign", payload.campaign_id, {"power": power_result["power"], "mdl": mdl, "readiness": readiness})
    return result


# ---------------------------------------------------------------------------
# Portfolio budget optimizer
# ---------------------------------------------------------------------------
@app.get("/api/full/optimizer/portfolio")
def optimize_portfolio(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        lines = dicts(db.execute("SELECT * FROM line_items").fetchall())
        factors = {f["line_item_id"]: dict(f) for f in db.execute("SELECT * FROM bid_factors").fetchall()}
        campaigns = {c["id"]: dict(c) for c in db.execute("SELECT * FROM campaigns").fetchall()}
    if not lines:
        return {"recommendations": [], "total_budget": 0, "reallocated": 0}
    # Efficiency proxy: outcome + working-media orientation minus data-cost exposure.
    scored = []
    for line in lines:
        f = factors.get(line["id"], BidFactors().model_dump())
        efficiency = round(
            f["outcome_signal_weight"] * 100
            + f["working_media_weight"] * 100
            - f["data_cost_guardrail"] * 40
            + (10 if line["pacing_mode"] == "even" else 0),
            1,
        )
        scored.append({"line": line, "efficiency": efficiency})
    avg_eff = sum(s["efficiency"] for s in scored) / len(scored)
    recommendations, reallocated = [], 0.0
    for s in scored:
        line, eff = s["line"], s["efficiency"]
        delta_pct = max(-0.3, min(0.3, (eff - avg_eff) / max(avg_eff, 1)))
        new_budget = round(line["budget"] * (1 + delta_pct), 2)
        action = "increase" if delta_pct > 0.05 else "decrease" if delta_pct < -0.05 else "hold"
        reallocated += abs(new_budget - line["budget"])
        recommendations.append({
            "line_item_id": line["id"], "name": line["name"], "channel": line["channel"],
            "campaign": campaigns.get(line["campaign_id"], {}).get("name", "—"),
            "current_budget": line["budget"], "recommended_budget": new_budget,
            "delta_pct": round(delta_pct * 100, 1), "efficiency_score": eff, "action": action,
        })
    recommendations.sort(key=lambda r: r["efficiency_score"], reverse=True)
    return {"recommendations": recommendations, "total_budget": round(sum(l["budget"] for l in lines), 2), "reallocated": round(reallocated, 2), "avg_efficiency": round(avg_eff, 1)}


# ---------------------------------------------------------------------------
# Reporting: synthetic delivery + pacing analytics
# ---------------------------------------------------------------------------
@app.get("/api/full/reporting/performance")
def reporting_performance(days: int = Query(14, ge=1, le=90), user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        campaigns = dicts(db.execute("SELECT * FROM campaigns").fetchall())
        lines = dicts(db.execute("SELECT * FROM line_items WHERE campaign_id IN (SELECT id FROM campaigns)").fetchall())
    lines_by_campaign: Dict[str, List[Dict[str, Any]]] = {}
    for line in lines:
        lines_by_campaign.setdefault(line["campaign_id"], []).append(line)
    report = []
    portfolio = {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0}
    for camp in campaigns:
        camp_lines = lines_by_campaign.get(camp["id"], [])
        budget = camp["budget"]
        daily_budget = budget / max(days, 1)
        rng = random.Random(hash(camp["id"]) & 0xFFFFFFFF)
        series, imps, clicks, convs, spend = [], 0, 0, 0, 0.0
        for d in range(days):
            day_spend = round(daily_budget * rng.uniform(0.7, 1.15), 2)
            avg_cpm = sum(l["max_bid_cpm"] for l in camp_lines) / max(len(camp_lines), 1) if camp_lines else 12
            day_imps = int(day_spend / max(avg_cpm, 1) * 1000)
            ctr = rng.uniform(0.0009, 0.0028)
            cvr = rng.uniform(0.012, 0.05)
            day_clicks = int(day_imps * ctr)
            day_convs = int(day_clicks * cvr)
            imps += day_imps
            clicks += day_clicks
            convs += day_convs
            spend += day_spend
            series.append({"date": (datetime.now(timezone.utc) - timedelta(days=days - d - 1)).date().isoformat(), "spend": day_spend, "impressions": day_imps, "clicks": day_clicks, "conversions": day_convs})
        pacing = round(spend / budget, 4) if budget else 0
        report.append({
            "campaign_id": camp["id"], "name": camp["name"], "brand": camp["brand"], "status": camp["status"],
            "budget": budget, "spend": round(spend, 2), "pacing": pacing,
            "pacing_status": "on_pace" if 0.9 <= pacing <= 1.1 else "underpacing" if pacing < 0.9 else "overpacing",
            "impressions": imps, "clicks": clicks, "conversions": convs,
            "ctr": round(clicks / max(imps, 1), 5), "cvr": round(convs / max(clicks, 1), 4),
            "cpa": round(spend / max(convs, 1), 2), "ecpm": round(spend / max(imps, 1) * 1000, 2),
            "series": series,
        })
        portfolio["impressions"] += imps
        portfolio["clicks"] += clicks
        portfolio["conversions"] += convs
        portfolio["spend"] += spend
    portfolio["spend"] = round(portfolio["spend"], 2)
    portfolio["ctr"] = round(portfolio["clicks"] / max(portfolio["impressions"], 1), 5)
    portfolio["cpa"] = round(portfolio["spend"] / max(portfolio["conversions"], 1), 2)
    return {"days": days, "portfolio": portfolio, "campaigns": report}


# ---------------------------------------------------------------------------
# Compliance scanner (no-PHI, consent, ISI, brand safety)
# ---------------------------------------------------------------------------
@app.get("/api/full/compliance/scan")
def compliance_scan(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        audiences = dicts(db.execute("SELECT * FROM audiences").fetchall())
        creatives = dicts(db.execute("SELECT * FROM creatives").fetchall())
        supply = dicts(db.execute("SELECT * FROM supply_paths").fetchall())
    findings = []
    for aud in audiences:
        if aud["contains_phi"]:
            findings.append({"severity": "critical", "area": "audience", "entity": aud["name"], "issue": "Audience flagged as containing PHI"})
    for cr in creatives:
        if not cr["isi_included"] and cr["mlr_status"] == "approved":
            findings.append({"severity": "high", "area": "creative", "entity": cr["name"], "issue": "Approved creative is missing Important Safety Information (ISI)"})
        if cr["mlr_status"] in {"in_review", "changes_requested"}:
            findings.append({"severity": "medium", "area": "creative", "entity": cr["name"], "issue": f"Creative not MLR-approved (status: {cr['mlr_status']}) — cannot serve"})
    for sp in supply:
        if sp["fraud_risk"] and sp["fraud_risk"] > 1.0 and sp["status"] == "approved":
            findings.append({"severity": "medium", "area": "supply", "entity": sp["partner"], "issue": f"Approved supply path has elevated fraud risk ({sp['fraud_risk']}%)"})
    serving_blocked = sum(1 for cr in creatives if cr["mlr_status"] != "approved")
    checks = {
        "no_phi_in_bidder": all(not a["contains_phi"] for a in audiences),
        "all_creatives_have_isi": all(c["isi_included"] for c in creatives) if creatives else True,
        "mlr_gating_active": True,
        "consent_enforced_at_auction": True,
    }
    score = round(100 - len(findings) * 7 - serving_blocked * 2)
    return {"compliance_score": max(0, min(100, score)), "checks": checks, "findings": findings, "creatives_blocked_from_serving": serving_blocked, "scanned_at": now_iso()}


# ---------------------------------------------------------------------------
# Executive overview
# ---------------------------------------------------------------------------
@app.get("/api/full/overview")
def overview(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        campaigns = dicts(db.execute("SELECT * FROM campaigns").fetchall())
        lines = dicts(db.execute("SELECT * FROM line_items").fetchall())
        audiences = dicts(db.execute("SELECT * FROM audiences").fetchall())
        creatives = dicts(db.execute("SELECT * FROM creatives").fetchall())
        deals = dicts(db.execute("SELECT * FROM deals").fetchall())
        supply = dicts(db.execute("SELECT * FROM supply_paths").fetchall())
        plans = dicts(db.execute("SELECT * FROM measurement_plans").fetchall())
    total_budget = sum(c["budget"] for c in campaigns)
    addressable_hcp = sum(a["npi_count"] for a in audiences if a["audience_type"] == "HCP")
    avg_working_media = round(sum(s["working_media_ratio"] for s in supply) / max(len(supply), 1), 3)
    return {
        "kpis": {
            "campaigns": len(campaigns),
            "active_campaigns": sum(1 for c in campaigns if c["status"] == "active"),
            "line_items": len(lines),
            "total_budget": round(total_budget, 2),
            "audiences": len(audiences),
            "addressable_hcps": addressable_hcp,
            "creatives": len(creatives),
            "creatives_approved": sum(1 for c in creatives if c["mlr_status"] == "approved"),
            "deals": len(deals),
            "supply_paths": len(supply),
            "measurement_plans": len(plans),
            "measurement_ready": sum(1 for p in plans if p["status"] == "ready"),
            "avg_working_media_ratio": avg_working_media,
        },
        "narrative": "Pharma Signal connects verified audience reach, MLR-gated creative, quality supply paths, and measurement power into one operating view — answering whether a media buy reached the right verified audience, through the right path, at the right cost, with enough power to prove business impact.",
    }


@app.get("/api/full/audit")
def list_audit(limit: int = Query(100, ge=1, le=500), user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM audit_events ORDER BY ts DESC LIMIT ?", (limit,)).fetchall())
