"""PharmaSignal DSP backend API tests."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pharma-signal.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Health ----------
class TestHealth:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["app"] == "PharmaSignal DSP"


# ---------- Dashboard ----------
class TestDashboard:
    def test_overview(self, session):
        r = session.get(f"{API}/dashboard/overview")
        assert r.status_code == 200
        d = r.json()
        for k in ["total_budget", "total_spent", "active_campaigns", "working_media_pct",
                  "verified_reach_pct", "script_lift_pct", "avg_supply_score",
                  "cost_per_quality_outcome"]:
            assert k in d["kpis"], f"missing kpi {k}"
        assert isinstance(d["script_lift_series"], list)
        assert len(d["script_lift_series"]) == 12
        assert isinstance(d["top_pmps"], list)
        assert len(d["top_pmps"]) == 5


# ---------- Campaigns ----------
class TestCampaigns:
    def test_list_seeded(self, session):
        r = session.get(f"{API}/campaigns")
        assert r.status_code == 200
        camps = r.json()
        assert isinstance(camps, list)
        # at least the seeded 7
        assert len(camps) >= 7
        c0 = camps[0]
        for k in ["brand", "indication", "campaign_type", "budget", "spent", "outcome_kpi", "channels"]:
            assert k in c0
        assert c0["campaign_type"] in ("HCP", "DTC")

    def test_create_and_persist(self, session):
        payload = {
            "name": "TEST_CampaignX",
            "brand": "TestBrand",
            "indication": "Type 2 Diabetes",
            "campaign_type": "DTC",
            "budget": 100000,
            "flight_start": "2026-02-01",
            "flight_end": "2026-04-30",
            "outcome_kpi": "Script Lift",
            "channels": ["Display", "CTV"],
        }
        r = session.post(f"{API}/campaigns", json=payload)
        assert r.status_code == 200
        c = r.json()
        assert c["name"] == "TEST_CampaignX"
        assert c["budget"] == 100000
        assert "id" in c

        # verify persistence
        r2 = session.get(f"{API}/campaigns")
        names = [x["name"] for x in r2.json()]
        assert "TEST_CampaignX" in names


# ---------- Audiences ----------
class TestAudiences:
    def test_list(self, session):
        r = session.get(f"{API}/audiences")
        assert r.status_code == 200
        a = r.json()
        assert len(a) == 8
        first = a[0]
        for k in ["match_rate_forecast", "data_cpm", "working_media_ratio",
                  "audience_quality_score", "rx_relevance_score", "scale_risk", "waste_risk"]:
            assert k in first


# ---------- PMPs ----------
class TestPMPs:
    def test_list_sorted_and_fields(self, session):
        r = session.get(f"{API}/pmps")
        assert r.status_code == 200
        pmps = r.json()
        assert len(pmps) == 8
        scores = [p["outcome_adjusted_score"] for p in pmps]
        assert scores == sorted(scores, reverse=True)
        p0 = pmps[0]
        for k in ["verified_reach", "engagement_quality", "script_lift_pct",
                  "working_media_efficiency", "match_rate", "data_cost_drag",
                  "fraud_risk", "outcome_adjusted_score", "recommendation"]:
            assert k in p0
        assert p0["recommendation"] in ("Scale", "Hold", "Reduce")


# ---------- Data Cost ----------
class TestDataCost:
    def test_list(self, session):
        r = session.get(f"{API}/data-cost")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 7
        for k in ["total_spend", "working_media", "data_fees", "platform_fees", "working_media_pct"]:
            assert k in rows[0]


# ---------- GA4 ----------
class TestGA4:
    def test_list(self, session):
        r = session.get(f"{API}/ga4")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 7
        for k in ["sessions", "engaged_sessions", "engagement_rate", "quality_visits", "conversions"]:
            assert k in rows[0]


# ---------- Script Lift ----------
class TestScriptLift:
    def test_list(self, session):
        r = session.get(f"{API}/script-lift")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 12
        for k in ["exposed_rx_index", "control_rx_index", "lift_pct"]:
            assert k in rows[0]


# ---------- Vendors ----------
class TestVendors:
    def test_list(self, session):
        r = session.get(f"{API}/vendors")
        assert r.status_code == 200
        v = r.json()
        assert len(v) >= 1
        for k in ["avg_score", "spend", "deals", "script_lift_contribution",
                  "working_media", "recommendation"]:
            assert k in v[0]


# ---------- RTB Simulator ----------
class TestRTB:
    def test_simulate(self, session):
        r = session.post(f"{API}/rtb/simulate", json={
            "outcome_probability": 0.7,
            "audience_quality_score": 0.8,
            "supply_quality_score": 0.75,
            "rx_lift_weight": 1.2,
            "engagement_quality": 0.65,
            "data_cost_multiplier": 1.3,
            "base_value": 12.0,
        })
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["final_bid_cpm"], (int, float))
        assert d["decision"] in ("BID", "LOW_BID", "NO_BID")
        assert isinstance(d["win_rate_pct"], (int, float))
        assert "formula" in d
        assert len(d["stream"]) == 24
        for s in d["stream"]:
            assert {"t", "bid", "decision"}.issubset(s.keys())


# ---------- AI Recommendations (streaming) ----------
class TestAI:
    def test_stream_returns_text(self, session):
        r = session.post(f"{API}/ai/recommendations", stream=True, timeout=60)
        assert r.status_code == 200
        chunks = []
        for chunk in r.iter_content(chunk_size=64, decode_unicode=True):
            if chunk:
                chunks.append(chunk)
            if sum(len(c) for c in chunks) > 50:
                break
        body = "".join(chunks)
        assert len(body) > 0, "AI stream returned empty body"


# ---------- CSV Upload ----------
class TestUpload:
    def test_upload_pmps_csv(self, session):
        csv_text = "vendor,score\nTEST_Vendor1,88\nTEST_Vendor2,72\n"
        files = {"file": ("test.csv", io.BytesIO(csv_text.encode()), "text/csv")}
        # Override Content-Type for multipart
        s = requests.Session()
        r = s.post(f"{API}/upload/pmps", files=files)
        assert r.status_code == 200
        d = r.json()
        assert d["dataset"] == "pmps"
        assert d["rows_inserted"] == 2

    def test_upload_invalid_dataset(self, session):
        s = requests.Session()
        files = {"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")}
        r = s.post(f"{API}/upload/bogus", files=files)
        assert r.status_code == 400
