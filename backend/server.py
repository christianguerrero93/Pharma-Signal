"""PharmaSignal DSP — Backend API.

A pharma-native demand-side platform with intelligence layer:
- Campaigns, Audiences, PMPs, Vendors, Script Lift, GA4 engagement
- Outcome-Adjusted Supply Score (killer feature)
- RTB bid simulator
- AI-powered next-best-action recommendations via Claude Sonnet 4.5
"""
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import csv
import json
import logging
import random
import uuid
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

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


class RTBSimulateRequest(BaseModel):
    outcome_probability: float = 0.6
    audience_quality_score: float = 0.75
    supply_quality_score: float = 0.7
    rx_lift_weight: float = 1.2
    engagement_quality: float = 0.65
    data_cost_multiplier: float = 1.3
    base_value: float = 12.0  # base CPM willingness


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
async def dashboard_overview():
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    pmps = await db.pmps.find({}, {"_id": 0}).to_list(1000)
    data_cost = await db.data_cost.find({}, {"_id": 0}).to_list(1000)
    script_lift = await db.script_lift.find({}, {"_id": 0}).to_list(1000)

    total_budget = sum(c.get("budget", 0) for c in campaigns)
    total_spent = sum(c.get("spent", 0) for c in campaigns)
    active = sum(1 for c in campaigns if c.get("status") == "Active")
    total_spend = sum(d["total_spend"] for d in data_cost)
    total_working = sum(d["working_media"] for d in data_cost)
    working_media_pct = round(total_working / total_spend * 100, 1) if total_spend else 0
    verified_reach = round(sum(p["verified_reach"] for p in pmps) / len(pmps) * 100, 1) if pmps else 0
    avg_supply_score = round(sum(p["outcome_adjusted_score"] for p in pmps) / len(pmps), 1) if pmps else 0
    latest_lift = script_lift[-1]["lift_pct"] if script_lift else 0

    cost_per_quality_outcome = round(total_spend / max(sum(p.get("impressions", 0) for p in pmps) / 1000 * 0.04, 1), 2)

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
        "top_pmps": pmps[:5],
        "channels": [d["channel"] for d in data_cost],
    }


@api_router.get("/campaigns")
async def list_campaigns():
    docs = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    return docs


@api_router.post("/campaigns")
async def create_campaign(payload: CampaignCreate):
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
    docs.sort(key=lambda p: p["outcome_adjusted_score"], reverse=True)
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


@api_router.post("/ai/recommendations")
async def ai_recommendations():
    """Stream Claude Sonnet 4.5 narrative insights about top PMPs/campaigns."""
    pmps = await db.pmps.find({}, {"_id": 0}).to_list(1000)
    campaigns = await db.campaigns.find({}, {"_id": 0}).to_list(1000)
    data_cost = await db.data_cost.find({}, {"_id": 0}).to_list(1000)
    audiences = await db.audiences.find({}, {"_id": 0}).to_list(1000)

    pmps_sorted = sorted(pmps, key=lambda p: p["outcome_adjusted_score"], reverse=True)
    top = pmps_sorted[:3]
    bottom = pmps_sorted[-3:]
    total_spend = sum(d["total_spend"] for d in data_cost)
    total_working = sum(d["working_media"] for d in data_cost)
    wm_pct = round(total_working / total_spend * 100, 1) if total_spend else 0

    context = {
        "top_pmps": [{"vendor": p["vendor"], "score": p["outcome_adjusted_score"],
                      "script_lift": p["script_lift_pct"], "wm": p["working_media_efficiency"]} for p in top],
        "bottom_pmps": [{"vendor": p["vendor"], "score": p["outcome_adjusted_score"],
                         "data_drag": p["data_cost_drag"]} for p in bottom],
        "working_media_pct": wm_pct,
        "active_campaigns": sum(1 for c in campaigns if c.get("status") == "Active"),
        "low_match_audiences": [a["name"] for a in audiences if a["match_rate_forecast"] < 0.5][:3],
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


@api_router.post("/upload/{dataset}")
async def upload_csv(dataset: str, file: UploadFile = File(...)):
    """Generic CSV uploader for pmps/audiences/ga4/data_cost."""
    allowed = {"pmps", "audiences", "ga4", "data_cost", "script_lift", "campaigns"}
    if dataset not in allowed:
        raise HTTPException(400, f"Dataset must be one of {allowed}")
    raw = await file.read()
    text = raw.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    # Attempt numeric coercion
    for r in rows:
        for k, v in list(r.items()):
            if v is None or v == "":
                continue
            try:
                if "." in v:
                    r[k] = float(v)
                else:
                    r[k] = int(v)
            except (ValueError, TypeError):
                pass
        if "id" not in r:
            r["id"] = str(uuid.uuid4())
    if rows:
        await db[dataset].insert_many(rows)
    return {"dataset": dataset, "rows_inserted": len(rows)}


@api_router.post("/admin/reseed")
async def reseed():
    await db.seed_meta.delete_many({})
    await ensure_seed()
    return {"ok": True}


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
    await ensure_seed()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
