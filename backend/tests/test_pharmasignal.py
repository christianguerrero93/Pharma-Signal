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


# ---------- CSV Upload (schema-validated) ----------
class TestUpload:
    def test_upload_pmps_invalid_schema_rejected(self, session):
        # Bug-fix: now rejected because columns don't match required schema
        csv_text = "vendor,score\nTEST_Vendor1,88\nTEST_Vendor2,72\n"
        files = {"file": ("test.csv", io.BytesIO(csv_text.encode()), "text/csv")}
        s = requests.Session()
        r = s.post(f"{API}/upload/pmps", files=files)
        assert r.status_code == 400, f"expected 400 invalid schema, got {r.status_code}"

    def test_upload_invalid_dataset(self, session):
        s = requests.Session()
        files = {"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")}
        r = s.post(f"{API}/upload/bogus", files=files)
        assert r.status_code == 400

    def test_upload_valid_script_lift(self, session):
        # script_lift schema accepts: week, exposed_rx_index, control_rx_index, lift_pct
        csv_text = (
            "week,exposed_rx_index,control_rx_index,lift_pct\n"
            "TEST_W1,101.2,100.1,1.1\n"
            "TEST_W2,103.5,100.5,2.99\n"
        )
        s = requests.Session()
        files = {"file": ("sl.csv", io.BytesIO(csv_text.encode()), "text/csv")}
        r = s.post(f"{API}/upload/script_lift", files=files)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["dataset"] == "script_lift"
        assert d["rows_inserted"] == 2


# ---------- Dashboard filters (NEW) ----------
class TestDashboardFilters:
    def test_filter_by_campaign_type_hcp(self, session):
        r_all = session.get(f"{API}/dashboard/overview")
        assert r_all.status_code == 200
        total_all = r_all.json()["kpis"]["total_campaigns"]
        r = session.get(f"{API}/dashboard/overview", params={"campaign_type": "HCP"})
        assert r.status_code == 200
        d = r.json()
        assert d["kpis"]["total_campaigns"] <= total_all
        # Verify it matches campaigns endpoint filter
        camps = session.get(f"{API}/campaigns", params={"campaign_type": "HCP"}).json()
        assert d["kpis"]["total_campaigns"] == len(camps)
        assert d["active_filters"]["campaign_type"] == "HCP"
        fo = d["filter_options"]
        assert "brands" in fo and "indications" in fo and "campaign_types" in fo
        assert "HCP" in fo["campaign_types"]

    def test_filter_by_brand(self, session):
        camps = session.get(f"{API}/campaigns").json()
        brand = camps[0]["brand"]
        r = session.get(f"{API}/dashboard/overview", params={"brand": brand})
        assert r.status_code == 200
        assert r.json()["kpis"]["total_campaigns"] >= 1


# ---------- Campaign detail + PATCH (NEW) ----------
class TestCampaignDetail:
    def test_get_campaign_detail(self, session):
        camps = session.get(f"{API}/campaigns").json()
        # find first seeded campaign that has links
        seeded = [c for c in camps if c.get("audience_ids") and c.get("pmp_ids")]
        assert seeded, "No seeded campaigns with linked audiences/pmps"
        cid = seeded[0]["id"]
        r = session.get(f"{API}/campaigns/{cid}")
        assert r.status_code == 200
        d = r.json()
        assert d["campaign"]["id"] == cid
        assert isinstance(d["audiences"], list) and len(d["audiences"]) >= 1
        assert isinstance(d["pmps"], list) and len(d["pmps"]) >= 1
        assert isinstance(d["creatives"], list)
        perf = d["performance"]
        for k in ["avg_supply_score", "total_impressions",
                  "avg_script_lift_pct", "avg_working_media_pct"]:
            assert k in perf

    def test_get_campaign_404(self, session):
        r = session.get(f"{API}/campaigns/does-not-exist")
        assert r.status_code == 404

    def test_patch_campaign_links(self, session):
        camps = session.get(f"{API}/campaigns").json()
        cid = camps[0]["id"]
        auds = session.get(f"{API}/audiences").json()
        pmps = session.get(f"{API}/pmps").json()
        new_aud = [auds[0]["id"], auds[1]["id"]]
        new_pmp = [pmps[0]["id"]]
        r = session.patch(f"{API}/campaigns/{cid}",
                          json={"audience_ids": new_aud, "pmp_ids": new_pmp})
        assert r.status_code == 200
        updated = r.json()
        assert updated["audience_ids"] == new_aud
        assert updated["pmp_ids"] == new_pmp
        # verify persisted
        r2 = session.get(f"{API}/campaigns/{cid}")
        assert r2.status_code == 200
        assert r2.json()["campaign"]["audience_ids"] == new_aud


# ---------- Scenarios CRUD (NEW) ----------
class TestScenarios:
    def test_scenario_create_list_delete(self, session):
        payload = {
            "name": "TEST_Scenario_Alpha",
            "params": {"outcome_probability": 0.7, "base_value": 12.0},
            "result": {"final_bid_cpm": 2.34, "decision": "BID"},
        }
        r = session.post(f"{API}/scenarios", json=payload)
        assert r.status_code == 200, r.text
        s = r.json()
        sid = s["id"]
        assert s["name"] == "TEST_Scenario_Alpha"
        assert s["params"]["base_value"] == 12.0

        # list newest-first
        lst = session.get(f"{API}/scenarios").json()
        ids = [x["id"] for x in lst]
        assert sid in ids
        assert lst[0]["id"] == sid

        # delete
        d = session.delete(f"{API}/scenarios/{sid}")
        assert d.status_code == 200
        # verify gone
        lst2 = session.get(f"{API}/scenarios").json()
        assert sid not in [x["id"] for x in lst2]

    def test_delete_missing_scenario(self, session):
        r = session.delete(f"{API}/scenarios/nope-12345")
        assert r.status_code == 404


# ---------- Creatives (NEW) ----------
class TestCreatives:
    def test_list_creatives_seeded(self, session):
        r = session.get(f"{API}/creatives")
        assert r.status_code == 200
        cs = r.json()
        assert len(cs) >= 14
        statuses = {c.get("mlr_status") for c in cs}
        assert "Approved" in statuses

    def test_filter_creatives_by_campaign(self, session):
        camps = session.get(f"{API}/campaigns").json()
        cid = camps[0]["id"]
        r = session.get(f"{API}/creatives", params={"campaign_id": cid})
        assert r.status_code == 200
        cs = r.json()
        for c in cs:
            assert c["campaign_id"] == cid

    def test_patch_creative_status(self, session):
        all_c = session.get(f"{API}/creatives").json()
        pending = [c for c in all_c if c.get("mlr_status") == "Pending"]
        if not pending:
            # Create one
            cr = session.post(f"{API}/creatives", json={
                "brand": "TestBrand", "indication": "T2D",
                "asset_name": "TEST_Asset", "format": "300x250",
            }).json()
            target = cr
        else:
            target = pending[0]
        r = session.patch(f"{API}/creatives/{target['id']}",
                          json={"mlr_status": "Approved",
                                "reviewer_notes": "TEST_ok"})
        assert r.status_code == 200
        d = r.json()
        assert d["mlr_status"] == "Approved"
        assert d["reviewer_notes"] == "TEST_ok"
        assert d.get("reviewed_at")


# ---------- Live bid stream (NEW) ----------
class TestLiveStream:
    def test_stream_emits_events(self, session):
        r = session.get(f"{API}/live/bid-stream", stream=True, timeout=30)
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        events = []
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                events.append(payload)
                if len(events) >= 5:
                    break
        r.close()
        assert len(events) >= 5
        import json as _json
        ev0 = _json.loads(events[0])
        for k in ["vendor", "channel", "audience", "bid_cpm", "decision"]:
            assert k in ev0
