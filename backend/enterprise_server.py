"""Enterprise Pharma Signal DSP API.

This is the CEO-level full-stack backend layer for Pharma Signal. It is intentionally
separate from server.py so the existing Emergent backend remains intact while this
module defines a production-oriented enterprise API surface:

- Multi-tenant orgs and brands
- Campaign, line item, creative, audience, and supply activation state
- OpenRTB auction evaluation
- Portfolio optimizer
- Measurement readiness
- Approval workflow
- Audit log
- Executive operating dashboard

Run locally:
    uvicorn enterprise_server:app --reload --port 8080
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from math import sqrt
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =============================
# Domain model
# =============================

class Role(str, Enum):
    CEO = "ceo"
    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    COMPLIANCE = "compliance"
    CLIENT = "client"
    VENDOR = "vendor"


class EntityStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"


class Decision(str, Enum):
    BID = "bid"
    THROTTLE = "throttle"
    NO_BID = "no_bid"
    BLOCKED = "blocked"


class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    region: str = "US"
    vertical: str = "Pharma"
    compliance_profile: str = "HIPAA-aware, no-PHI storage, MLR approval required"
    created_at: str = Field(default_factory=lambda: now_iso())


class Brand(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str
    name: str
    indication: str
    audience_partition: str
    mrl_owner: str = "brand-mlr@pharmasignal.local"
    status: EntityStatus = EntityStatus.ACTIVE


class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str
    brand_id: str
    name: str
    objective: str
    audience_type: str
    budget: float
    spent: float = 0
    start_date: str
    end_date: str
    base_cpm: float
    target_frequency_weekly: int
    max_frequency_daily: int
    outcome_kpi: str
    status: EntityStatus = EntityStatus.DRAFT
    risk_notes: List[str] = Field(default_factory=list)


class LineItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    name: str
    channel: str
    budget: float
    bid_strategy: str
    max_bid_cpm: float
    pacing_mode: str = "even"
    status: EntityStatus = EntityStatus.DRAFT


class Audience(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str
    name: str
    type: str
    source: str
    estimated_size: int
    match_rate: float
    data_cpm: float
    quality_score: float
    privacy_posture: str
    activation_allowed: bool = True


class SupplyPath(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    partner: str
    channel: str
    deal_id: str
    seller_type: str
    bid_floor_cpm: float
    viewability: float
    fraud_risk: float
    match_rate: float
    working_media_ratio: float
    outcome_score: float
    status: EntityStatus = EntityStatus.REVIEW


class Creative(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    campaign_id: str
    name: str
    format: str
    claim_summary: str
    fair_balance: bool
    mlr_status: EntityStatus = EntityStatus.REVIEW


class AuctionRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    org_id: str
    campaign_id: str
    line_item_id: str
    audience_id: str
    supply_path_id: str
    creative_id: str
    floor_cpm: float
    audience_match: float = Field(ge=0, le=100)
    contextual_relevance: float = Field(ge=0, le=100)
    outcome_signal: float = Field(ge=0, le=100)
    frequency_seen_today: int = Field(ge=0)
    contains_phi: bool = False
    geo_allowed: bool = True
    consent_ok: bool = True


class AuctionResponse(BaseModel):
    request_id: str
    decision: Decision
    bid_cpm: float
    clearing_price_cpm: Optional[float]
    confidence: int
    creative_id: Optional[str]
    deal_id: Optional[str]
    reasons: List[str]
    guardrails: List[str]
    event_log: List[str]


class MeasurementPlan(BaseModel):
    campaign_id: str
    expected_conversions: int
    exposed_sample: int
    control_sample: int
    minimum_detectable_lift: float
    power_score: int
    recommendation: str


class ApprovalRequest(BaseModel):
    entity_type: str
    entity_id: str
    action: str
    requested_by: str
    risk_level: str
    notes: str = ""


class ApprovalDecision(BaseModel):
    approval_id: str
    decision: str
    decided_by: str
    notes: str = ""


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: str = Field(default_factory=lambda: now_iso())
    actor: str
    role: Role
    action: str
    entity_type: str
    entity_id: str
    risk_level: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutiveDashboard(BaseModel):
    total_budget: float
    total_spent: float
    working_media_ratio: float
    active_campaigns: int
    approved_supply_paths: int
    measurement_ready_campaigns: int
    compliance_blocks: int
    avg_outcome_supply_score: float
    ceo_summary: str
    next_board_questions: List[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================
# In-memory enterprise store
# Replace with Postgres repositories in production.
# =============================

org = Organization(name="Pharma Signal Demo Holding Company")
brand_tzield = Brand(org_id=org.id, name="TZIELD", indication="Type 1 diabetes delay", audience_partition="DTC education + HCP specialist")
brand_ms = Brand(org_id=org.id, name="MS Portfolio", indication="Multiple sclerosis", audience_partition="HCP neurology + DTC support")

campaigns: Dict[str, Campaign] = {}
line_items: Dict[str, LineItem] = {}
audiences: Dict[str, Audience] = {}
supply_paths: Dict[str, SupplyPath] = {}
creatives: Dict[str, Creative] = {}
approvals: Dict[str, Dict[str, Any]] = {}
audit_log: List[AuditEvent] = []


def seed_enterprise_store() -> None:
    if campaigns:
        return

    c1 = Campaign(
        org_id=org.id,
        brand_id=brand_tzield.id,
        name="TZIELD DTC Outcomes Flight",
        objective="Quality reach, site engagement, and new patient start proxy",
        audience_type="DTC",
        budget=1_710_000,
        spent=684_000,
        start_date="2026-01-15",
        end_date="2026-12-31",
        base_cpm=18,
        target_frequency_weekly=8,
        max_frequency_daily=2,
        outcome_kpi="New patient starts / qualified conversion proxy",
        status=EntityStatus.ACTIVE,
        risk_notes=["No sensitive condition inference", "Aggregated reporting only"],
    )
    c2 = Campaign(
        org_id=org.id,
        brand_id=brand_ms.id,
        name="MS HCP Neurology Precision Flight",
        objective="Verified neurologist reach and NPI engagement depth",
        audience_type="HCP",
        budget=645_000,
        spent=214_000,
        start_date="2026-02-01",
        end_date="2026-09-30",
        base_cpm=42,
        target_frequency_weekly=6,
        max_frequency_daily=3,
        outcome_kpi="Qualified NPI engagement",
        status=EntityStatus.ACTIVE,
        risk_notes=["Protect NPI exports", "Separate HCP and DTC reporting"],
    )
    for c in [c1, c2]:
        campaigns[c.id] = c

    li1 = LineItem(campaign_id=c1.id, name="DTC display + contextual", channel="Display", budget=910_000, bid_strategy="outcome_weighted", max_bid_cpm=28, status=EntityStatus.ACTIVE)
    li2 = LineItem(campaign_id=c2.id, name="HCP endemic + PMP", channel="Display", budget=420_000, bid_strategy="verified_hcp_precision", max_bid_cpm=64, status=EntityStatus.ACTIVE)
    for li in [li1, li2]:
        line_items[li.id] = li

    a1 = Audience(org_id=org.id, name="Predictive T1D risk education", type="DTC", source="Modeled audience", estimated_size=2_400_000, match_rate=52, data_cpm=11, quality_score=82, privacy_posture="Modeled and aggregated; no PHI stored")
    a2 = Audience(org_id=org.id, name="Verified neurologists ICD-10 G35", type="HCP", source="NPI CRM seed", estimated_size=4_021, match_rate=73, data_cpm=18, quality_score=94, privacy_posture="Professional identity only; role-limited reporting")
    for a in [a1, a2]:
        audiences[a.id] = a

    s1 = SupplyPath(name="PubMatic curated health mobile", partner="PubMatic", channel="Display", deal_id="PM-PHARMA-HCP-001", seller_type="Direct", bid_floor_cpm=6.8, viewability=69, fraud_risk=1.1, match_rate=71, working_media_ratio=0.54, outcome_score=82, status=EntityStatus.APPROVED)
    s2 = SupplyPath(name="OpenX health web", partner="OpenX", channel="Display", deal_id="OX-HEALTH-WEB-117", seller_type="SPO verified", bid_floor_cpm=7.4, viewability=72, fraud_risk=1.4, match_rate=68, working_media_ratio=0.62, outcome_score=79, status=EntityStatus.REVIEW)
    for s in [s1, s2]:
        supply_paths[s.id] = s

    cr1 = Creative(campaign_id=c1.id, name="TZIELD education 300x250", format="300x250", claim_summary="Education-safe type 1 diabetes delay message", fair_balance=True, mlr_status=EntityStatus.APPROVED)
    cr2 = Creative(campaign_id=c2.id, name="MS HCP neuro clinical card", format="300x600", claim_summary="HCP-only clinical education card", fair_balance=True, mlr_status=EntityStatus.APPROVED)
    for cr in [cr1, cr2]:
        creatives[cr.id] = cr


seed_enterprise_store()


# =============================
# Security and RBAC
# =============================

ROLE_PERMISSIONS = {
    Role.CEO: {"read", "approve", "activate", "optimize", "audit"},
    Role.ADMIN: {"read", "write", "approve", "activate", "optimize", "audit"},
    Role.TRADER: {"read", "write", "activate", "optimize"},
    Role.ANALYST: {"read", "optimize"},
    Role.COMPLIANCE: {"read", "approve", "audit"},
    Role.CLIENT: {"read"},
    Role.VENDOR: {"read"},
}


def current_role(x_pharma_role: str = Header(default="ceo")) -> Role:
    try:
        return Role(x_pharma_role.lower())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Unknown role") from exc


def require_permission(permission: str):
    def dependency(role: Role = Depends(current_role)) -> Role:
        if permission not in ROLE_PERMISSIONS[role]:
            raise HTTPException(status_code=403, detail=f"Role {role.value} lacks {permission} permission")
        return role
    return dependency


def log_event(role: Role, action: str, entity_type: str, entity_id: str, risk_level: str = "low", metadata: Optional[Dict[str, Any]] = None) -> None:
    audit_log.append(
        AuditEvent(
            actor=f"{role.value}@pharmasignal.local",
            role=role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            risk_level=risk_level,
            metadata=metadata or {},
        )
    )


# =============================
# Decisioning services
# =============================

def clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def supply_score(path: SupplyPath) -> int:
    score = (
        path.outcome_score * 0.32
        + path.viewability * 0.18
        + path.match_rate * 0.18
        + path.working_media_ratio * 100 * 0.22
        + (100 - path.fraud_risk * 10) * 0.10
    )
    return round(clamp(score, 0, 100))


def measure_campaign(campaign: Campaign) -> MeasurementPlan:
    expected_conversions = round(campaign.budget / max(120 if campaign.audience_type == "DTC" else 190, 1))
    exposed_sample = round((campaign.budget / max(campaign.base_cpm, 1)) * 1000 * 0.72)
    control_sample = round(exposed_sample * 0.22)
    depth_score = clamp(expected_conversions / 3500, 0.2, 1.1)
    balance_score = clamp(control_sample / max(exposed_sample * 0.2, 1), 0.4, 1.1)
    spend_signal = clamp(campaign.spent / max(campaign.budget * 0.25, 1), 0.25, 1.2)
    power_score = round(clamp((depth_score * 0.44 + balance_score * 0.26 + spend_signal * 0.30) * 100, 0, 98))
    minimum_detectable_lift = round(clamp(0.30 - power_score / 500, 0.04, 0.24), 2)
    recommendation = (
        "Board-ready measurement plan. Keep exposure/control methodology stable."
        if power_score >= 75
        else "Promising but not board-ready. Increase conversion depth or tighten control design."
        if power_score >= 55
        else "Underpowered. Treat as directional learning or increase budget/time."
    )
    return MeasurementPlan(
        campaign_id=campaign.id,
        expected_conversions=expected_conversions,
        exposed_sample=exposed_sample,
        control_sample=control_sample,
        minimum_detectable_lift=minimum_detectable_lift,
        power_score=power_score,
        recommendation=recommendation,
    )


def evaluate_auction(req: AuctionRequest) -> AuctionResponse:
    campaign = campaigns.get(req.campaign_id)
    line_item = line_items.get(req.line_item_id)
    audience = audiences.get(req.audience_id)
    supply = supply_paths.get(req.supply_path_id)
    creative = creatives.get(req.creative_id)

    if not all([campaign, line_item, audience, supply, creative]):
        return AuctionResponse(
            request_id=req.request_id,
            decision=Decision.NO_BID,
            bid_cpm=0,
            clearing_price_cpm=None,
            confidence=0,
            creative_id=None,
            deal_id=None,
            reasons=["Unknown campaign, line item, audience, supply path, or creative."],
            guardrails=["Entity validation failed."],
            event_log=["auction.received", "auction.no_bid.entity_validation"],
        )

    guardrails = []
    if req.contains_phi:
        guardrails.append("PHI-like payload blocked before bid decision.")
    if not req.geo_allowed:
        guardrails.append("Geo not approved for activation.")
    if not req.consent_ok:
        guardrails.append("Consent signal missing or invalid.")
    if audience.type != campaign.audience_type and campaign.audience_type != "Hybrid":
        guardrails.append("Audience partition mismatch.")
    if creative.mlr_status != EntityStatus.APPROVED:
        guardrails.append("Creative is not MLR approved.")
    if supply.status not in {EntityStatus.APPROVED, EntityStatus.ACTIVE}:
        guardrails.append("Supply path not approved for automated activation.")
    if req.frequency_seen_today >= campaign.max_frequency_daily:
        guardrails.append("Frequency cap pressure detected.")

    if any(g for g in guardrails if "blocked" in g.lower() or "not approved" in g.lower() or "mismatch" in g.lower()):
        return AuctionResponse(
            request_id=req.request_id,
            decision=Decision.BLOCKED,
            bid_cpm=0,
            clearing_price_cpm=None,
            confidence=0,
            creative_id=None,
            deal_id=supply.deal_id,
            reasons=["Compliance or approval guardrail prevented bidding."],
            guardrails=guardrails,
            event_log=["auction.received", "compliance.evaluated", "auction.blocked"],
        )

    supply_quality = supply_score(supply)
    audience_quality = audience.quality_score
    working_media = supply.working_media_ratio
    frequency_penalty = 0.62 if req.frequency_seen_today >= campaign.max_frequency_daily else 1
    bid_multiplier = clamp(
        (0.62 + req.audience_match / 100)
        * (0.70 + supply_quality / 130)
        * (0.74 + req.outcome_signal / 150)
        * (0.80 + req.contextual_relevance / 220)
        * (0.70 + working_media / 2)
        * frequency_penalty,
        0.20,
        2.85,
    )
    bid_cpm = round(min(line_item.max_bid_cpm, campaign.base_cpm * bid_multiplier), 2)
    confidence = round(req.audience_match * 0.26 + req.outcome_signal * 0.22 + req.contextual_relevance * 0.16 + supply_quality * 0.24 + audience_quality * 0.12)
    decision = Decision.NO_BID if bid_cpm < req.floor_cpm or confidence < 58 else Decision.THROTTLE if guardrails else Decision.BID
    clearing = round(min(bid_cpm, max(req.floor_cpm, bid_cpm * 0.86)), 2) if decision in {Decision.BID, Decision.THROTTLE} else None

    return AuctionResponse(
        request_id=req.request_id,
        decision=decision,
        bid_cpm=bid_cpm if clearing else 0,
        clearing_price_cpm=clearing,
        confidence=confidence,
        creative_id=creative.id if clearing else None,
        deal_id=supply.deal_id,
        reasons=[
            f"Supply score {supply_quality}/100",
            f"Audience quality {round(audience_quality)}/100",
            f"Working media ratio {round(working_media * 100)}%",
            f"Outcome signal {round(req.outcome_signal)}/100",
        ],
        guardrails=guardrails or ["No PHI accepted", "Audience partition valid", "Creative approved"],
        event_log=["auction.received", "compliance.evaluated", "bid.price_calculated", f"auction.{decision.value}", "event_stream.queued"],
    )


# =============================
# App and routes
# =============================

app = FastAPI(title="Pharma Signal Enterprise DSP", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "pharma-signal-enterprise-dsp",
        "version": "2.0.0",
        "modules": ["control_plane", "auction_gateway", "optimizer", "measurement", "approvals", "audit"],
    }


@app.get("/api/v2/executive-dashboard", response_model=ExecutiveDashboard)
def executive_dashboard(role: Role = Depends(require_permission("read"))) -> ExecutiveDashboard:
    total_budget = sum(c.budget for c in campaigns.values())
    total_spent = sum(c.spent for c in campaigns.values())
    approved_paths = [p for p in supply_paths.values() if p.status in {EntityStatus.APPROVED, EntityStatus.ACTIVE}]
    measurement_ready = sum(1 for c in campaigns.values() if measure_campaign(c).power_score >= 70)
    compliance_blocks = sum(1 for e in audit_log if e.risk_level in {"high", "critical"})
    avg_supply = round(sum(supply_score(p) for p in supply_paths.values()) / max(len(supply_paths), 1), 1)
    working_media = round(sum(p.working_media_ratio for p in supply_paths.values()) / max(len(supply_paths), 1), 3)

    return ExecutiveDashboard(
        total_budget=total_budget,
        total_spent=total_spent,
        working_media_ratio=working_media,
        active_campaigns=sum(1 for c in campaigns.values() if c.status == EntityStatus.ACTIVE),
        approved_supply_paths=len(approved_paths),
        measurement_ready_campaigns=measurement_ready,
        compliance_blocks=compliance_blocks,
        avg_outcome_supply_score=avg_supply,
        ceo_summary=(
            "Enterprise DSP foundation is live: campaign control plane, supply scoring, OpenRTB-style auctioning, "
            "measurement readiness, approvals, and auditability are represented in code. The next CEO decision is "
            "whether to prioritize bidder latency, data ingestion, or commercial partner integrations."
        ),
        next_board_questions=[
            "Which supply paths are truly incremental after data and platform costs?",
            "Which campaigns can prove lift versus directional performance only?",
            "What guardrails block scale and who owns removing them?",
            "How quickly can the bidder move from simulation to low-latency production?",
        ],
    )


@app.get("/api/v2/campaigns", response_model=List[Campaign])
def list_campaigns(status: Optional[EntityStatus] = None, role: Role = Depends(require_permission("read"))) -> List[Campaign]:
    rows = list(campaigns.values())
    return [c for c in rows if status is None or c.status == status]


@app.post("/api/v2/campaigns", response_model=Campaign)
def create_campaign(payload: Campaign, role: Role = Depends(require_permission("write"))) -> Campaign:
    campaigns[payload.id] = payload
    log_event(role, "created_campaign", "campaign", payload.id, "medium", {"budget": payload.budget})
    return payload


@app.get("/api/v2/supply-paths", response_model=List[SupplyPath])
def list_supply_paths(status: Optional[EntityStatus] = None, role: Role = Depends(require_permission("read"))) -> List[SupplyPath]:
    rows = list(supply_paths.values())
    return [p for p in rows if status is None or p.status == status]


@app.post("/api/v2/auction/evaluate", response_model=AuctionResponse)
def auction_endpoint(payload: AuctionRequest, role: Role = Depends(require_permission("activate"))) -> AuctionResponse:
    result = evaluate_auction(payload)
    risk = "high" if result.decision in {Decision.BLOCKED, Decision.NO_BID} else "medium" if result.decision == Decision.THROTTLE else "low"
    log_event(role, f"auction_{result.decision.value}", "auction_request", payload.request_id, risk, result.model_dump())
    return result


@app.get("/api/v2/optimizer/portfolio")
def portfolio_optimizer(role: Role = Depends(require_permission("optimize"))) -> Dict[str, Any]:
    recommendations = []
    for c in campaigns.values():
        measurement = measure_campaign(c)
        pacing = c.spent / max(c.budget, 1)
        readiness = measurement.power_score / 100
        priority = 1.12 if c.status == EntityStatus.ACTIVE else 0.92
        multiplier = clamp(0.82 + readiness * 0.24 + (0.45 - pacing) * 0.18 + priority * 0.08, 0.72, 1.22)
        rec_budget = round(c.budget * multiplier / 1000) * 1000
        delta = rec_budget - c.budget
        status = "increase" if delta > c.budget * 0.05 else "decrease" if delta < -c.budget * 0.05 else "hold"
        recommendations.append({
            "campaign_id": c.id,
            "campaign_name": c.name,
            "current_budget": c.budget,
            "recommended_budget": rec_budget,
            "delta": delta,
            "status": status,
            "power_score": measurement.power_score,
            "rationale": "Optimize toward measurement-ready, outcome-proven campaigns while protecting compliance and pacing.",
        })
    return {
        "current_budget": sum(c.budget for c in campaigns.values()),
        "recommended_budget": sum(r["recommended_budget"] for r in recommendations),
        "recommendations": recommendations,
    }


@app.get("/api/v2/measurement/plans", response_model=List[MeasurementPlan])
def measurement_plans(role: Role = Depends(require_permission("read"))) -> List[MeasurementPlan]:
    return [measure_campaign(c) for c in campaigns.values()]


@app.post("/api/v2/approvals")
def request_approval(payload: ApprovalRequest, role: Role = Depends(require_permission("write"))) -> Dict[str, Any]:
    approval_id = str(uuid4())
    approval = payload.model_dump()
    approval.update({"id": approval_id, "status": "pending", "created_at": now_iso()})
    approvals[approval_id] = approval
    log_event(role, "requested_approval", payload.entity_type, payload.entity_id, payload.risk_level, approval)
    return approval


@app.post("/api/v2/approvals/decision")
def decide_approval(payload: ApprovalDecision, role: Role = Depends(require_permission("approve"))) -> Dict[str, Any]:
    approval = approvals.get(payload.approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval.update({
        "status": payload.decision,
        "decided_by": payload.decided_by,
        "decision_notes": payload.notes,
        "decided_at": now_iso(),
    })
    log_event(role, f"approval_{payload.decision}", approval["entity_type"], approval["entity_id"], approval["risk_level"], approval)
    return approval


@app.get("/api/v2/audit", response_model=List[AuditEvent])
def audit_events(limit: int = Query(50, ge=1, le=500), role: Role = Depends(require_permission("audit"))) -> List[AuditEvent]:
    return list(reversed(audit_log[-limit:]))


@app.get("/api/v2/board/narrative")
def board_narrative(role: Role = Depends(require_permission("read"))) -> Dict[str, Any]:
    dash = executive_dashboard(role)
    return {
        "headline": "Pharma Signal is evolving from dashboard to enterprise DSP operating system.",
        "what_is_real_now": [
            "Full-stack backend API surface for campaigns, supply, auctions, measurement, optimizer, approvals, and audit.",
            "OpenRTB-style auction engine with pharma-specific guardrails before bid pricing.",
            "Measurement planner that separates board-ready lift claims from directional learning.",
            "CEO dashboard that translates media mechanics into enterprise operating questions.",
        ],
        "numbers": dash.model_dump(),
        "next_90_days": [
            "Connect Mongo/Postgres persistence to the v2 enterprise API repositories.",
            "Replace simulated auction traffic with partner-specific SSP adapters.",
            "Add real GA4, SSP delivery, verification, and measurement imports.",
            "Stand up low-latency bidder service in Go/Rust while keeping FastAPI as control plane.",
        ],
    }
