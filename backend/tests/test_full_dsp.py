"""Pytest suite for the Pharma Signal Full DSP API.

Runs against a throwaway SQLite database (set via FULL_DSP_DB before import).
Covers: auth (JWT, refresh, rate limiting, tamper rejection), RBAC, campaigns,
bid engine (targeting, IVT, brand safety, frequency persistence), measurement
statistics, VAST validation, and user management.

Run: cd backend && python -m pytest tests/ -q
"""
from __future__ import annotations

import os
import sys
import tempfile

os.environ["FULL_DSP_DB"] = os.path.join(tempfile.mkdtemp(), "test_dsp.db")
os.environ.pop("DATABASE_URL", None)
os.environ["FULL_DSP_LOGIN_RATE_LIMIT"] = "3"
os.environ["FULL_DSP_LOGIN_RATE_WINDOW"] = "60"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

import full_dsp_server
from full_dsp_server import app

client = TestClient(app)
PASSWORD = "pharma-signal-local"


def login(email: str, password: str = PASSWORD) -> dict:
    resp = client.post("/api/full/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin() -> dict:
    return login("admin@pharmasignal.local")


@pytest.fixture(scope="session")
def trader() -> dict:
    return login("trader@pharmasignal.local")


@pytest.fixture(scope="session")
def analyst() -> dict:
    return login("analyst@pharmasignal.local")


@pytest.fixture(scope="session")
def campaign(trader) -> dict:
    resp = client.post("/api/full/campaign-build", headers=auth(trader["access_token"]), json={
        "campaign": {"name": "Test Launch", "brand": "TZIELD", "indication": "T1D", "audience_type": "DTC",
                     "objective": "lift", "budget": 500000, "flight_start": "2026-07-01", "flight_end": "2026-12-31", "status": "active"},
        "line_items": [{"name": "Display", "channel": "Display", "budget": 250000, "max_bid_cpm": 24,
                        "pacing_mode": "even", "status": "active", "frequency_cap": 3}],
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Auth & hardening
# ---------------------------------------------------------------------------
class TestAuth:
    def test_health(self):
        body = client.get("/health").json()
        assert body["status"] == "ok" and body["storage"] == "sqlite"

    def test_login_returns_access_and_refresh(self, admin):
        assert admin["access_token"].count(".") == 2
        assert admin["refresh_token"].count(".") == 2
        assert admin["user"]["role"] == "admin"

    def test_bad_password_rejected(self):
        assert client.post("/api/full/auth/login", json={"email": "admin@pharmasignal.local", "password": "wrong-pass-xyz"}).status_code == 401

    def test_tampered_token_rejected(self, admin):
        bad = admin["access_token"][:-4] + ("aaaa" if not admin["access_token"].endswith("aaaa") else "bbbb")
        assert client.get("/api/full/overview", headers=auth(bad)).status_code == 401

    def test_refresh_flow(self, admin):
        resp = client.post("/api/full/auth/refresh", json={"refresh_token": admin["refresh_token"]})
        assert resp.status_code == 200, resp.text
        new_access = resp.json()["access_token"]
        assert client.get("/api/full/auth/me", headers=auth(new_access)).status_code == 200

    def test_refresh_token_rejected_as_access(self, admin):
        assert client.get("/api/full/overview", headers=auth(admin["refresh_token"])).status_code == 401

    def test_access_token_rejected_for_refresh(self, admin):
        assert client.post("/api/full/auth/refresh", json={"refresh_token": admin["access_token"]}).status_code == 401

    def test_login_rate_limited_after_failures(self):
        full_dsp_server._login_failures.clear()
        for _ in range(3):
            client.post("/api/full/auth/login", json={"email": "victim@pharmasignal.local", "password": "nope"})
        resp = client.post("/api/full/auth/login", json={"email": "victim@pharmasignal.local", "password": "nope"})
        assert resp.status_code == 429
        full_dsp_server._login_failures.clear()


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------
class TestRBAC:
    def test_analyst_cannot_build_campaigns(self, analyst):
        resp = client.post("/api/full/campaign-build", headers=auth(analyst["access_token"]), json={
            "campaign": {"name": "x", "brand": "b", "indication": "i", "audience_type": "DTC", "objective": "o",
                         "budget": 1000, "flight_start": "2026-07-01", "flight_end": "2026-12-31", "status": "draft"},
            "line_items": []})
        assert resp.status_code == 403

    def test_trader_cannot_review_creatives(self, trader, campaign):
        cr = client.post("/api/full/creatives", headers=auth(trader["access_token"]), json={
            "campaign_id": campaign["campaign_id"], "name": "Hero", "fmt": "Display 300x250",
            "channel": "Display", "claims": "x", "isi_included": True, "landing_url": "u"})
        assert cr.status_code == 200
        assert client.post(f"/api/full/creatives/{cr.json()['id']}/review", headers=auth(trader["access_token"]),
                           json={"decision": "approved", "notes": "n"}).status_code == 403

    def test_non_admin_cannot_manage_users(self, trader):
        assert client.get("/api/full/users", headers=auth(trader["access_token"])).status_code == 403

    def test_unauthenticated_rejected(self):
        assert client.get("/api/full/overview").status_code == 401


# ---------------------------------------------------------------------------
# Bid engine
# ---------------------------------------------------------------------------
class TestBidder:
    def test_bidstream_filters_and_persistence(self, admin, campaign):
        lid = campaign["line_items"][0]["id"]
        client.post(f"/api/full/frequency/state/{lid}/reset", headers=auth(admin["access_token"]))
        run1 = client.post("/api/full/bidstream/simulate", headers=auth(admin["access_token"]),
                           json={"line_item_id": lid, "requests": 1500, "seed": 7, "phi_leak_rate": 0.05}).json()
        assert run1["carried_over_users"] == 0 and run1["persisted_users"] > 0
        assert run1["phi_blocked"] > 0 and run1["ivt_filtered"] >= 0
        run2 = client.post("/api/full/bidstream/simulate", headers=auth(admin["access_token"]),
                           json={"line_item_id": lid, "requests": 1500, "seed": 7, "phi_leak_rate": 0.05}).json()
        assert run2["carried_over_users"] > 0
        assert run2["frequency_capped"] >= run1["frequency_capped"]

    def test_blocklisted_partner_excluded(self, admin, campaign):
        lid = campaign["line_items"][0]["id"]
        item = client.post("/api/full/supply-blocklist", headers=auth(admin["access_token"]),
                           json={"value": "Magnite", "kind": "partner", "reason": "test"}).json()
        sim = client.post("/api/full/bidstream/simulate", headers=auth(admin["access_token"]),
                          json={"line_item_id": lid, "requests": 1000, "seed": 2}).json()
        assert sim["brand_safety_blocked"] > 0
        assert not any(p["partner"] == "Magnite" for p in sim["by_partner"])
        client.request("DELETE", f"/api/full/supply-blocklist/{item['id']}", headers=auth(admin["access_token"]))

    def test_rtb_bid_and_no_bid(self, admin, campaign):
        lid = campaign["line_items"][0]["id"]
        ok = client.post(f"/api/full/rtb/bid?line_item_id={lid}", headers=auth(admin["access_token"]),
                         json={"id": "t1", "imp": [{"id": "1", "bidfloor": 4.0, "banner": {"w": 300, "h": 250}}],
                               "device": {"geo": {"country": "USA"}}, "user": {"consent": True}})
        assert ok.status_code == 200
        bid = ok.json()["seatbid"][0]["bid"][0]
        assert bid["price"] > 0 and "${AUCTION_PRICE}" in bid["nurl"]
        assert client.get(f"/api/full/rtb/win?wid={bid['id']}&price={bid['price']}").status_code == 200
        nobid = client.post(f"/api/full/rtb/bid?line_item_id={lid}", headers=auth(admin["access_token"]),
                            json={"id": "t2", "imp": [{"id": "1", "bidfloor": 4.0}],
                                  "device": {"geo": {"country": "CAN"}}, "user": {"consent": True}})
        assert nobid.status_code == 204

    def test_targeting_validation(self, admin, campaign):
        lid = campaign["line_items"][0]["id"]
        assert client.put(f"/api/full/line-items/{lid}/targeting", headers=auth(admin["access_token"]),
                          json={"devices": ["hologram"]}).status_code == 400
        ok = client.put(f"/api/full/line-items/{lid}/targeting", headers=auth(admin["access_token"]),
                        json={"devices": [], "geos": [], "dayparts": [], "brand_safety": "standard", "viewability_target": 0.0})
        assert ok.status_code == 200


# ---------------------------------------------------------------------------
# Measurement statistics
# ---------------------------------------------------------------------------
class TestMeasurement:
    def test_power_and_closed_loop(self, admin, campaign):
        plan = client.post("/api/full/measurement/plan", headers=auth(admin["access_token"]), json={
            "campaign_id": campaign["campaign_id"], "study_type": "script_lift", "baseline_rate": 0.02,
            "expected_lift_pct": 15, "exposed_size": 80000, "control_size": 80000}).json()
        assert 0.9 < plan["power"] <= 1.0 and plan["readiness"] == "ready"
        sig = client.post(f"/api/full/measurement/{plan['id']}/results", headers=auth(admin["access_token"]), json={
            "exposed_n": 80000, "exposed_conversions": 1840, "control_n": 80000, "control_conversions": 1600,
            "media_spend": 250000, "rx_value_per_conversion": 3000}).json()
        assert sig["significant"] is True and sig["incremental_conversions"] == 240
        null = client.post(f"/api/full/measurement/{plan['id']}/results", headers=auth(admin["access_token"]), json={
            "exposed_n": 80000, "exposed_conversions": 1600, "control_n": 80000, "control_conversions": 1600,
            "media_spend": 250000}).json()
        assert null["significant"] is False

    def test_underpowered_design_flagged(self, admin, campaign):
        plan = client.post("/api/full/measurement/plan", headers=auth(admin["access_token"]), json={
            "campaign_id": campaign["campaign_id"], "study_type": "script_lift", "baseline_rate": 0.02,
            "expected_lift_pct": 3, "exposed_size": 2000, "control_size": 2000}).json()
        assert plan["readiness"] == "underpowered"


# ---------------------------------------------------------------------------
# VAST + brand safety
# ---------------------------------------------------------------------------
class TestQualityControls:
    def test_vast_validation(self, admin):
        h = auth(admin["access_token"])
        assert client.post("/api/full/vast-tags/validate", headers=h, json={"vast_url": "https://a/v.xml"}).json()["valid"] is True
        assert client.post("/api/full/vast-tags/validate", headers=h, json={"vast_url": "ftp://nope"}).json()["valid"] is False
        xml = '<VAST version="4.0"><Ad><InLine><Creatives><Creative><Linear><MediaFiles><MediaFile>https://cdn/x.mp4</MediaFile></MediaFiles></Linear></Creative></Creatives></InLine></Ad></VAST>'
        result = client.post("/api/full/vast-tags/validate", headers=h, json={"vast_xml": xml}).json()
        assert result["valid"] is True and result["version"] == "4.0" and result["media_files"]

    def test_brand_safety_category_validation(self, admin):
        h = auth(admin["access_token"])
        assert client.put("/api/full/brand-safety", headers=h,
                          json={"blocked_categories": ["not_a_category"], "sensitivity": "standard"}).status_code == 400
        ok = client.put("/api/full/brand-safety", headers=h,
                        json={"blocked_categories": ["adult", "gambling"], "sensitivity": "pharma_sensitive"})
        assert ok.status_code == 200 and ok.json()["config"]["sensitivity"] == "pharma_sensitive"

    def test_ivt_report(self, admin):
        report = client.get("/api/full/ivt/report", headers=auth(admin["access_token"])).json()
        assert 0 < report["avg_valid_rate"] <= 100 and len(report["by_partner"]) >= 5


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------
class TestUsers:
    def test_create_login_delete(self, admin):
        h = auth(admin["access_token"])
        created = client.post("/api/full/users", headers=h, json={
            "email": "pytest@pharmasignal.local", "name": "Pytest User", "role": "analyst", "password": "secret123"})
        assert created.status_code == 200
        assert login("pytest@pharmasignal.local", "secret123")["user"]["role"] == "analyst"
        assert client.post("/api/full/users", headers=h, json={
            "email": "pytest@pharmasignal.local", "name": "Dup", "role": "trader", "password": "secret123"}).status_code == 400
        assert client.request("DELETE", f"/api/full/users/{created.json()['id']}", headers=h).json()["deleted"] is True

    def test_cannot_delete_self(self, admin):
        assert client.request("DELETE", f"/api/full/users/{admin['user']['id']}", headers=auth(admin["access_token"])).status_code == 400
