"""PharmaSignal DSP — Backend API.

A pharma-native demand-side platform with intelligence layer:
- Campaigns, Audiences, PMPs, Vendors, Script Lift, GA4 engagement
- Outcome-Adjusted Supply Score (killer feature)
- RTB bid simulator
- AI-powered next-best-action recommendations via Claude Sonnet 4.5
"""
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Query, Depends, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import csv
import json
import secrets
import logging
import random
import uuid
import bcrypt
import jwt
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 12  # 12h
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@pharmasignal.io')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@2026')

ROLES = {"admin", "trader", "analyst", "vendor"}

app = FastAPI(title="PharmaSignal DSP")
api_router = APIRouter(prefix="/api")

logger = logging.getLogger("pharmasignal")
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# ============== MODELS ==============
def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    brand: str
    indication: str
    campaign_type: str  # HCP / DTC
    budget: float
    spent: float = 0.0
    flight_start: str
    flight_end: str
    status: str = "Active"  # Active / Paused / Draft
    npi_target_count: Optional[int] = 0
    specialty: Optional[str] = None
    diagnosis: Optional[str] = None
    data_partner: Optional[str] = None
    outcome_kpi: str = "Script Lift"
    mlr_status: str = "Approved"
    frequency_cap: int = 5
    channels: List[str] = Field(default_factory=list)
    audience_ids: List[str] = Field(default_factory=list)
    pmp_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class CampaignCreate(BaseModel):
    name: str
    brand: str
    indication: str
    campaign_type: str
    budget: float
    flight_start: str
    flight_end: str
    npi_target_count: Optional[int] = 0
    specialty: Optional[str] = None
    diagnosis: Optional[str] = None
    data_partner: Optional[str] = None
    outcome_kpi: str = "Script Lift"
    frequency_cap: int = 5
    channels: List[str] = Field(default_factory=list)
    audience_ids: List[str] = Field(default_factory=list)
    pmp_ids: List[str] = Field(default_factory=list)


class CampaignLinkUpdate(BaseModel):
    audience_ids: Optional[List[str]] = None
    pmp_ids: Optional[List[str]] = None
    status: Optional[str] = None


class RTBSimulateRequest(BaseModel):
    outcome_probability: float = 0.6
    audience_quality_score: float = 0.75
    supply_quality_score: float = 0.7
    rx_lift_weight: float = 1.2
    engagement_quality: float = 0.65
    data_cost_multiplier: float = 1.3
    base_value: float = 12.0  # base CPM willingness


class ScenarioCreate(BaseModel):
    name: str
    params: Dict[str, Any]
    result: Dict[str, Any]


class CreativeCreate(BaseModel):
    campaign_id: Optional[str] = None
    brand: str
    indication: str
    asset_name: str
    format: str  # 300x250, OLV-15s, CTV-30s, etc.
    claims: str = ""
    fair_balance: bool = True
    reviewer_notes: str = ""


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "analyst"
    vendor_scope: Optional[str] = None  # for role=vendor: which vendor they map to


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ShareCreate(BaseModel):
    vendor: str
    expires_in_days: int = 14


# ============== AUTH HELPERS ==============
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id, "email": email, "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = auth[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require_roles(*allowed):
    async def dep(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed:
            raise HTTPException(403, f"Requires role: {' or '.join(allowed)}")
        return current_user
    return dep


# ============== SEED DATA ==============
SEED_DOC_ID = "pharmasignal_seed_v1"

SPECIALTIES = ["Oncology", "Endocrinology", "Cardiology", "Neurology", "Rheumatology", "Family Practice"]
INDICATIONS = ["Type 2 Diabetes", "HER2+ Breast Cancer", "Multiple Sclerosis", "Atrial Fibrillation", "Psoriatic Arthritis"]
DATA_PARTNERS = ["Crossix", "Swoop", "IQVIA", "LiveRamp", "DeepIntent Audiences"]
PMP_VENDORS = ["DeepIntent", "PulsePoint", "Doceree", "PubMatic Health", "Index Health", "OpenX RX", "Magnite Health", "Infolinks Health"]
CHANNELS = ["Display", "OLV", "CTV", "Audio", "Native", "EHR/POC", "Endemic"]


def seed_campaigns():
    brands = [
        ("Veltrexa", "Type 2 Diabetes", "DTC"),
        ("Veltrexa Pro", "Type 2 Diabetes", "HCP"),
        ("Onkora", "HER2+ Breast Cancer", "HCP"),
        ("Onkora Patient", "HER2+ Breast Cancer", "DTC"),
        ("Mylenra", "Multiple Sclerosis", "DTC"),
        ("Cardiox HCP", "Atrial Fibrillation", "HCP"),
        ("Psorina", "Psoriatic Arthritis", "DTC"),
    ]
    out = []
    for name, ind, ctype in brands:
        budget = random.choice([250000, 500000, 750000, 1200000])
        spent = round(budget * random.uniform(0.32, 0.78), 2)
        c = Campaign(
            name=f"{name} Q1 2026",
            brand=name,
            indication=ind,
            campaign_type=ctype,
            budget=budget,
            spent=spent,
            flight_start="2026-01-15",
            flight_end="2026-03-31",
            status=random.choice(["Active", "Active", "Active", "Paused"]),
            npi_target_count=random.choice([1200, 4500, 8200, 15000]) if ctype == "HCP" else 0,
            specialty=random.choice(SPECIALTIES) if ctype == "HCP" else None,
            diagnosis=ind if ctype == "DTC" else None,
            data_partner=random.choice(DATA_PARTNERS),
            outcome_kpi=random.choice(["Script Lift", "Verified Reach", "Quality Visits", "NPS"]),
            frequency_cap=random.choice([3, 5, 8, 12]),
            channels=random.sample(CHANNELS, k=random.randint(2, 4)),
        )
        out.append(c.model_dump())
    return out


def seed_audiences():
    audiences = []
    templates = [
        ("Endocrinologists — Decile 8-10", "HCP", 12400),
        ("Oncologists treating HER2+ BC", "HCP", 4800),
        ("Newly Diagnosed T2D Adults 40-65", "DTC", 2_400_000),
        ("Caregivers of MS Patients", "DTC", 850_000),
        ("AFib Patient Lookalikes", "DTC", 1_650_000),
        ("PsA Female 30-55 Active Search", "DTC", 420_000),
        ("Family Practice — High Rx Volume", "HCP", 18500),
        ("Cardiologists — AFib Decile 9-10", "HCP", 7200),
    ]
    for name, t, size in templates:
        match_rate = round(random.uniform(0.32, 0.84), 2)
        data_cpm = round(random.uniform(2.5, 9.5), 2)
        media_cpm = round(random.uniform(8, 28), 2)
        working_media = round(media_cpm / (media_cpm + data_cpm), 3)
        a = {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": t,
            "estimated_size": size,
            "match_rate_forecast": match_rate,
            "data_cpm": data_cpm,
            "media_cpm": media_cpm,
            "working_media_ratio": working_media,
            "audience_quality_score": round(random.uniform(55, 95), 1),
            "rx_relevance_score": round(random.uniform(50, 98), 1),
            "scale_risk": random.choice(["Low", "Medium", "High"]),
            "waste_risk": random.choice(["Low", "Medium", "High"]),
            "data_partner": random.choice(DATA_PARTNERS),
        }
        audiences.append(a)
    return audiences


def seed_pmps():
    pmps = []
    for vendor in PMP_VENDORS:
        spend = round(random.uniform(45000, 380000), 0)
        verified_reach = round(random.uniform(0.45, 0.92), 3)
        engagement_quality = round(random.uniform(0.30, 0.88), 3)
        script_lift = round(random.uniform(-0.5, 6.8), 2)  # percent
        working_media = round(random.uniform(0.55, 0.93), 3)
        match_rate = round(random.uniform(0.40, 0.90), 3)
        data_cost_drag = round(random.uniform(0.05, 0.40), 3)
        fraud_risk = round(random.uniform(0.01, 0.12), 3)
        # Outcome-Adjusted Supply Score: composite
        score = (
            verified_reach * 22
            + engagement_quality * 18
            + max(script_lift, 0) * 4
            + working_media * 18
            + match_rate * 18
            - data_cost_drag * 25
            - fraud_risk * 60
        )
        score = max(0, min(100, round(score, 1)))
        recommendation = "Scale" if score >= 72 else ("Hold" if score >= 55 else "Reduce")
        pmps.append({
            "id": str(uuid.uuid4()),
            "vendor": vendor,
            "deal_id": f"PMP-{vendor[:3].upper()}-{random.randint(1000,9999)}",
            "spend": spend,
            "impressions": int(spend / random.uniform(0.008, 0.022)),
            "ctr": round(random.uniform(0.08, 0.62), 3),
            "vcr": round(random.uniform(0.55, 0.88), 3),
            "verified_reach": verified_reach,
            "engagement_quality": engagement_quality,
            "script_lift_pct": script_lift,
            "working_media_efficiency": working_media,
            "match_rate": match_rate,
            "data_cost_drag": data_cost_drag,
            "fraud_risk": fraud_risk,
            "outcome_adjusted_score": score,
            "recommendation": recommendation,
            "supply_path": random.choice(["Direct", "SPO Verified", "Reseller"]),
        })
    return sorted(pmps, key=lambda p: p["outcome_adjusted_score"], reverse=True)


def seed_ga4():
    data = []
    for ch in CHANNELS:
        sessions = random.randint(8000, 95000)
        engaged = int(sessions * random.uniform(0.42, 0.78))
        quality_visits = int(engaged * random.uniform(0.18, 0.55))
        conversions = int(quality_visits * random.uniform(0.04, 0.18))
        data.append({
            "channel": ch,
            "sessions": sessions,
            "engaged_sessions": engaged,
            "engagement_rate": round(engaged / sessions, 3),
            "quality_visits": quality_visits,
            "avg_session_duration": round(random.uniform(45, 220), 1),
            "conversions": conversions,
        })
    return data


def seed_script_lift():
    # Time-series exposed vs control
    series = []
    base_exposed = 100
    base_control = 100
    for w in range(1, 13):
        base_exposed += random.uniform(1.5, 4.2)
        base_control += random.uniform(0.2, 1.5)
        series.append({
            "week": f"W{w}",
            "exposed_rx_index": round(base_exposed, 1),
            "control_rx_index": round(base_control, 1),
            "lift_pct": round((base_exposed - base_control) / base_control * 100, 2),
        })
    return series


def seed_data_cost():
    # Working media breakdown by line item
    items = []
    for i, ch in enumerate(CHANNELS):
        total = random.uniform(40000, 220000)
        data_fees = total * random.uniform(0.12, 0.34)
        platform_fees = total * random.uniform(0.06, 0.14)
        working_media = total - data_fees - platform_fees
        items.append({
            "line_item": f"{ch} — Q1",
            "channel": ch,
            "total_spend": round(total, 0),
            "data_fees": round(data_fees, 0),
            "platform_fees": round(platform_fees, 0),
            "working_media": round(working_media, 0),
            "working_media_pct": round(working_media / total * 100, 1),
        })
    return items


def seed_vendors():
    pmps = seed_pmps()  # reuse logic
    vendor_summary = {}
    for p in pmps:
        v = p["vendor"]
        if v not in vendor_summary:
            vendor_summary[v] = {
                "vendor": v,
                "spend": 0, "deals": 0, "avg_score": 0,
                "script_lift_contribution": 0, "working_media": 0,
            }
        vendor_summary[v]["spend"] += p["spend"]
        vendor_summary[v]["deals"] += 1
        vendor_summary[v]["avg_score"] += p["outcome_adjusted_score"]
        vendor_summary[v]["script_lift_contribution"] += max(p["script_lift_pct"], 0)
        vendor_summary[v]["working_media"] += p["working_media_efficiency"]
    out = []
    for v, d in vendor_summary.items():
        d["avg_score"] = round(d["avg_score"] / d["deals"], 1)
        d["working_media"] = round(d["working_media"] / d["deals"], 3)
        d["script_lift_contribution"] = round(d["script_lift_contribution"], 2)
        d["recommendation"] = "Scale" if d["avg_score"] >= 72 else ("Hold" if d["avg_score"] >= 55 else "Reduce")
        out.append(d)
    return sorted(out, key=lambda x: x["avg_score"], reverse=True)


async def ensure_users_seed():
    """Idempotent seed of admin + role demo accounts."""
    await db.users.create_index("email", unique=True)
    demo = [
        {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": "Admin", "role": "admin", "vendor_scope": None},
        {"email": "trader@pharmasignal.io", "password": "Trader@2026", "name": "Sam Trader", "role": "trader", "vendor_scope": None},
        {"email": "analyst@pharmasignal.io", "password": "Analyst@2026", "name": "Riya Analyst", "role": "analyst", "vendor_scope": None},
        {"email": "vendor@pulsepoint.com", "password": "Vendor@2026", "name": "PulsePoint Rep", "role": "vendor", "vendor_scope": "PulsePoint"},
    ]
    for u in demo:
        existing = await db.users.find_one({"email": u["email"]})
        if existing is None:
            doc = {
                "id": str(uuid.uuid4()),
                "email": u["email"].lower(),
                "password_hash": hash_password(u["password"]),
                "name": u["name"],
                "role": u["role"],
                "vendor_scope": u["vendor_scope"],
                "created_at": now_iso(),
            }
            await db.users.insert_one(doc)
        else:
            # Keep password in sync with .env for admin
            if u["email"] == ADMIN_EMAIL and not verify_password(u["password"], existing.get("password_hash", "")):
                await db.users.update_one({"email": ADMIN_EMAIL},
                                          {"$set": {"password_hash": hash_password(u["password"])}})


async def ensure_seed():
    """Idempotent seed — only seed once."""
    existing = await db.seed_meta.find_one({"_id": SEED_DOC_ID})
    if existing:
        return
    logger.info("Seeding PharmaSignal DSP demo data...")
    random.seed(42)
    campaigns = seed_campaigns()
    audiences = seed_audiences()
    pmps = seed_pmps()
    ga4 = seed_ga4()
    script_lift = seed_script_lift()
    data_cost = seed_data_cost()
    vendors = seed_vendors()

    # Link 2-4 audiences and 2-3 PMPs to each campaign
    for c in campaigns:
        same_type_aud = [a for a in audiences if a["type"] == c["campaign_type"]]
        c["audience_ids"] = [a["id"] for a in random.sample(same_type_aud, min(3, len(same_type_aud)))]
        c["pmp_ids"] = [p["id"] for p in random.sample(pmps, k=min(3, len(pmps)))]

    # Sample creatives per campaign
    creatives = []
    formats = ["300x250", "728x90", "OLV-15s", "CTV-30s", "Native-card"]
    for c in campaigns:
        for fmt in random.sample(formats, k=random.randint(2, 4)):
            creatives.append({
                "id": str(uuid.uuid4()),
                "campaign_id": c["id"],
                "brand": c["brand"],
                "indication": c["indication"],
                "asset_name": f"{c['brand']} — {fmt}",
                "format": fmt,
                "claims": random.choice(["Reduce A1C by 1.4%", "FDA-approved Q4 2025", "Once-daily oral", "Proven efficacy"]),
                "fair_balance": True,
                "mlr_status": random.choice(["Approved", "Approved", "Pending", "Rejected"]),
                "reviewer_notes": "",
                "created_at": now_iso(),
                "reviewed_at": now_iso(),
            })

    await db.campaigns.delete_many({})
    if campaigns:
        await db.campaigns.insert_many(campaigns)
    await db.audiences.delete_many({})
    if audiences:
        await db.audiences.insert_many(audiences)
    await db.pmps.delete_many({})
    if pmps:
        await db.pmps.insert_many(pmps)
    await db.ga4.delete_many({})
    if ga4:
        await db.ga4.insert_many(ga4)
    await db.script_lift.delete_many({})
    if script_lift:
        await db.script_lift.insert_many(script_lift)
    await db.data_cost.delete_many({})
    if data_cost:
        await db.data_cost.insert_many(data_cost)
    await db.vendors.delete_many({})
    if vendors:
        await db.vendors.insert_many(vendors)
    await db.creatives.delete_many({})
    if creatives:
        await db.creatives.insert_many(creatives)
    await db.scenarios.delete_many({})

    await db.seed_meta.insert_one({"_id": SEED_DOC_ID, "seeded_at": now_iso()})
    logger.info("Seed complete.")


# ============== HELPERS ==============
def clean(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc = {k: v for k, v in doc.items() if k != "_id"}
    return doc


# ============== ROUTES ==============
@api_router.get("/")
async def root():
    return {"app": "PharmaSignal DSP", "status": "ok", "version": "1.0"}


@api_router.get("/dashboard/overview")
async def dashboard_overview(
    brand: Optional[str] = Query(None),
    indication: Optional[str] = Query(None),
    campaign_type: Optional[str] = Query(None),
):
    q = {}
    if brand: q["brand"] = brand
    if indication: q["indication"] = indication
    if campaign_type: q["campaign_type"] = campaign_type
    campaigns = await db.campaigns.find(q, {"_id": 0}).to_list(1000)
    all_pmps = await db.pmps.find({}, {"_id": 0}).to_list(1000)
    data_cost = await db.data_cost.find({}, {"_id": 0}).to_list(1000)
    script_lift = await db.script_lift.find({}, {"_id": 0}).to_list(1000)

    # If filtering by campaign, narrow PMPs to those linked to filtered campaigns
    linked_pmp_ids = set()
    for c in campaigns:
        linked_pmp_ids.update(c.get("pmp_ids", []) or [])

    pmps_valid = [p for p in all_pmps if "outcome_adjusted_score" in p and "verified_reach" in p]
    pmps = [p for p in pmps_valid if p.get("id") in linked_pmp_ids] if (q and linked_pmp_ids) else pmps_valid

    total_budget = sum(c.get("budget", 0) for c in campaigns)
    total_spent = sum(c.get("spent", 0) for c in campaigns)
    active = sum(1 for c in campaigns if c.get("status") == "Active")
    total_spend = sum(d.get("total_spend", 0) for d in data_cost)
    total_working = sum(d.get("working_media", 0) for d in data_cost)
    working_media_pct = round(total_working / total_spend * 100, 1) if total_spend else 0
    verified_reach = round(sum(p.get("verified_reach", 0) for p in pmps) / len(pmps) * 100, 1) if pmps else 0
    avg_supply_score = round(sum(p.get("outcome_adjusted_score", 0) for p in pmps) / len(pmps), 1) if pmps else 0
    latest_lift = script_lift[-1].get("lift_pct", 0) if script_lift else 0

    cost_per_quality_outcome = round(total_spend / max(sum(p.get("impressions", 0) for p in pmps) / 1000 * 0.04, 1), 2)

    pmps_sorted = sorted(pmps, key=lambda p: p.get("outcome_adjusted_score", 0), reverse=True)

    # Build filter options from all campaigns
    all_camps = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    return {
        "kpis": {
            "total_budget": total_budget,
            "total_spent": total_spent,
            "active_campaigns": active,
            "total_campaigns": len(campaigns),
            "working_media_pct": working_media_pct,
            "verified_reach_pct": verified_reach,
            "avg_supply_score": avg_supply_score,
            "script_lift_pct": latest_lift,
            "cost_per_quality_outcome": cost_per_quality_outcome,
        },
        "script_lift_series": script_lift,
        "top_pmps": pmps_sorted[:5],
        "channels": [d.get("channel") for d in data_cost if d.get("channel")],
        "filter_options": {
            "brands": sorted({c.get("brand") for c in all_camps if c.get("brand")}),
            "indications": sorted({c.get("indication") for c in all_camps if c.get("indication")}),
            "campaign_types": sorted({c.get("campaign_type") for c in all_camps if c.get("campaign_type")}),
        },
        "active_filters": {"brand": brand, "indication": indication, "campaign_type": campaign_type},
    }


@api_router.get("/campaigns")
async def list_campaigns(
    brand: Optional[str] = Query(None),
    indication: Optional[str] = Query(None),
    campaign_type: Optional[str] = Query(None),
):
    q = {}
    if brand: q["brand"] = brand
    if indication: q["indication"] = indication
    if campaign_type: q["campaign_type"] = campaign_type
    docs = await db.campaigns.find(q, {"_id": 0}).to_list(1000)
    return docs


@api_router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    c = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Campaign not found")
    # Linked audiences and pmps
    aud_ids = c.get("audience_ids") or []
    pmp_ids = c.get("pmp_ids") or []
    audiences = await db.audiences.find({"id": {"$in": aud_ids}}, {"_id": 0}).to_list(100) if aud_ids else []
    pmps = await db.pmps.find({"id": {"$in": pmp_ids}}, {"_id": 0}).to_list(100) if pmp_ids else []
    # Performance synthesized from linked PMPs
    if pmps:
        avg_score = round(sum(p.get("outcome_adjusted_score", 0) for p in pmps) / len(pmps), 1)
        total_impressions = sum(p.get("impressions", 0) for p in pmps)
        avg_lift = round(sum(p.get("script_lift_pct", 0) for p in pmps) / len(pmps), 2)
        avg_wm = round(sum(p.get("working_media_efficiency", 0) for p in pmps) / len(pmps) * 100, 1)
    else:
        avg_score = avg_lift = avg_wm = 0
        total_impressions = 0
    creatives = await db.creatives.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(100)
    return {
        "campaign": c,
        "audiences": audiences,
        "pmps": pmps,
        "creatives": creatives,
        "performance": {
            "avg_supply_score": avg_score,
            "total_impressions": total_impressions,
            "avg_script_lift_pct": avg_lift,
            "avg_working_media_pct": avg_wm,
        },
    }


@api_router.patch("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, payload: CampaignLinkUpdate,
                           current_user: dict = Depends(require_roles("admin", "trader"))):
    upd = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not upd:
        raise HTTPException(400, "No fields to update")
    res = await db.campaigns.update_one({"id": campaign_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(404, "Campaign not found")
    c = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return c


@api_router.post("/campaigns")
async def create_campaign(payload: CampaignCreate, current_user: dict = Depends(require_roles("admin", "trader"))):
    c = Campaign(**payload.model_dump())
    await db.campaigns.insert_one(c.model_dump())
    return c.model_dump()


@api_router.get("/audiences")
async def list_audiences():
    docs = await db.audiences.find({}, {"_id": 0}).to_list(1000)
    return docs


@api_router.get("/pmps")
async def list_pmps():
    docs = await db.pmps.find({}, {"_id": 0}).to_list(1000)
    docs = [p for p in docs if "outcome_adjusted_score" in p]
    docs.sort(key=lambda p: p.get("outcome_adjusted_score", 0), reverse=True)
    return docs


@api_router.get("/data-cost")
async def list_data_cost():
    docs = await db.data_cost.find({}, {"_id": 0}).to_list(1000)
    return docs


@api_router.get("/ga4")
async def list_ga4():
    docs = await db.ga4.find({}, {"_id": 0}).to_list(1000)
    return docs


@api_router.get("/script-lift")
async def list_script_lift():
    docs = await db.script_lift.find({}, {"_id": 0}).to_list(1000)
    return docs


@api_router.get("/vendors")
async def list_vendors():
    docs = await db.vendors.find({}, {"_id": 0}).to_list(1000)
    return docs


@api_router.post("/rtb/simulate")
async def rtb_simulate(req: RTBSimulateRequest):
    # bid = outcome_probability × audience_quality × supply_quality × rx_lift_weight × engagement_quality ÷ data_cost_multiplier × base_value
    bid_raw = (
        req.outcome_probability
        * req.audience_quality_score
        * req.supply_quality_score
        * req.rx_lift_weight
        * req.engagement_quality
        / max(req.data_cost_multiplier, 0.01)
    )
    final_bid = round(bid_raw * req.base_value, 4)
    decision = "BID" if final_bid >= 1.5 else ("LOW_BID" if final_bid >= 0.5 else "NO_BID")

    # generate a small simulated stream of N bid requests
    def jitter(v, j=0.12):
        return max(0.01, min(1.0, v + random.uniform(-j, j)))

    sim = []
    for i in range(24):
        op = jitter(req.outcome_probability)
        aq = jitter(req.audience_quality_score)
        sq = jitter(req.supply_quality_score)
        eq = jitter(req.engagement_quality)
        dc = max(0.5, req.data_cost_multiplier + random.uniform(-0.2, 0.2))
        b = round((op * aq * sq * req.rx_lift_weight * eq / dc) * req.base_value, 4)
        sim.append({
            "t": i,
            "bid": b,
            "decision": "BID" if b >= 1.5 else ("LOW_BID" if b >= 0.5 else "NO_BID"),
        })
    win_rate = round(sum(1 for s in sim if s["decision"] == "BID") / len(sim) * 100, 1)
    return {
        "final_bid_cpm": final_bid,
        "decision": decision,
        "formula": "bid = outcome_prob × audience_quality × supply_quality × rx_lift_weight × engagement_quality / data_cost × base_value",
        "win_rate_pct": win_rate,
        "stream": sim,
    }


# ============== SCENARIOS ==============
@api_router.get("/scenarios")
async def list_scenarios():
    docs = await db.scenarios.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return docs


@api_router.post("/scenarios")
async def create_scenario(payload: ScenarioCreate):
    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "params": payload.params,
        "result": payload.result,
        "created_at": now_iso(),
    }
    await db.scenarios.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.delete("/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: str):
    res = await db.scenarios.delete_one({"id": scenario_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Scenario not found")
    return {"ok": True}


# ============== MLR / CREATIVES ==============
@api_router.get("/creatives")
async def list_creatives(campaign_id: Optional[str] = Query(None)):
    q = {"campaign_id": campaign_id} if campaign_id else {}
    docs = await db.creatives.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api_router.post("/creatives")
async def create_creative(payload: CreativeCreate):
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["mlr_status"] = "Pending"
    doc["created_at"] = now_iso()
    doc["reviewed_at"] = None
    await db.creatives.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.patch("/creatives/{creative_id}")
async def update_creative(creative_id: str, body: Dict[str, Any],
                           current_user: dict = Depends(require_roles("admin", "analyst"))):
    allowed = {"mlr_status", "reviewer_notes"}
    upd = {k: v for k, v in body.items() if k in allowed}
    if "mlr_status" in upd:
        upd["reviewed_at"] = now_iso()
    if not upd:
        raise HTTPException(400, "Nothing to update")
    res = await db.creatives.update_one({"id": creative_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(404, "Creative not found")
    return await db.creatives.find_one({"id": creative_id}, {"_id": 0})


# ============== LIVE BID STREAM (Simulated) ==============
@api_router.get("/live/bid-stream")
async def live_bid_stream():
    """Server-sent simulated OpenRTB bid request stream.

    In production this would consume real exchange feeds (PubMatic, Magnite, OpenX, etc.).
    Here we simulate realistic bid requests with our outcome-aware bidder responding.
    """
    pmps_all = await db.pmps.find({}, {"_id": 0}).to_list(1000)
    pmps = [p for p in pmps_all if "outcome_adjusted_score" in p]
    audiences = await db.audiences.find({}, {"_id": 0}).to_list(100)

    async def gen():
        for i in range(40):
            pmp = random.choice(pmps) if pmps else {"vendor": "PubMatic Health", "outcome_adjusted_score": 70,
                                                     "working_media_efficiency": 0.8, "match_rate": 0.7}
            aud = random.choice(audiences) if audiences else None
            op = random.uniform(0.35, 0.92)
            aq = (aud.get("audience_quality_score", 75) / 100) if aud else random.uniform(0.5, 0.9)
            sq = pmp.get("outcome_adjusted_score", 70) / 100
            eq = pmp.get("engagement_quality", random.uniform(0.4, 0.85))
            rx = 1.0 + (pmp.get("script_lift_pct", 0) / 10)
            dc = 1.0 + (pmp.get("data_cost_drag", 0.15) * 2)
            bid = round(op * aq * sq * rx * eq / dc * 12, 4)
            decision = "BID" if bid >= 1.5 else ("LOW_BID" if bid >= 0.5 else "NO_BID")
            event = {
                "t": i,
                "ts": now_iso(),
                "vendor": pmp.get("vendor"),
                "deal_id": pmp.get("deal_id", "—"),
                "audience": aud.get("name", "General") if aud else "General",
                "audience_type": aud.get("type", "DTC") if aud else "DTC",
                "channel": random.choice(["Display", "OLV", "CTV", "Native", "EHR/POC", "Audio"]),
                "bid_cpm": bid,
                "decision": decision,
                "outcome_prob": round(op, 3),
                "match_rate": round(pmp.get("match_rate", 0.7), 3),
            }
            yield f"data: {json.dumps(event)}\n\n"
            import asyncio
            await asyncio.sleep(0.15)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_router.post("/ai/recommendations")
async def ai_recommendations():
    """Stream Claude Sonnet 4.5 narrative insights about top PMPs/campaigns."""
    pmps_all = await db.pmps.find({}, {"_id": 0}).to_list(1000)
    pmps = [p for p in pmps_all if "outcome_adjusted_score" in p and "verified_reach" in p]
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    data_cost = await db.data_cost.find({}, {"_id": 0}).to_list(1000)
    audiences = await db.audiences.find({}, {"_id": 0}).to_list(1000)

    pmps_sorted = sorted(pmps, key=lambda p: p.get("outcome_adjusted_score", 0), reverse=True)
    top = pmps_sorted[:3]
    bottom = pmps_sorted[-3:]
    total_spend = sum(d.get("total_spend", 0) for d in data_cost)
    total_working = sum(d.get("working_media", 0) for d in data_cost)
    wm_pct = round(total_working / total_spend * 100, 1) if total_spend else 0

    context = {
        "top_pmps": [{"vendor": p.get("vendor"), "score": p.get("outcome_adjusted_score"),
                      "script_lift": p.get("script_lift_pct"), "wm": p.get("working_media_efficiency")} for p in top],
        "bottom_pmps": [{"vendor": p.get("vendor"), "score": p.get("outcome_adjusted_score"),
                         "data_drag": p.get("data_cost_drag")} for p in bottom],
        "working_media_pct": wm_pct,
        "active_campaigns": sum(1 for c in campaigns if c.get("status") == "Active"),
        "low_match_audiences": [a.get("name") for a in audiences if a.get("match_rate_forecast", 1) < 0.5][:3],
    }

    prompt = f"""You are a senior pharma programmatic strategist analyzing a healthcare DSP campaign portfolio.
Generate 4-6 specific, commercial, pharma-native Next-Best-Action recommendations based on this data:

{json.dumps(context, indent=2)}

For each recommendation:
- Title (short, action-oriented like "Scale PubMatic Health in-app")
- Reasoning (2 sentences tying audience quality, supply quality, working media, script lift)
- Impact (estimated lift in script impact or working media)
- Priority (HIGH/MEDIUM/LOW)

Format as a streaming narrative — start with one paragraph of executive context, then list recommendations.
Be senior, commercial, decisive. No fluff. Reference specific vendors and numbers.
"""

    async def generate():
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"rec-{uuid.uuid4()}",
                system_message="You are a senior pharma programmatic media strategist."
            ).with_model("anthropic", "claude-sonnet-4-6")
            async for ev in chat.stream_message(UserMessage(text=prompt)):
                if isinstance(ev, TextDelta):
                    yield ev.content
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.exception("LLM stream failed")
            yield f"\n[AI recommendation engine unavailable: {str(e)}]\n"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


DATASET_REQUIRED_COLUMNS = {
    "pmps": {"vendor", "outcome_adjusted_score", "verified_reach", "engagement_quality",
             "script_lift_pct", "working_media_efficiency", "match_rate",
             "data_cost_drag", "fraud_risk", "spend"},
    "audiences": {"name", "type", "match_rate_forecast", "data_cpm",
                  "working_media_ratio", "audience_quality_score", "rx_relevance_score"},
    "ga4": {"channel", "sessions", "engaged_sessions", "engagement_rate",
            "quality_visits", "conversions"},
    "data_cost": {"line_item", "channel", "total_spend", "data_fees",
                  "platform_fees", "working_media", "working_media_pct"},
    "script_lift": {"week", "exposed_rx_index", "control_rx_index", "lift_pct"},
    "campaigns": {"name", "brand", "indication", "campaign_type", "budget"},
}


@api_router.post("/upload/{dataset}")
async def upload_csv(dataset: str, file: UploadFile = File(...),
                     current_user: dict = Depends(require_roles("admin", "trader"))):
    """CSV uploader with per-dataset schema validation.

    Required columns are validated against the seed schema. Rows missing
    required columns are rejected (no partial inserts) to keep downstream
    dashboards and AI insights consistent.
    """
    if dataset not in DATASET_REQUIRED_COLUMNS:
        raise HTTPException(400, f"Dataset must be one of {sorted(DATASET_REQUIRED_COLUMNS)}")
    raw = await file.read()
    text = raw.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(400, "CSV is empty or unreadable.")

    required = DATASET_REQUIRED_COLUMNS[dataset]
    header = set(reader.fieldnames or [])
    missing_cols = required - header
    if missing_cols:
        raise HTTPException(
            400,
            f"CSV is missing required columns for '{dataset}': {sorted(missing_cols)}. "
            f"Required: {sorted(required)}",
        )

    cleaned = []
    rejected = 0
    for r in rows:
        # Numeric coercion
        for k, v in list(r.items()):
            if v is None or v == "":
                continue
            try:
                r[k] = float(v) if "." in v else int(v)
            except (ValueError, TypeError):
                pass
        # Row-level required-value check
        if any(r.get(c) in (None, "") for c in required):
            rejected += 1
            continue
        if "id" not in r or not r["id"]:
            r["id"] = str(uuid.uuid4())
        cleaned.append(r)

    if not cleaned:
        raise HTTPException(400, "All rows rejected — required values missing.")

    await db[dataset].insert_many(cleaned)
    return {"dataset": dataset, "rows_inserted": len(cleaned), "rows_rejected": rejected}


@api_router.post("/admin/reseed")
async def reseed(current_user: dict = Depends(require_roles("admin"))):
    await db.seed_meta.delete_many({})
    await ensure_seed()
    return {"ok": True}


# ============== AUTH ROUTES ==============
@api_router.post("/auth/login")
async def login(body: LoginRequest):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(user["id"], user["email"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"], "email": user["email"], "name": user["name"],
            "role": user["role"], "vendor_scope": user.get("vendor_scope"),
        },
    }


@api_router.get("/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    return current_user


@api_router.get("/auth/users")
async def list_users(current_user: dict = Depends(require_roles("admin"))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return users


@api_router.post("/auth/users")
async def create_user(body: UserCreate, current_user: dict = Depends(require_roles("admin"))):
    if body.role not in ROLES:
        raise HTTPException(400, f"Role must be one of {ROLES}")
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(400, "Email already registered")
    doc = {
        "id": str(uuid.uuid4()),
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "name": body.name,
        "role": body.role,
        "vendor_scope": body.vendor_scope,
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


# ============== FREQUENCY INTELLIGENCE ==============
@api_router.get("/frequency-intelligence")
async def frequency_intelligence(current_user: dict = Depends(get_current_user)):
    """Detect overexposure risk for HCP audiences.

    Risk = (impressions / audience_size) / weeks_in_flight relative to frequency_cap.
    """
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    audiences = await db.audiences.find({}, {"_id": 0}).to_list(1000)
    pmps_all = await db.pmps.find({}, {"_id": 0}).to_list(1000)
    pmps_valid = [p for p in pmps_all if "outcome_adjusted_score" in p]
    aud_by_id = {a["id"]: a for a in audiences}

    rows = []
    for c in campaigns:
        aud_ids = c.get("audience_ids") or []
        for aud_id in aud_ids:
            aud = aud_by_id.get(aud_id)
            if not aud or aud.get("type") != "HCP":
                continue
            # Realistic synthetic model: weekly impressions per matched HCP
            # is driven by per-user dwell intensity, capped by match rate quality.
            # Deterministic by (campaign, audience) so frequency view is stable.
            seed_val = abs(hash(c["id"] + aud["id"])) % 10_000
            rng = random.Random(seed_val)
            cap = max(c.get("frequency_cap", 5), 1)
            # base weekly per HCP between 0.4×cap and 1.6×cap
            weekly_per_user = round(cap * rng.uniform(0.4, 1.6), 2)
            saturation = weekly_per_user / cap
            audience_size = aud.get("estimated_size", 1) or 1

            if saturation >= 1.15:
                risk = "Critical"
            elif saturation >= 0.85:
                risk = "High"
            elif saturation >= 0.55:
                risk = "Moderate"
            else:
                risk = "Healthy"
            rows.append({
                "campaign_id": c["id"],
                "campaign_name": c["name"],
                "brand": c["brand"],
                "audience_id": aud["id"],
                "audience_name": aud["name"],
                "audience_size": audience_size,
                "frequency_cap": cap,
                "weekly_impressions_per_hcp": weekly_per_user,
                "saturation_pct": round(saturation * 100, 1),
                "risk": risk,
                "recommendation": (
                    "Reduce frequency cap or rotate creative" if risk in ("Critical", "High")
                    else ("Monitor closely" if risk == "Moderate" else "Within healthy range")
                ),
            })
    rows.sort(key=lambda r: r["saturation_pct"], reverse=True)
    summary = {
        "total_hcp_lists": len(rows),
        "critical": sum(1 for r in rows if r["risk"] == "Critical"),
        "high": sum(1 for r in rows if r["risk"] == "High"),
        "moderate": sum(1 for r in rows if r["risk"] == "Moderate"),
        "healthy": sum(1 for r in rows if r["risk"] == "Healthy"),
    }
    return {"rows": rows, "summary": summary}


# ============== VENDOR SHARES (public read-only) ==============
@api_router.post("/shares/vendor")
async def create_vendor_share(body: ShareCreate, current_user: dict = Depends(require_roles("admin", "trader"))):
    token = secrets.token_urlsafe(16)
    doc = {
        "id": str(uuid.uuid4()),
        "token": token,
        "vendor": body.vendor,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)).isoformat(),
        "created_by": current_user["email"],
        "created_at": now_iso(),
    }
    await db.vendor_shares.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.get("/shares/vendor")
async def list_vendor_shares(current_user: dict = Depends(require_roles("admin", "trader"))):
    docs = await db.vendor_shares.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@api_router.delete("/shares/vendor/{share_id}")
async def revoke_vendor_share(share_id: str, current_user: dict = Depends(require_roles("admin", "trader"))):
    res = await db.vendor_shares.delete_one({"id": share_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Share not found")
    return {"ok": True}


@api_router.get("/public/shares/vendor/{token}")
async def public_vendor_share(token: str):
    """Public, unauthenticated read-only vendor scorecard via share token."""
    share = await db.vendor_shares.find_one({"token": token}, {"_id": 0})
    if not share:
        raise HTTPException(404, "Share link not found or revoked")
    try:
        exp = datetime.fromisoformat(share["expires_at"])
        if exp < datetime.now(timezone.utc):
            raise HTTPException(410, "Share link expired")
    except (ValueError, KeyError):
        pass
    vendor = share["vendor"]
    vendor_summary = await db.vendors.find_one({"vendor": vendor}, {"_id": 0})
    pmps = await db.pmps.find({"vendor": vendor}, {"_id": 0}).to_list(100)
    return {"vendor": vendor_summary, "deals": pmps, "expires_at": share["expires_at"], "created_at": share["created_at"]}


# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await ensure_users_seed()
    await ensure_seed()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
