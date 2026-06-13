"""Pharma Signal Full DSP Server.

Functional local DSP backend with SQLite persistence: login, campaign build,
line items, bid factors, bulk edit, auction evaluation, and audit logging.

Run: uvicorn full_dsp_server:app --reload --port 8090
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = Path(os.environ.get("FULL_DSP_DB", Path(__file__).with_name("pharma_signal_dsp.db")))
SESSIONS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="Pharma Signal Full DSP", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


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


def init_db() -> None:
    with conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT, name TEXT, role TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, name TEXT, brand TEXT, indication TEXT, audience_type TEXT, objective TEXT, budget REAL, flight_start TEXT, flight_end TEXT, status TEXT, created_by TEXT, created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS line_items (id TEXT PRIMARY KEY, campaign_id TEXT, name TEXT, channel TEXT, budget REAL, max_bid_cpm REAL, pacing_mode TEXT, status TEXT, frequency_cap INTEGER, created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS bid_factors (line_item_id TEXT PRIMARY KEY, audience_quality_weight REAL, supply_quality_weight REAL, outcome_signal_weight REAL, contextual_relevance_weight REAL, working_media_weight REAL, frequency_penalty_weight REAL, bid_shading_pct REAL, max_bid_multiplier REAL, data_cost_guardrail REAL, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS supply_paths (id TEXT PRIMARY KEY, partner TEXT, channel TEXT, deal_id TEXT, seller_type TEXT, bid_floor_cpm REAL, viewability REAL, fraud_risk REAL, match_rate REAL, working_media_ratio REAL, outcome_score REAL, status TEXT);
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
        db.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


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


@app.post("/api/full/auction/evaluate")
def evaluate_auction(payload: AuctionEvaluateRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    with conn() as db:
        line = db.execute("SELECT * FROM line_items WHERE id=?", (payload.line_item_id,)).fetchone()
        factors = db.execute("SELECT * FROM bid_factors WHERE line_item_id=?", (payload.line_item_id,)).fetchone()
        supply = db.execute("SELECT * FROM supply_paths WHERE id=?", (payload.supply_path_id,)).fetchone()
    if not line or not factors or not supply:
        raise HTTPException(404, "Line item, bid factors, or supply path not found")
    guardrails = []
    if payload.contains_phi: guardrails.append("Blocked: PHI-like payload cannot enter bidder")
    if not payload.creative_approved: guardrails.append("Blocked: creative is not MLR approved")
    if not payload.geo_allowed: guardrails.append("Blocked: geo is outside approved activation footprint")
    if not payload.consent_ok: guardrails.append("Blocked: consent signal missing")
    if payload.data_cost_ratio > factors["data_cost_guardrail"]: guardrails.append("Throttle: data cost exceeds guardrail")
    if payload.frequency_seen_today >= line["frequency_cap"]: guardrails.append("Throttle: frequency cap pressure")
    if supply["status"] != "approved": guardrails.append("Blocked: supply path not approved")
    hard_block = any(g.startswith("Blocked") for g in guardrails)
    weighted_score = payload.audience_quality * factors["audience_quality_weight"] + payload.supply_quality * factors["supply_quality_weight"] + payload.outcome_signal * factors["outcome_signal_weight"] + payload.contextual_relevance * factors["contextual_relevance_weight"] + payload.working_media_ratio * 100 * factors["working_media_weight"] - min(payload.frequency_seen_today / max(line["frequency_cap"], 1), 1) * 100 * factors["frequency_penalty_weight"]
    multiplier = min(factors["max_bid_multiplier"], max(0.1, weighted_score / 60))
    shaded_bid = round(line["max_bid_cpm"] * multiplier * (1 - factors["bid_shading_pct"]), 2)
    decision = "blocked" if hard_block else "no_bid" if shaded_bid < payload.floor_cpm else "throttle" if guardrails else "bid"
    clearing = None if decision in {"blocked", "no_bid"} else round(min(shaded_bid, max(payload.floor_cpm, shaded_bid * 0.88)), 2)
    result = {"decision": decision, "bid_cpm": 0 if clearing is None else shaded_bid, "clearing_price_cpm": clearing, "confidence": round(max(0, min(100, weighted_score))), "reasons": [f"Weighted score {round(weighted_score, 1)}/100", f"Audience quality {payload.audience_quality}/100", f"Supply quality {payload.supply_quality}/100", f"Outcome signal {payload.outcome_signal}/100", f"Bid shading {round(factors['bid_shading_pct'] * 100)}%"], "guardrails": guardrails or ["No PHI accepted", "Creative approved", "Supply path approved"]}
    audit(user["email"], "auction_evaluate", "line_item", payload.line_item_id, result)
    return result


@app.get("/api/full/audit")
def list_audit(limit: int = Query(100, ge=1, le=500), user: Dict[str, Any] = Depends(current_user)) -> List[Dict[str, Any]]:
    with conn() as db:
        return dicts(db.execute("SELECT * FROM audit_events ORDER BY ts DESC LIMIT ?", (limit,)).fetchall())
