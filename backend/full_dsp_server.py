"""Pharma Signal Full DSP Server.

Functional pharma-native Demand-Side Platform backend.

Storage: SQLite by default, or Postgres when DATABASE_URL is set (see storage.py).
Auth: HS256 JWT (stdlib hmac) + bcrypt password hashing + role-based access.

Capabilities (DeepIntent-class + pharma-native differentiators):
  - Auth, roles, and an append-only audit trail on every mutation
  - Campaign + line-item planning with flights, pacing, and budgets
  - Weighted, outcome-aware bid-factor engine and single-impression auction eval
  - OpenRTB-style bidstream simulation with second-price clearing, pacing, and
    per-user frequency capping
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

import base64
import csv
import hashlib
import hmac
import io
import json
import math
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import bcrypt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from storage import STORAGE_BACKEND, conn, dicts

app = FastAPI(title="Pharma Signal Full DSP", version="6.0.0")

# CORS origins are configurable: default "*" for local dev, or a comma-separated
# allowlist (e.g. "https://pharma-signal.netlify.app") to lock down production.
_cors_setting = os.environ.get("CORS_ORIGINS", "*").strip()
CORS_ORIGINS = ["*"] if _cors_setting in {"", "*"} else [o.strip() for o in _cors_setting.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.environ.get("FULL_DSP_JWT_SECRET", "pharma-signal-dev-secret-change-me")
JWT_TTL_SECONDS = int(os.environ.get("FULL_DSP_JWT_TTL", "43200"))  # 12 hours
# Absolute base used to build OpenRTB win-notice (nurl) and billing (burl) URLs.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

# Channel taxonomy (DeepIntent-style): typical CPM ranges, devices, and notes.
CHANNELS = [
    {"id": "Display", "label": "Display", "typical_cpm": [4, 12], "devices": ["desktop", "mobile", "tablet"], "note": "Banner & in-app display"},
    {"id": "Video", "label": "Online Video", "typical_cpm": [12, 28], "devices": ["desktop", "mobile", "tablet"], "note": "In-stream / out-stream video"},
    {"id": "CTV", "label": "Connected TV", "typical_cpm": [22, 45], "devices": ["ctv"], "note": "Streaming TV, non-skippable"},
    {"id": "Audio", "label": "Digital Audio", "typical_cpm": [8, 18], "devices": ["mobile", "desktop"], "note": "Podcast & streaming audio"},
    {"id": "Native", "label": "Native", "typical_cpm": [6, 16], "devices": ["desktop", "mobile", "tablet"], "note": "In-feed endemic health content"},
    {"id": "DOOH", "label": "Digital OOH", "typical_cpm": [6, 14], "devices": ["dooh"], "note": "Point-of-care & out-of-home screens"},
    {"id": "EHR", "label": "EHR / Point of Care", "typical_cpm": [18, 40], "devices": ["desktop"], "note": "Endemic EHR messaging at point of care"},
]
DEVICE_TYPES = ["desktop", "mobile", "tablet", "ctv", "dooh"]
BRAND_SAFETY_TIERS = ["standard", "strict", "pharma_sensitive"]


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit(actor: str, action: str, entity_type: str, entity_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    with conn() as db:
        db.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid4()), now_iso(), actor, action, entity_type, entity_id, json.dumps(metadata or {})),
        )
        db.commit()


# ---------------------------------------------------------------------------
# Auth: bcrypt password hashing + stdlib HS256 JWT
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, stored: str) -> bool:
    if stored.startswith("$2"):
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
        except ValueError:
            return False
    # Legacy sha256 hashes from earlier versions (migrated to bcrypt on login).
    return hashlib.sha256(plain.encode("utf-8")).hexdigest() == stored


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def create_access_token(user: Dict[str, Any]) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": user["id"], "email": user["email"], "role": user["role"], "iat": now, "exp": now + JWT_TTL_SECONDS}
    signing_input = _b64u(json.dumps(header, separators=(",", ":")).encode()) + "." + _b64u(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64u(hmac.new(JWT_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest())
    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(401, "Malformed token")
    header_b64, payload_b64, signature_b64 = parts
    expected = _b64u(hmac.new(JWT_SECRET.encode("utf-8"), f"{header_b64}.{payload_b64}".encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, signature_b64):
        raise HTTPException(401, "Invalid token signature")
    try:
        payload = json.loads(_b64u_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(401, "Invalid token payload")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(401, "Token expired")
    return payload


def current_user(authorization: str = Header(default="")) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    claims = decode_access_token(authorization[7:])
    with conn() as db:
        row = db.execute("SELECT id, email, name, role, created_at FROM users WHERE id=?", (claims["sub"],)).fetchone()
    if not row:
        raise HTTPException(401, "User no longer exists")
    return dict(row)


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


class OutcomeCreate(BaseModel):
    exposed_n: int = Field(gt=0)
    exposed_conversions: int = Field(ge=0)
    control_n: int = Field(gt=0)
    control_conversions: int = Field(ge=0)
    media_spend: float = Field(gt=0)
    rx_value_per_conversion: float = Field(default=0.0, ge=0)


class OverlapRequest(BaseModel):
    audience_ids: List[str] = Field(min_length=1)


# --- OpenRTB 2.x (subset) ---
class ORTBBanner(BaseModel):
    w: Optional[int] = None
    h: Optional[int] = None


class ORTBImp(BaseModel):
    id: str = "1"
    bidfloor: float = 0.0
    bidfloorcur: str = "USD"
    banner: Optional[ORTBBanner] = None
    tagid: Optional[str] = None


class ORTBGeo(BaseModel):
    country: Optional[str] = "USA"
    region: Optional[str] = None


class ORTBDevice(BaseModel):
    ua: Optional[str] = None
    ip: Optional[str] = None
    devicetype: Optional[int] = None   # OpenRTB: 2=desktop, 4=mobile, 5=tablet, 3/7=ctv
    geo: Optional[ORTBGeo] = None


class ORTBUser(BaseModel):
    id: Optional[str] = None
    buyeruid: Optional[str] = None
    consent: bool = True


class ORTBBidRequest(BaseModel):
    id: str
    imp: List[ORTBImp] = Field(min_length=1)
    device: Optional[ORTBDevice] = None
    user: Optional[ORTBUser] = None
    at: int = 2          # 2 = second-price
    tmax: int = 100
    cur: List[str] = Field(default_factory=lambda: ["USD"])
    test: int = 0


class DeliveryFact(BaseModel):
    fact_date: str
    campaign_id: Optional[str] = None
    partner: Optional[str] = None
    channel: Optional[str] = None
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    spend: float = Field(default=0.0, ge=0)


class IngestRequest(BaseModel):
    kind: str = Field(pattern="^(ga4|ssp|crossix|identity)$")
    rows: List[DeliveryFact] = Field(min_length=1)


class TargetingUpdate(BaseModel):
    devices: List[str] = Field(default_factory=list)
    geos: List[str] = Field(default_factory=list)
    dayparts: List[int] = Field(default_factory=list)   # hours of day, 0-23
    brand_safety: str = Field(default="standard", pattern="^(standard|strict|pharma_sensitive)$")
    viewability_target: float = Field(default=0.7, ge=0, le=1)


class PlannerChannel(BaseModel):
    channel: str
    pct: float = Field(ge=0, le=1)


class PlannerRequest(BaseModel):
    budget: float = Field(gt=0)
    frequency: float = Field(default=3.0, ge=1, le=20)
    channels: List[PlannerChannel] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Database bootstrap + seed
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, name TEXT, role TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, name TEXT, brand TEXT, indication TEXT, audience_type TEXT, objective TEXT, budget REAL, flight_start TEXT, flight_end TEXT, status TEXT, created_by TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS line_items (id TEXT PRIMARY KEY, campaign_id TEXT, name TEXT, channel TEXT, budget REAL, max_bid_cpm REAL, pacing_mode TEXT, status TEXT, frequency_cap INTEGER, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS bid_factors (line_item_id TEXT PRIMARY KEY, audience_quality_weight REAL, supply_quality_weight REAL, outcome_signal_weight REAL, contextual_relevance_weight REAL, working_media_weight REAL, frequency_penalty_weight REAL, bid_shading_pct REAL, max_bid_multiplier REAL, data_cost_guardrail REAL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS line_item_targeting (line_item_id TEXT PRIMARY KEY, devices TEXT, geos TEXT, dayparts TEXT, brand_safety TEXT, viewability_target REAL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS supply_paths (id TEXT PRIMARY KEY, partner TEXT, channel TEXT, deal_id TEXT, seller_type TEXT, bid_floor_cpm REAL, viewability REAL, fraud_risk REAL, match_rate REAL, working_media_ratio REAL, outcome_score REAL, status TEXT);
CREATE TABLE IF NOT EXISTS audiences (id TEXT PRIMARY KEY, name TEXT, audience_type TEXT, description TEXT, npi_count INTEGER, reach INTEGER, match_rate REAL, data_cpm REAL, refresh_cadence TEXT, contains_phi INTEGER, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS creatives (id TEXT PRIMARY KEY, campaign_id TEXT, name TEXT, fmt TEXT, channel TEXT, claims TEXT, isi_included INTEGER, landing_url TEXT, mlr_status TEXT, version INTEGER, reviewer TEXT, review_notes TEXT, submitted_at TEXT, decided_at TEXT);
CREATE TABLE IF NOT EXISTS deals (id TEXT PRIMARY KEY, partner TEXT, deal_id TEXT, deal_type TEXT, channel TEXT, floor_cpm REAL, audience_match REAL, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS measurement_plans (id TEXT PRIMARY KEY, campaign_id TEXT, study_type TEXT, baseline_rate REAL, expected_lift_pct REAL, exposed_size INTEGER, control_size INTEGER, power REAL, mdl REAL, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS measurement_results (id TEXT PRIMARY KEY, plan_id TEXT, campaign_id TEXT, exposed_n INTEGER, exposed_conversions INTEGER, control_n INTEGER, control_conversions INTEGER, media_spend REAL, rx_value REAL, observed_lift_pct REAL, absolute_lift_pp REAL, ci_low_pp REAL, ci_high_pp REAL, p_value REAL, significant INTEGER, incremental_conversions INTEGER, cpic REAL, roas REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS connectors (id TEXT PRIMARY KEY, name TEXT, kind TEXT, status TEXT, config_json TEXT, last_sync TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS delivery_facts (id TEXT PRIMARY KEY, connector_id TEXT, source TEXT, fact_date TEXT, campaign_id TEXT, partner TEXT, channel TEXT, impressions INTEGER, clicks INTEGER, conversions INTEGER, spend REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS rtb_wins (id TEXT PRIMARY KEY, line_item_id TEXT, request_id TEXT, imp_id TEXT, partner TEXT, bid_price_cpm REAL, clear_price_cpm REAL, status TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS frequency_ledger (line_item_id TEXT, user_key INTEGER, impressions INTEGER, last_ts TEXT, PRIMARY KEY (line_item_id, user_key));
CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, ts TEXT, actor TEXT, action TEXT, entity_type TEXT, entity_id TEXT, metadata_json TEXT);
"""


def init_db() -> None:
    with conn() as db:
        db.executescript(SCHEMA)
        if not db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            seed_password = os.environ.get("FULL_DSP_DEV_PASSWORD", "pharma-signal-local")
            pw_hash = hash_password(seed_password)
            for email, name, role in [("admin@pharmasignal.local", "Admin", "admin"), ("trader@pharmasignal.local", "Trader", "trader"), ("analyst@pharmasignal.local", "Analyst", "analyst")]:
                db.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)", (str(uuid4()), email, pw_hash, name, role, now_iso()))
        if not db.execute("SELECT 1 FROM supply_paths LIMIT 1").fetchone():
            seed_supply = [
                ("PubMatic", "Display", "PM-PHARMA-HCP-001", "Direct", 6.8, 69, 1.1, 71, 0.54, 82, "approved"),
                ("OpenX", "Display", "OX-HEALTH-WEB-117", "SPO verified", 7.4, 72, 1.4, 68, 0.62, 79, "approved"),
                ("Magnite", "CTV", "MG-CTV-RSV-902", "Direct", 21.8, 92, 0.4, 62, 0.71, 88, "approved"),
                ("Index Exchange", "Display", "IX-PHARMA-WEB-219", "SPO verified", 5.4, 78, 0.8, 58, 0.70, 84, "review"),
                ("Endemic Health Network", "Native", "EH-ONC-NATIVE-009", "Direct", 24.0, 81, 0.5, 64, 0.58, 91, "approved"),
            ]
            for row in seed_supply:
                db.execute("INSERT INTO supply_paths VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), *row))
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
        if not db.execute("SELECT 1 FROM connectors LIMIT 1").fetchone():
            seed_connectors = [
                ("GA4 Engagement", "ga4", "mock", '{"property_id": "", "note": "Set GA4 property + service-account to go live"}'),
                ("SSP Delivery — PubMatic", "ssp", "mock", '{"partner": "PubMatic", "report_api": ""}'),
                ("Crossix Measurement", "crossix", "mock", '{"feed": "", "note": "Rx/script-lift exposed-control feed"}'),
                ("Identity — LiveRamp", "identity", "mock", '{"ramp_id": "", "note": "NPI / household identity resolution"}'),
            ]
            for name, kind, status, config in seed_connectors:
                db.execute("INSERT INTO connectors VALUES (?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), name, kind, status, config, None, now_iso()))
        db.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Health + auth
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "pharma-signal-full-dsp", "storage": STORAGE_BACKEND}


@app.post("/api/full/auth/login")
def login(payload: LoginRequest) -> Dict[str, Any]:
    init_db()
    with conn() as db:
        row = db.execute("SELECT * FROM users WHERE lower(email)=lower(?)", (payload.email,)).fetchone()
        if not row or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(401, "Invalid email or password")
        row = dict(row)
        if not row["password_hash"].startswith("$2"):
            db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(payload.password), row["id"]))
            db.commit()
    user = {k: row[k] for k in row if k != "password_hash"}
    token = create_access_token(user)
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


@app.get("/api/full/channels")
def list_channels(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    return {"channels": CHANNELS, "devices": DEVICE_TYPES, "brand_safety_tiers": BRAND_SAFETY_TIERS}


@app.post("/api/full/planner")
def media_planner(payload: PlannerRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    """Allocate budget across channels and forecast impressions / reach using the CPM taxonomy."""
    cmap = {c["id"]: c for c in CHANNELS}
    chans = payload.channels
    if not chans:
        default = ["Display", "Native", "CTV", "Video"]
        chans = [PlannerChannel(channel=c, pct=round(1 / len(default), 4)) for c in default]
    total_pct = sum(c.pct for c in chans) or 1.0
    rows, tot_spend, tot_imps = [], 0.0, 0
    for c in chans:
        meta = cmap.get(c.channel)
        if not meta:
            raise HTTPException(400, f"Unknown channel: {c.channel}")
        norm = c.pct / total_pct
        spend = round(payload.budget * norm, 2)
        cpm = (meta["typical_cpm"][0] + meta["typical_cpm"][1]) / 2
        imps = int(spend / cpm * 1000)
        rows.append({"channel": c.channel, "pct": round(norm, 4), "spend": spend, "cpm": cpm, "impressions": imps, "est_reach": int(imps / max(payload.frequency, 1))})
        tot_spend += spend
        tot_imps += imps
    return {
        "budget": payload.budget, "frequency": payload.frequency, "channels": rows,
        "totals": {
            "spend": round(tot_spend, 2), "impressions": tot_imps,
            "blended_cpm": round(tot_spend / max(tot_imps, 1) * 1000, 2),
            "est_unique_reach": int(tot_imps / max(payload.frequency, 1)),
        },
    }


def _targeting_defaults(line_item_id: str) -> Dict[str, Any]:
    return {"line_item_id": line_item_id, "devices": [], "geos": [], "dayparts": [], "brand_safety": "standard", "viewability_target": 0.7, "updated_at": None}


@app.get("/api/full/line-items/{line_item_id}/targeting")
def get_targeting(line_item_id: str, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        row = db.execute("SELECT * FROM line_item_targeting WHERE line_item_id=?", (line_item_id,)).fetchone()
    if not row:
        return _targeting_defaults(line_item_id)
    row = dict(row)
    return {
        "line_item_id": line_item_id,
        "devices": json.loads(row["devices"] or "[]"),
        "geos": json.loads(row["geos"] or "[]"),
        "dayparts": json.loads(row["dayparts"] or "[]"),
        "brand_safety": row["brand_safety"],
        "viewability_target": row["viewability_target"],
        "updated_at": row["updated_at"],
    }


@app.put("/api/full/line-items/{line_item_id}/targeting")
def set_targeting(line_item_id: str, payload: TargetingUpdate, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    bad_devices = set(payload.devices) - set(DEVICE_TYPES)
    if bad_devices:
        raise HTTPException(400, f"Unknown device types: {sorted(bad_devices)}")
    if any(h < 0 or h > 23 for h in payload.dayparts):
        raise HTTPException(400, "Dayparts must be hours 0-23")
    ts = now_iso()
    with conn() as db:
        if not db.execute("SELECT id FROM line_items WHERE id=?", (line_item_id,)).fetchone():
            raise HTTPException(404, "Line item not found")
        exists = db.execute("SELECT line_item_id FROM line_item_targeting WHERE line_item_id=?", (line_item_id,)).fetchone()
        values = (json.dumps(payload.devices), json.dumps(payload.geos), json.dumps(payload.dayparts), payload.brand_safety, payload.viewability_target, ts)
        if exists:
            db.execute("UPDATE line_item_targeting SET devices=?, geos=?, dayparts=?, brand_safety=?, viewability_target=?, updated_at=? WHERE line_item_id=?", (*values, line_item_id))
        else:
            db.execute("INSERT INTO line_item_targeting VALUES (?, ?, ?, ?, ?, ?, ?)", (line_item_id, *values))
        db.commit()
    audit(user["email"], "targeting_update", "line_item", line_item_id, payload.model_dump())
    return {"line_item_id": line_item_id, **payload.model_dump(), "updated_at": ts}


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


ORTB_DEVICE_MAP = {2: "desktop", 4: "mobile", 1: "mobile", 5: "tablet", 3: "ctv", 7: "ctv", 6: "dooh"}


def _load_targeting(db, line_item_id: str) -> Dict[str, Any]:
    row = db.execute("SELECT * FROM line_item_targeting WHERE line_item_id=?", (line_item_id,)).fetchone()
    if not row:
        return {"devices": [], "geos": [], "dayparts": [], "brand_safety": "standard", "viewability_target": 0.0}
    row = dict(row)
    return {
        "devices": json.loads(row["devices"] or "[]"),
        "geos": json.loads(row["geos"] or "[]"),
        "dayparts": json.loads(row["dayparts"] or "[]"),
        "brand_safety": row["brand_safety"],
        "viewability_target": row["viewability_target"] or 0.0,
    }


def _targeting_block(targeting: Dict[str, Any], *, device: Optional[str], geo: Optional[str], hour: int, supply: Dict[str, Any]) -> List[str]:
    """Return block reasons if an impression fails the line item's targeting (empty = passes)."""
    reasons: List[str] = []
    if targeting["devices"] and device and device not in targeting["devices"]:
        reasons.append(f"device '{device}' not in targeting")
    if targeting["geos"] and geo:
        if not any(geo.upper() in g.upper() or g.upper() in geo.upper() for g in targeting["geos"]):
            reasons.append(f"geo '{geo}' not in targeting")
    if targeting["dayparts"] and hour not in targeting["dayparts"]:
        reasons.append(f"hour {hour} outside dayparts")
    view = (supply.get("viewability") or 0) / 100.0
    if targeting["viewability_target"] and view < targeting["viewability_target"]:
        reasons.append("below viewability floor")
    fraud = supply.get("fraud_risk") or 0
    if targeting["brand_safety"] == "pharma_sensitive" and fraud > 0.8:
        reasons.append("brand safety (pharma-sensitive): fraud risk")
    elif targeting["brand_safety"] == "strict" and fraud > 1.5:
        reasons.append("brand safety (strict): fraud risk")
    return reasons


@app.post("/api/full/auction/evaluate")
def evaluate_auction(payload: AuctionEvaluateRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        line = db.execute("SELECT * FROM line_items WHERE id=?", (payload.line_item_id,)).fetchone()
        factors = db.execute("SELECT * FROM bid_factors WHERE line_item_id=?", (payload.line_item_id,)).fetchone()
        supply = db.execute("SELECT * FROM supply_paths WHERE id=?", (payload.supply_path_id,)).fetchone()
    if not line or not factors or not supply:
        raise HTTPException(404, "Line item, bid factors, or supply path not found")
    line, factors, supply = dict(line), dict(factors), dict(supply)
    scored = _score_impression(
        factors, line,
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
        targeting = _load_targeting(db, payload.line_item_id) if line else None
        # Load persisted per-user frequency so caps carry across simulation runs.
        ledger_rows = dicts(db.execute("SELECT user_key, impressions FROM frequency_ledger WHERE line_item_id=?", (payload.line_item_id,)).fetchall()) if line else []
    if not line or not factors:
        raise HTTPException(404, "Line item or bid factors not found")
    if not supply_rows:
        raise HTTPException(400, "No supply paths configured")
    factors_d, line_d = dict(factors), dict(line)
    geo_pool = ["US-CA", "US-NY", "US-TX", "US-FL", "US-IL"]

    # Pacing budget for this simulation window, and a modeled user pool so we can
    # enforce real per-user frequency caps across the request stream.
    sim_budget = round(payload.requests * line_d["max_bid_cpm"] / 1000 * 0.45, 2)
    user_pool = max(50, payload.requests // 5)
    freq_seen: Dict[int, int] = {int(r["user_key"]): int(r["impressions"]) for r in ledger_rows}
    starting_users = len(freq_seen)

    tally = {"bid": 0, "throttle": 0, "no_bid": 0, "blocked": 0}
    wins, spend_cpm, clearing_sum, second_price_sum, score_sum = 0, 0.0, 0.0, 0.0, 0.0
    frequency_capped, pace_throttled, targeting_filtered = 0, 0, 0
    by_partner: Dict[str, Dict[str, Any]] = {}

    for i in range(payload.requests):
        supply = rng.choice(supply_rows)
        uid = rng.randrange(user_pool)
        seen = freq_seen.get(uid, 0)
        contains_phi = rng.random() < payload.phi_leak_rate
        # Targeting filter (devices / geo / dayparts / brand safety / viewability).
        if targeting:
            req_device = rng.choice(DEVICE_TYPES)
            req_geo = rng.choice(geo_pool)
            req_hour = rng.randrange(24)
            if _targeting_block(targeting, device=req_device, geo=req_geo, hour=req_hour, supply=supply):
                targeting_filtered += 1
                continue
        scored = _score_impression(
            factors_d, line_d,
            audience_quality=rng.uniform(55, 98), supply_quality=supply["outcome_score"], outcome_signal=rng.uniform(45, 95),
            contextual_relevance=rng.uniform(50, 95), working_media_ratio=supply["working_media_ratio"], data_cost_ratio=rng.uniform(0.1, 0.5),
            frequency_seen_today=seen, floor_cpm=supply["bid_floor_cpm"], supply_status=supply["status"],
            contains_phi=contains_phi, creative_approved=True, geo_allowed=rng.random() > 0.02, consent_ok=rng.random() > 0.03,
        )
        score_sum += scored["weighted_score"]
        partner = by_partner.setdefault(supply["partner"], {"requests": 0, "wins": 0, "spend_cpm": 0.0})
        partner["requests"] += 1

        if seen >= line_d["frequency_cap"] and scored["decision"] in {"bid", "throttle"}:
            frequency_capped += 1

        # Pacing control: if cumulative spend is ahead of a linear pacing target,
        # throttle eligible impressions to protect the flight from front-loading.
        progress = (i + 1) / payload.requests
        ahead_of_pace = sim_budget > 0 and (spend_cpm / 1000) > sim_budget * progress * 1.05
        if ahead_of_pace and scored["decision"] in {"bid", "throttle"}:
            pace_throttled += 1
            tally["throttle"] += 1
            continue

        tally[scored["decision"]] += 1
        if scored["decision"] in {"bid", "throttle"} and scored["clearing_price_cpm"]:
            # Second-price auction: pay the strongest competitor's price (capped by our bid).
            competitor = supply["bid_floor_cpm"] * rng.uniform(0.7, 1.6)
            if scored["bid_cpm"] >= competitor:
                clear_price = round(min(scored["bid_cpm"], max(supply["bid_floor_cpm"], competitor)), 2)
                wins += 1
                spend_cpm += clear_price
                clearing_sum += clear_price
                second_price_sum += competitor
                freq_seen[uid] = seen + 1
                partner["wins"] += 1
                partner["spend_cpm"] += clear_price

    bids = tally["bid"] + tally["throttle"]
    unique_reach = len(freq_seen)
    total_imps = sum(freq_seen.values())
    spend = round(spend_cpm / 1000, 2)
    summary = {
        "requests": payload.requests,
        "decisions": tally,
        "bid_rate": round(bids / payload.requests, 4),
        "win_rate": round(wins / max(bids, 1), 4),
        "impressions_won": wins,
        "avg_clearing_cpm": round(clearing_sum / max(wins, 1), 2),
        "avg_second_price_cpm": round(second_price_sum / max(wins, 1), 2),
        "est_spend": spend,
        "sim_budget": sim_budget,
        "budget_utilization": round(spend / sim_budget, 4) if sim_budget else 0,
        "avg_weighted_score": round(score_sum / payload.requests, 1),
        "phi_blocked": tally["blocked"],
        "frequency_capped": frequency_capped,
        "pace_throttled": pace_throttled,
        "targeting_filtered": targeting_filtered,
        "unique_reach": unique_reach,
        "avg_frequency": round(total_imps / max(unique_reach, 1), 2),
        "by_partner": [
            {"partner": p, "requests": v["requests"], "wins": v["wins"], "win_rate": round(v["wins"] / max(v["requests"], 1), 4), "est_spend": round(v["spend_cpm"] / 1000, 2)}
            for p, v in sorted(by_partner.items(), key=lambda kv: kv[1]["wins"], reverse=True)
        ],
    }
    summary["carried_over_users"] = starting_users
    summary["persisted_users"] = len(freq_seen)
    # Persist the updated per-user frequency so the next run accumulates.
    ts = now_iso()
    with conn() as db:
        for user_key, imps in freq_seen.items():
            cur = db.execute("UPDATE frequency_ledger SET impressions=?, last_ts=? WHERE line_item_id=? AND user_key=?", (imps, ts, payload.line_item_id, user_key))
            if cur.rowcount == 0:
                db.execute("INSERT INTO frequency_ledger VALUES (?, ?, ?, ?)", (payload.line_item_id, user_key, imps, ts))
        db.commit()
    audit(user["email"], "bidstream_simulate", "line_item", payload.line_item_id, {"requests": payload.requests, "win_rate": summary["win_rate"]})
    return summary


# ---------------------------------------------------------------------------
# OpenRTB 2.x bid endpoint + win-notice (nurl) / billing (burl) handlers
# ---------------------------------------------------------------------------
@app.post("/api/full/rtb/bid")
def rtb_bid(req: ORTBBidRequest, line_item_id: str = Query(...), user: Dict[str, Any] = Depends(current_user)):
    """Evaluate an OpenRTB BidRequest and return a BidResponse (or 204 no-bid)."""
    with conn() as db:
        line = db.execute("SELECT * FROM line_items WHERE id=?", (line_item_id,)).fetchone()
        factors = db.execute("SELECT * FROM bid_factors WHERE line_item_id=?", (line_item_id,)).fetchone()
        supply = db.execute("SELECT * FROM supply_paths WHERE status='approved' ORDER BY outcome_score DESC LIMIT 1").fetchone()
        targeting = _load_targeting(db, line_item_id) if line else None
    if not line or not factors:
        raise HTTPException(404, "Line item or bid factors not found")
    line, factors = dict(line), dict(factors)
    supply = dict(supply) if supply else {"partner": "OpenMarket", "bid_floor_cpm": 1.0, "outcome_score": 78, "working_media_ratio": 0.6, "viewability": 70, "fraud_risk": 0.5, "status": "approved"}
    rng = random.Random(hash(req.id) & 0xFFFFFFFF)
    geo_ok = True
    req_geo, req_device = None, None
    if req.device:
        if req.device.geo:
            req_geo = req.device.geo.region or req.device.geo.country
            if req.device.geo.country:
                geo_ok = req.device.geo.country.upper() in {"USA", "US"}
        if req.device.devicetype is not None:
            req_device = ORTB_DEVICE_MAP.get(req.device.devicetype)
    req_hour = datetime.now(timezone.utc).hour
    consent_ok = req.user.consent if req.user else True
    ts = now_iso()
    bids: List[Dict[str, Any]] = []
    filtered_reasons: List[str] = []
    with conn() as db:
        for imp in req.imp:
            if targeting:
                blocks = _targeting_block(targeting, device=req_device, geo=req_geo, hour=req_hour, supply=supply)
                if blocks:
                    filtered_reasons.extend(blocks)
                    continue
            floor = imp.bidfloor or supply["bid_floor_cpm"]
            scored = _score_impression(
                factors, line,
                audience_quality=rng.uniform(60, 96), supply_quality=supply["outcome_score"], outcome_signal=rng.uniform(50, 92),
                contextual_relevance=rng.uniform(55, 95), working_media_ratio=supply["working_media_ratio"], data_cost_ratio=rng.uniform(0.1, 0.4),
                frequency_seen_today=0, floor_cpm=max(floor, 0.01), supply_status=supply["status"],
                contains_phi=False, creative_approved=True, geo_allowed=geo_ok, consent_ok=consent_ok,
            )
            if scored["decision"] in {"bid", "throttle"} and scored["clearing_price_cpm"] and scored["bid_cpm"] >= floor:
                win_id = str(uuid4())
                db.execute("INSERT INTO rtb_wins VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (win_id, line_item_id, req.id, imp.id, supply["partner"], scored["bid_cpm"], None, "bid", ts))
                bids.append({
                    "id": win_id, "impid": imp.id, "price": scored["bid_cpm"],
                    "nurl": f"{PUBLIC_BASE_URL}/api/full/rtb/win?wid={win_id}&price=" + "${AUCTION_PRICE}",
                    "burl": f"{PUBLIC_BASE_URL}/api/full/rtb/billing?wid={win_id}",
                    "adm": "<MLR-approved creative markup>", "crid": "ps-creative-1",
                    "w": imp.banner.w if imp.banner else None, "h": imp.banner.h if imp.banner else None,
                })
        db.commit()
    if not bids:
        return Response(status_code=204)  # OpenRTB no-bid
    audit(user["email"], "rtb_bid", "line_item", line_item_id, {"request_id": req.id, "bids": len(bids)})
    return {"id": req.id, "bidid": str(uuid4()), "cur": "USD", "seatbid": [{"seat": "pharma-signal", "bid": bids}]}


@app.get("/api/full/rtb/win")
def rtb_win(wid: str, price: float = 0.0):
    """Win notice (nurl). The exchange substitutes ${AUCTION_PRICE} with the clearing price."""
    with conn() as db:
        if db.execute("SELECT 1 FROM rtb_wins WHERE id=?", (wid,)).fetchone():
            db.execute("UPDATE rtb_wins SET clear_price_cpm=?, status=? WHERE id=?", (price, "won", wid))
            db.commit()
    return Response(status_code=200)


@app.get("/api/full/rtb/billing")
def rtb_billing(wid: str):
    """Billing notice (burl) — fired when the impression is rendered/billable."""
    with conn() as db:
        if db.execute("SELECT 1 FROM rtb_wins WHERE id=?", (wid,)).fetchone():
            db.execute("UPDATE rtb_wins SET status=? WHERE id=?", ("billed", wid))
            db.commit()
    return Response(status_code=200)


@app.get("/api/full/rtb/wins")
def list_rtb_wins(limit: int = Query(50, ge=1, le=500), user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM rtb_wins ORDER BY ts DESC LIMIT ?", (limit,)).fetchall())


@app.get("/api/full/frequency/state/{line_item_id}")
def frequency_state(line_item_id: str, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    """Persisted cross-run per-user frequency for a line item."""
    with conn() as db:
        rows = dicts(db.execute("SELECT user_key, impressions FROM frequency_ledger WHERE line_item_id=? ORDER BY impressions DESC", (line_item_id,)).fetchall())
        line = db.execute("SELECT frequency_cap FROM line_items WHERE id=?", (line_item_id,)).fetchone()
    cap = dict(line)["frequency_cap"] if line else 0
    total = sum(int(r["impressions"]) for r in rows)
    unique = len(rows)
    return {
        "line_item_id": line_item_id, "frequency_cap": cap,
        "unique_users": unique, "total_impressions": total,
        "avg_frequency": round(total / max(unique, 1), 2),
        "over_cap_users": sum(1 for r in rows if int(r["impressions"]) > cap),
        "top": [{"user_key": int(r["user_key"]), "impressions": int(r["impressions"])} for r in rows[:10]],
    }


@app.post("/api/full/frequency/state/{line_item_id}/reset")
def reset_frequency_state(line_item_id: str, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    with conn() as db:
        db.execute("DELETE FROM frequency_ledger WHERE line_item_id=?", (line_item_id,))
        db.commit()
    audit(user["email"], "frequency_reset", "line_item", line_item_id, {})
    return {"line_item_id": line_item_id, "reset": True}


EXPORT_QUERIES = {
    "campaigns": "SELECT id, name, brand, indication, audience_type, objective, budget, status, flight_start, flight_end FROM campaigns ORDER BY created_at DESC",
    "audit": "SELECT ts, actor, action, entity_type, entity_id FROM audit_events ORDER BY ts DESC LIMIT 2000",
    "wins": "SELECT ts, line_item_id, partner, bid_price_cpm, clear_price_cpm, status FROM rtb_wins ORDER BY ts DESC LIMIT 5000",
    "delivery": "SELECT fact_date, source, campaign_id, partner, channel, impressions, clicks, conversions, spend FROM delivery_facts ORDER BY fact_date DESC LIMIT 5000",
}


@app.get("/api/full/export")
def export_csv(dataset: str = Query(...), user: Dict[str, Any] = Depends(current_user)) -> Response:
    """Export a dataset as CSV (campaigns | audit | wins | delivery)."""
    query = EXPORT_QUERIES.get(dataset)
    if not query:
        raise HTTPException(404, f"Unknown dataset. Options: {sorted(EXPORT_QUERIES)}")
    with conn() as db:
        rows = dicts(db.execute(query).fetchall())
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if rows:
        writer.writerow(list(rows[0].keys()))
        for row in rows:
            writer.writerow(list(row.values()))
    else:
        writer.writerow(["(no rows)"])
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=pharma-signal-{dataset}.csv"})


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


@app.post("/api/full/audiences/overlap")
def audience_overlap(payload: OverlapRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    """Identity resolution: dedupe overlapping reach across audiences into unique reach."""
    placeholders = ",".join("?" for _ in payload.audience_ids)
    with conn() as db:
        rows = dicts(db.execute(f"SELECT * FROM audiences WHERE id IN ({placeholders})", tuple(payload.audience_ids)).fetchall())
    if not rows:
        raise HTTPException(404, "No audiences found")
    combined = sum(r["reach"] for r in rows)
    addressable_npis = sum(r["npi_count"] for r in rows)
    matched = [r for r in rows if r["match_rate"] > 0]
    avg_match = round(sum(r["match_rate"] * r["reach"] for r in matched) / max(sum(r["reach"] for r in matched), 1), 3) if matched else 0.0
    pairs, overlap_total = [], 0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            # Same-type audiences (e.g. HCP + HCP) overlap more than cross-type.
            factor = 0.32 if a["audience_type"] == b["audience_type"] else 0.06
            ov = int(min(a["reach"], b["reach"]) * factor)
            overlap_total += ov
            pairs.append({"a": a["name"], "b": b["name"], "overlap": ov})
    deduped_unique = max(0, combined - overlap_total)
    return {
        "audiences": [{"id": r["id"], "name": r["name"], "type": r["audience_type"], "reach": r["reach"], "npi_count": r["npi_count"], "match_rate": r["match_rate"]} for r in rows],
        "combined_reach": combined,
        "deduplicated_unique_reach": deduped_unique,
        "overlap": overlap_total,
        "overlap_pct": round(overlap_total / max(combined, 1), 4),
        "addressable_npis": addressable_npis,
        "avg_match_rate": avg_match,
        "pairs": pairs,
        "note": "Identity resolution dedupes overlapping reach across audiences so unique addressable reach (not summed reach) drives planning and frequency.",
    }


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
        row = dict(row)
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
# Measurement: closed-loop observed results (Crossix / Swoop style)
# ---------------------------------------------------------------------------
@app.post("/api/full/measurement/{plan_id}/results")
def record_measurement_results(plan_id: str, payload: OutcomeCreate, user: Dict[str, Any] = Depends(roles("admin", "analyst"))) -> Dict[str, Any]:
    """Record observed exposed/control conversions and compute measured incremental lift."""
    with conn() as db:
        plan = db.execute("SELECT * FROM measurement_plans WHERE id=?", (plan_id,)).fetchone()
    if not plan:
        raise HTTPException(404, "Measurement plan not found")
    plan = dict(plan)
    p_exposed = payload.exposed_conversions / payload.exposed_n
    p_control = payload.control_conversions / payload.control_n
    absolute_lift = p_exposed - p_control
    relative_lift_pct = round((p_exposed / p_control - 1) * 100, 2) if p_control > 0 else 0.0
    pooled = (payload.exposed_conversions + payload.control_conversions) / (payload.exposed_n + payload.control_n)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / payload.exposed_n + 1 / payload.control_n)) if 0 < pooled < 1 else 0.0
    z = absolute_lift / se_pooled if se_pooled > 0 else 0.0
    p_value = round(2 * (1 - norm_cdf(abs(z))), 5)
    se_unpooled = math.sqrt(p_exposed * (1 - p_exposed) / payload.exposed_n + p_control * (1 - p_control) / payload.control_n)
    ci_low_pp = round((absolute_lift - 1.96 * se_unpooled) * 100, 3)
    ci_high_pp = round((absolute_lift + 1.96 * se_unpooled) * 100, 3)
    significant = bool(p_value < 0.05 and absolute_lift > 0)
    incremental = round(absolute_lift * payload.exposed_n)
    cpic = round(payload.media_spend / incremental, 2) if incremental > 0 else None
    incremental_value = incremental * payload.rx_value_per_conversion
    roas = round(incremental_value / payload.media_spend, 2) if payload.media_spend > 0 and incremental > 0 else None
    result_id = str(uuid4())
    with conn() as db:
        db.execute(
            "INSERT INTO measurement_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (result_id, plan_id, plan["campaign_id"], payload.exposed_n, payload.exposed_conversions, payload.control_n, payload.control_conversions, payload.media_spend, payload.rx_value_per_conversion, relative_lift_pct, round(absolute_lift * 100, 3), ci_low_pp, ci_high_pp, p_value, int(significant), incremental, cpic, roas, now_iso()),
        )
        db.commit()
    if significant:
        verdict = "Significant incremental lift — campaign moved the outcome."
    elif absolute_lift > 0:
        verdict = "Positive but not statistically significant — collect more exposure or extend the flight."
    else:
        verdict = "No measured lift — revisit audience quality, supply paths, and frequency."
    result = {
        "id": result_id, "plan_id": plan_id, "campaign_id": plan["campaign_id"], "study_type": plan["study_type"],
        "exposed_rate": round(p_exposed, 5), "control_rate": round(p_control, 5),
        "observed_relative_lift_pct": relative_lift_pct,
        "absolute_lift_pp": round(absolute_lift * 100, 3),
        "ci_95_pp": [ci_low_pp, ci_high_pp],
        "p_value": p_value, "significant": significant,
        "incremental_conversions": incremental,
        "cost_per_incremental_conversion": cpic,
        "roas": roas, "media_spend": payload.media_spend,
        "planned_lift_pct": plan["expected_lift_pct"], "planned_power": plan["power"],
        "verdict": verdict,
    }
    audit(user["email"], "measurement_results", "campaign", plan["campaign_id"], {"significant": significant, "relative_lift_pct": relative_lift_pct, "p_value": p_value})
    return result


@app.get("/api/full/measurement/results")
def list_measurement_results(user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        rows = dicts(db.execute("SELECT * FROM measurement_results ORDER BY created_at DESC").fetchall())
        campaigns = {c["id"]: dict(c) for c in db.execute("SELECT id, name FROM campaigns").fetchall()}
    for row in rows:
        row["significant"] = bool(row["significant"])
        row["campaign_name"] = campaigns.get(row["campaign_id"], {}).get("name", "—")
    return rows


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
# Reporting: live delivery facts when present, else simulated
# ---------------------------------------------------------------------------
@app.get("/api/full/reporting/performance")
def reporting_performance(days: int = Query(14, ge=1, le=90), user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        campaigns = dicts(db.execute("SELECT * FROM campaigns").fetchall())
        lines = dicts(db.execute("SELECT * FROM line_items").fetchall())
        facts = dicts(db.execute("SELECT * FROM delivery_facts WHERE source IN ('ssp', 'identity')").fetchall())
    lines_by_campaign: Dict[str, List[Dict[str, Any]]] = {}
    for line in lines:
        lines_by_campaign.setdefault(line["campaign_id"], []).append(line)
    facts_by_campaign: Dict[str, List[Dict[str, Any]]] = {}
    for fact in facts:
        facts_by_campaign.setdefault(fact["campaign_id"], []).append(fact)

    report = []
    portfolio = {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0}
    live_campaigns = 0
    for camp in campaigns:
        budget = camp["budget"]
        camp_facts = facts_by_campaign.get(camp["id"], [])
        if camp_facts:
            # Live: aggregate ingested SSP/identity delivery facts by date.
            source = "live"
            by_date: Dict[str, Dict[str, float]] = {}
            for fact in camp_facts:
                bucket = by_date.setdefault(fact["fact_date"], {"spend": 0.0, "impressions": 0, "clicks": 0, "conversions": 0})
                bucket["spend"] += fact["spend"] or 0
                bucket["impressions"] += fact["impressions"] or 0
                bucket["clicks"] += fact["clicks"] or 0
                bucket["conversions"] += fact["conversions"] or 0
            dates = sorted(by_date)[-days:]
            series = [{"date": dt, "spend": round(by_date[dt]["spend"], 2), "impressions": int(by_date[dt]["impressions"]), "clicks": int(by_date[dt]["clicks"]), "conversions": int(by_date[dt]["conversions"])} for dt in dates]
            live_campaigns += 1
        else:
            # Simulated fallback when no feed has been ingested for this campaign.
            source = "simulated"
            camp_lines = lines_by_campaign.get(camp["id"], [])
            daily_budget = budget / max(days, 1)
            rng = random.Random(hash(camp["id"]) & 0xFFFFFFFF)
            avg_cpm = sum(l["max_bid_cpm"] for l in camp_lines) / max(len(camp_lines), 1) if camp_lines else 12
            series = []
            for d in range(days):
                day_spend = round(daily_budget * rng.uniform(0.7, 1.15), 2)
                day_imps = int(day_spend / max(avg_cpm, 1) * 1000)
                day_clicks = int(day_imps * rng.uniform(0.0009, 0.0028))
                day_convs = int(day_clicks * rng.uniform(0.012, 0.05))
                series.append({"date": (datetime.now(timezone.utc) - timedelta(days=days - d - 1)).date().isoformat(), "spend": day_spend, "impressions": day_imps, "clicks": day_clicks, "conversions": day_convs})
        imps = sum(s["impressions"] for s in series)
        clicks = sum(s["clicks"] for s in series)
        convs = sum(s["conversions"] for s in series)
        spend = round(sum(s["spend"] for s in series), 2)
        pacing = round(spend / budget, 4) if budget else 0
        report.append({
            "campaign_id": camp["id"], "name": camp["name"], "brand": camp["brand"], "status": camp["status"],
            "budget": budget, "spend": spend, "pacing": pacing, "source": source,
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
    return {"days": days, "source": "live" if live_campaigns else "simulated", "live_campaigns": live_campaigns, "portfolio": portfolio, "campaigns": report}


# ---------------------------------------------------------------------------
# Connectors / live feeds (GA4, SSP delivery, Crossix measurement, identity)
# ---------------------------------------------------------------------------
@app.get("/api/full/connectors")
def list_connectors(user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        rows = dicts(db.execute("SELECT * FROM connectors ORDER BY name").fetchall())
        counts = {dict(r)["connector_id"]: dict(r)["n"] for r in db.execute("SELECT connector_id, COUNT(*) AS n FROM delivery_facts GROUP BY connector_id").fetchall()}
    for row in rows:
        row["fact_count"] = counts.get(row["id"], 0)
    return rows


@app.post("/api/full/connectors/{connector_id}/sync")
def sync_connector(connector_id: str, days: int = Query(14, ge=1, le=90), user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    """Pull (here: generate) delivery facts from a source into delivery_facts."""
    with conn() as db:
        crow = db.execute("SELECT * FROM connectors WHERE id=?", (connector_id,)).fetchone()
        if not crow:
            raise HTTPException(404, "Connector not found")
        crow = dict(crow)
        campaigns = dicts(db.execute("SELECT * FROM campaigns").fetchall())
        lines = dicts(db.execute("SELECT * FROM line_items").fetchall())
    lines_by_campaign: Dict[str, List[Dict[str, Any]]] = {}
    for line in lines:
        lines_by_campaign.setdefault(line["campaign_id"], []).append(line)
    rng = random.Random(hash(connector_id) & 0xFFFFFFFF)
    ts = now_iso()
    inserted = 0
    with conn() as db:
        db.execute("DELETE FROM delivery_facts WHERE connector_id=?", (connector_id,))
        for camp in campaigns:
            camp_lines = lines_by_campaign.get(camp["id"], [])
            channel = camp_lines[0]["channel"] if camp_lines else "Display"
            avg_cpm = sum(l["max_bid_cpm"] for l in camp_lines) / max(len(camp_lines), 1) if camp_lines else 12
            daily_budget = camp["budget"] / max(days, 1)
            for d in range(days):
                date = (datetime.now(timezone.utc) - timedelta(days=days - d - 1)).date().isoformat()
                day_spend = round(daily_budget * rng.uniform(0.7, 1.15), 2)
                day_imps = int(day_spend / max(avg_cpm, 1) * 1000)
                day_clicks = int(day_imps * rng.uniform(0.0009, 0.0028))
                day_convs = int(day_clicks * rng.uniform(0.012, 0.05))
                if crow["kind"] == "ga4":          # engagement only, no media spend
                    vals = (day_imps, day_clicks, day_convs, 0.0)
                elif crow["kind"] == "crossix":    # conversions / Rx outcomes only
                    vals = (0, 0, day_convs, 0.0)
                else:                               # ssp / identity: full delivery
                    vals = (day_imps, day_clicks, day_convs, day_spend)
                db.execute("INSERT INTO delivery_facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), connector_id, crow["kind"], date, camp["id"], crow["name"], channel, vals[0], vals[1], vals[2], vals[3], ts))
                inserted += 1
        db.execute("UPDATE connectors SET status=?, last_sync=? WHERE id=?", ("connected", ts, connector_id))
        db.commit()
    audit(user["email"], "connector_sync", "connector", connector_id, {"facts": inserted, "days": days})
    return {"connector_id": connector_id, "kind": crow["kind"], "facts_ingested": inserted, "status": "connected", "last_sync": ts}


@app.post("/api/full/connectors/ingest")
def ingest_facts(payload: IngestRequest, user: Dict[str, Any] = Depends(roles("admin", "trader"))) -> Dict[str, Any]:
    """Ingest real delivery/measurement rows from an external feed."""
    ts = now_iso()
    inserted = 0
    with conn() as db:
        crow = db.execute("SELECT * FROM connectors WHERE kind=? ORDER BY created_at LIMIT 1", (payload.kind,)).fetchone()
        connector_id = dict(crow)["id"] if crow else str(uuid4())
        if not crow:
            db.execute("INSERT INTO connectors VALUES (?, ?, ?, ?, ?, ?, ?)", (connector_id, f"{payload.kind} feed", payload.kind, "connected", "{}", ts, ts))
        for r in payload.rows:
            db.execute("INSERT INTO delivery_facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid4()), connector_id, payload.kind, r.fact_date, r.campaign_id, r.partner, r.channel, r.impressions, r.clicks, r.conversions, r.spend, ts))
            inserted += 1
        db.execute("UPDATE connectors SET status=?, last_sync=? WHERE id=?", ("connected", ts, connector_id))
        db.commit()
    audit(user["email"], "connector_ingest", "connector", connector_id, {"kind": payload.kind, "facts": inserted})
    return {"connector_id": connector_id, "kind": payload.kind, "facts_ingested": inserted}


@app.get("/api/full/connectors/facts")
def connector_facts(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        rows = dicts(db.execute("SELECT source, COUNT(*) AS n, COALESCE(SUM(impressions),0) AS impressions, COALESCE(SUM(clicks),0) AS clicks, COALESCE(SUM(conversions),0) AS conversions, COALESCE(SUM(spend),0) AS spend FROM delivery_facts GROUP BY source ORDER BY source").fetchall())
    for r in rows:
        r["n"] = int(r["n"])
        r["impressions"] = int(r["impressions"])
        r["clicks"] = int(r["clicks"])
        r["conversions"] = int(r["conversions"])
        r["spend"] = round(float(r["spend"]), 2)
    return {"by_source": rows}


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
        results = dicts(db.execute("SELECT * FROM measurement_results").fetchall())
        connectors = dicts(db.execute("SELECT * FROM connectors").fetchall())
        fact_count = dict(db.execute("SELECT COUNT(*) AS n FROM delivery_facts").fetchone())["n"]
        rtb_win_count = dict(db.execute("SELECT COUNT(*) AS n FROM rtb_wins WHERE status IN ('won', 'billed')").fetchone())["n"]
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
            "measured_studies": len(results),
            "significant_studies": sum(1 for r in results if r["significant"]),
            "connectors": len(connectors),
            "connectors_live": sum(1 for c in connectors if c["status"] == "connected"),
            "live_delivery_facts": int(fact_count),
            "rtb_wins": int(rtb_win_count),
            "avg_working_media_ratio": avg_working_media,
        },
        "storage_backend": STORAGE_BACKEND,
        "narrative": "Pharma Signal connects verified audience reach, MLR-gated creative, quality supply paths, and measurement power into one operating view — answering whether a media buy reached the right verified audience, through the right path, at the right cost, with enough power to prove business impact.",
    }


@app.get("/api/full/insights")
def insights(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    """AI-style recommendations synthesized from current platform state."""
    with conn() as db:
        campaigns = dicts(db.execute("SELECT * FROM campaigns").fetchall())
        lines = dicts(db.execute("SELECT * FROM line_items").fetchall())
        supply = dicts(db.execute("SELECT * FROM supply_paths").fetchall())
        creatives = dicts(db.execute("SELECT * FROM creatives").fetchall())
        plans = dicts(db.execute("SELECT * FROM measurement_plans").fetchall())
        audiences = dicts(db.execute("SELECT * FROM audiences").fetchall())
        connectors = dicts(db.execute("SELECT * FROM connectors").fetchall())
        results = dicts(db.execute("SELECT * FROM measurement_results").fetchall())

    recs: List[Dict[str, Any]] = []

    def add(priority: str, category: str, title: str, detail: str, tab: str) -> None:
        recs.append({"priority": priority, "category": category, "title": title, "detail": detail, "tab": tab})

    plans_by_campaign = {p["campaign_id"] for p in plans}
    if not campaigns:
        add("high", "Setup", "Create your first campaign", "Start by building a campaign with line items, budgets, and flight dates.", "campaigns")
    else:
        for camp in campaigns:
            if camp["id"] not in plans_by_campaign:
                add("medium", "Measurement", f"Plan measurement for '{camp['name']}'", "No measurement plan exists — design a script-lift study so the buy can be proven.", "measurement")
                break

    # Supply path quality
    for sp in supply:
        if sp["status"] == "approved" and sp["fraud_risk"] and sp["fraud_risk"] > 1.0:
            add("high", "Supply", f"Elevated fraud risk on {sp['partner']}", f"{sp['partner']} is approved but shows {sp['fraud_risk']}% fraud risk — review or reduce spend.", "supply")
    low_working = [sp for sp in supply if sp["working_media_ratio"] < 0.6 and sp["status"] == "approved"]
    if low_working:
        add("medium", "Efficiency", "Working-media ratio is low on some paths", f"{len(low_working)} approved supply path(s) put under 60% of spend into working media — prioritize higher-efficiency paths.", "supply")

    # Frequency governance
    channel_caps: Dict[str, List[int]] = {}
    camp_by_id = {c["id"]: c for c in campaigns}
    for line in lines:
        channel_caps.setdefault(line["channel"], []).append(line["frequency_cap"])
    pressure = sum(round(sum(v) / len(v), 1) for v in channel_caps.values())
    if pressure > 8 and len(channel_caps) > 1:
        add("medium", "Frequency", "Coordinate frequency across channels", f"Combined cap pressure is {round(pressure, 1)} across {len(channel_caps)} channels — set a coordinated global weekly cap so HCPs aren't over-exposed.", "compliance")

    # Creatives / MLR
    pending = [c for c in creatives if c["mlr_status"] in {"in_review", "changes_requested"}]
    if pending:
        add("high", "Compliance", f"{len(pending)} creative(s) awaiting MLR", "Creatives can't serve until MLR-approved. Clear the review queue to unblock delivery.", "creative")
    no_isi = [c for c in creatives if not c["isi_included"]]
    if no_isi:
        add("high", "Compliance", "Creative missing ISI", f"{len(no_isi)} creative(s) lack Important Safety Information — required before serving.", "creative")

    # Connectors / live data
    synced = [c for c in connectors if c["status"] == "connected"]
    if connectors and not synced:
        add("low", "Data", "Connect a live feed", "No connector has synced yet — sync SSP/GA4/Crossix to replace simulated reporting with live data.", "connectors")

    # Measurement readiness + results
    underpowered = [p for p in plans if p["status"] == "underpowered"]
    if underpowered:
        add("medium", "Measurement", "Some studies are underpowered", f"{len(underpowered)} plan(s) won't detect the expected lift — increase exposed/control size or extend the flight.", "measurement")
    if plans and not results:
        add("low", "Measurement", "Close the loop with observed results", "You have study designs but no recorded outcomes — record exposed/control conversions to measure real lift.", "measurement")

    # Audience
    if len([a for a in audiences if a["audience_type"] == "HCP"]) and len(audiences) > 1:
        add("low", "Audience", "Resolve audience overlap", "Run identity resolution to dedupe overlapping reach into unique addressable reach before planning frequency.", "audiences")

    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: order.get(r["priority"], 3))
    counts = {"high": sum(1 for r in recs if r["priority"] == "high"), "medium": sum(1 for r in recs if r["priority"] == "medium"), "low": sum(1 for r in recs if r["priority"] == "low")}
    return {"recommendations": recs, "counts": counts, "generated_at": now_iso()}


@app.get("/api/full/alerts")
def alerts(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    """Threshold-breach monitoring: surfaces conditions that need attention now."""
    with conn() as db:
        lines = dicts(db.execute("SELECT id, name, frequency_cap FROM line_items").fetchall())
        ledger = dicts(db.execute("SELECT line_item_id, impressions FROM frequency_ledger").fetchall())
        creatives = dicts(db.execute("SELECT mlr_status FROM creatives").fetchall())
        supply = dicts(db.execute("SELECT * FROM supply_paths").fetchall())
        plans = dicts(db.execute("SELECT status FROM measurement_plans").fetchall())
        audiences = dicts(db.execute("SELECT name, contains_phi FROM audiences").fetchall())
    out: List[Dict[str, Any]] = []

    def add(severity: str, category: str, message: str, metric: str, value: Any) -> None:
        out.append({"severity": severity, "category": category, "message": message, "metric": metric, "value": value})

    cap_by_line = {l["id"]: l["frequency_cap"] for l in lines}
    name_by_line = {l["id"]: l["name"] for l in lines}
    over_by_line: Dict[str, int] = {}
    for r in ledger:
        cap = cap_by_line.get(r["line_item_id"])
        if cap is not None and int(r["impressions"]) > cap:
            over_by_line[r["line_item_id"]] = over_by_line.get(r["line_item_id"], 0) + 1
    for lid, n in over_by_line.items():
        add("warning", "frequency", f"{name_by_line.get(lid, 'Line item')}: {n} users over the frequency cap ({cap_by_line[lid]})", "over_cap_users", n)
    for a in audiences:
        if a["contains_phi"]:
            add("critical", "compliance", f"Audience '{a['name']}' is flagged as containing PHI", "contains_phi", 1)
    for sp in supply:
        if sp["status"] == "approved" and (sp["fraud_risk"] or 0) > 1.0:
            add("critical", "supply", f"{sp['partner']}: {sp['fraud_risk']}% fraud risk on an approved path", "fraud_risk", sp["fraud_risk"])
    blocked = sum(1 for c in creatives if c["mlr_status"] != "approved")
    if blocked:
        add("warning", "creative", f"{blocked} creative(s) not MLR-approved — cannot serve", "blocked_creatives", blocked)
    under = sum(1 for p in plans if p["status"] == "underpowered")
    if under:
        add("warning", "measurement", f"{under} measurement plan(s) underpowered", "underpowered_plans", under)
    if supply:
        awm = sum(s["working_media_ratio"] for s in supply) / len(supply)
        if awm < 0.6:
            add("info", "efficiency", f"Average working media {round(awm * 100)}% is below the 60% target", "avg_working_media", round(awm, 3))
    order = {"critical": 0, "warning": 1, "info": 2}
    out.sort(key=lambda a: order.get(a["severity"], 3))
    counts = {s: sum(1 for a in out if a["severity"] == s) for s in ["critical", "warning", "info"]}
    return {"alerts": out, "counts": counts, "total": len(out), "generated_at": now_iso()}


@app.get("/api/full/audit")
def list_audit(limit: int = Query(100, ge=1, le=500), user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM audit_events ORDER BY ts DESC LIMIT ?", (limit,)).fetchall())
