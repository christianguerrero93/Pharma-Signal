"""PharmaSignal DSP backend API tests — Iteration 3 (with JWT auth & RBAC)."""
import io
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "admin": ("admin@pharmasignal.io", "Admin@2026"),
    "trader": ("trader@pharmasignal.io", "Trader@2026"),
    "analyst": ("analyst@pharmasignal.io", "Analyst@2026"),
    "vendor": ("vendor@pulsepoint.com", "Vendor@2026"),
}


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def tokens():
    s = requests.Session()
    out = {}
    for role, (email, pw) in CREDS.items():
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
        if r.status_code != 200:
            pytest.skip(f"Cannot login {role}: {r.status_code} {r.text}")
        out[role] = r.json()["access_token"]
    return out


def auth_session(token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def admin_sess(tokens):
    return auth_session(tokens["admin"])


@pytest.fixture(scope="session")
def trader_sess(tokens):
    return auth_session(tokens["trader"])


@pytest.fixture(scope="session")
def analyst_sess(tokens):
    return auth_session(tokens["analyst"])


@pytest.fixture(scope="session")
def vendor_sess(tokens):
    return auth_session(tokens["vendor"])


# ---------- Health ----------
class TestHealth:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------- Auth (NEW) ----------
class TestAuth:
    def test_login_admin_ok(self, session):
        r = session.post(f"{API}/auth/login", json={
            "email": "admin@pharmasignal.io", "password": "Admin@2026"})
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d and isinstance(d["access_token"], str) and len(d["access_token"]) > 20
        u = d["user"]
        for k in ["id", "email", "name", "role", "vendor_scope"]:
            assert k in u
        assert u["email"] == "admin@pharmasignal.io"
        assert u["role"] == "admin"

    def test_login_wrong_password(self, session):
        r = session.post(f"{API}/auth/login", json={
            "email": "admin@pharmasignal.io", "password": "WRONG"})
        assert r.status_code == 401

    def test_me_without_token(self, session):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_with_token(self, admin_sess):
        r = admin_sess.get(f"{API}/auth/me")
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == "admin@pharmasignal.io"
        assert "password_hash" not in u

    def test_users_list_admin_only(self, admin_sess, analyst_sess, trader_sess, vendor_sess):
        for s in (analyst_sess, trader_sess, vendor_sess):
            assert s.get(f"{API}/auth/users").status_code == 403
        r = admin_sess.get(f"{API}/auth/users")
        assert r.status_code == 200
        users = r.json()
        assert len(users) >= 4
        for u in users:
            assert "password_hash" not in u

    def test_create_user_and_dup(self, admin_sess):
        payload = {
            "email": "test_newuser_iter3@pharmasignal.io",
            "password": "TestPW@2026",
            "name": "TEST_New",
            "role": "analyst",
        }
        r = admin_sess.post(f"{API}/auth/users", json=payload)
        # Could be 200 (first run) or 400 (already exists from prior run)
        assert r.status_code in (200, 400)
        # Duplicate
        r2 = admin_sess.post(f"{API}/auth/users", json=payload)
        assert r2.status_code == 400


# ---------- Role Guards (NEW) ----------
class TestRoleGuards:
    def test_campaigns_create_matrix(self, admin_sess, trader_sess, analyst_sess, vendor_sess):
        payload = {
            "name": "TEST_RBAC_Camp", "brand": "RBACBrand",
            "indication": "Type 2 Diabetes", "campaign_type": "DTC",
            "budget": 50000, "flight_start": "2026-02-01", "flight_end": "2026-04-30",
        }
        assert analyst_sess.post(f"{API}/campaigns", json=payload).status_code == 403
        assert vendor_sess.post(f"{API}/campaigns", json=payload).status_code == 403
        r_t = trader_sess.post(f"{API}/campaigns", json=payload)
        assert r_t.status_code == 200
        r_a = admin_sess.post(f"{API}/campaigns", json={**payload, "name": "TEST_RBAC_Camp_admin"})
        assert r_a.status_code == 200

    def test_campaign_patch_matrix(self, admin_sess, trader_sess, analyst_sess, vendor_sess):
        camps = admin_sess.get(f"{API}/campaigns").json()
        cid = camps[0]["id"]
        body = {"status": "Active"}
        assert analyst_sess.patch(f"{API}/campaigns/{cid}", json=body).status_code == 403
        assert vendor_sess.patch(f"{API}/campaigns/{cid}", json=body).status_code == 403
        assert trader_sess.patch(f"{API}/campaigns/{cid}", json=body).status_code == 200
        assert admin_sess.patch(f"{API}/campaigns/{cid}", json=body).status_code == 200

    def test_upload_requires_admin_or_trader(self, analyst_sess, vendor_sess):
        files = {"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")}
        # multipart -- need to remove content-type header
        s = requests.Session()
        s.headers.update({"Authorization": analyst_sess.headers["Authorization"]})
        assert s.post(f"{API}/upload/pmps", files=files).status_code == 403
        s.headers["Authorization"] = vendor_sess.headers["Authorization"]
        files = {"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")}
        assert s.post(f"{API}/upload/pmps", files=files).status_code == 403

    def test_shares_requires_admin_or_trader(self, analyst_sess, vendor_sess, trader_sess):
        body = {"vendor": "PulsePoint", "expires_in_days": 7}
        assert analyst_sess.post(f"{API}/shares/vendor", json=body).status_code == 403
        assert vendor_sess.post(f"{API}/shares/vendor", json=body).status_code == 403
        assert trader_sess.post(f"{API}/shares/vendor", json=body).status_code == 200

    def test_creative_patch_role(self, admin_sess, trader_sess, analyst_sess, vendor_sess):
        cs = admin_sess.get(f"{API}/creatives").json()
        cid = cs[0]["id"]
        body = {"reviewer_notes": "TEST_rbac"}
        assert trader_sess.patch(f"{API}/creatives/{cid}", json=body).status_code == 403
        assert vendor_sess.patch(f"{API}/creatives/{cid}", json=body).status_code == 403
        assert analyst_sess.patch(f"{API}/creatives/{cid}", json=body).status_code == 200
        assert admin_sess.patch(f"{API}/creatives/{cid}", json=body).status_code == 200

    def test_reseed_admin_only(self, admin_sess, trader_sess, analyst_sess, vendor_sess):
        for s in (trader_sess, analyst_sess, vendor_sess):
            assert s.post(f"{API}/admin/reseed").status_code == 403
        # don't actually reseed to avoid disrupting other tests state — verify admin can call but
        # we test unauth without admin call
        # Optionally check admin reseed works (returns ok) — keep it
        r = admin_sess.post(f"{API}/admin/reseed")
        assert r.status_code == 200


# ---------- Frequency Intelligence (NEW) ----------
class TestFrequency:
    def test_requires_auth(self, session):
        r = session.get(f"{API}/frequency-intelligence")
        assert r.status_code == 401

    def test_returns_distribution(self, analyst_sess):
        r = analyst_sess.get(f"{API}/frequency-intelligence")
        assert r.status_code == 200
        d = r.json()
        assert "rows" in d and "summary" in d
        for k in ["total_hcp_lists", "critical", "high", "moderate", "healthy"]:
            assert k in d["summary"]
        # Should not be all-critical
        risks = {r["risk"] for r in d["rows"]}
        assert len(risks) >= 2, f"Risk distribution too flat: {risks}"
        # Row fields
        if d["rows"]:
            r0 = d["rows"][0]
            for k in ["campaign_id", "audience_id", "audience_size", "frequency_cap",
                     "weekly_impressions_per_hcp", "saturation_pct", "risk", "recommendation"]:
                assert k in r0


# ---------- Shares CRUD + Public (NEW) ----------
class TestShares:
    def test_share_lifecycle_and_public(self, trader_sess, session):
        # create
        r = trader_sess.post(f"{API}/shares/vendor",
                              json={"vendor": "PulsePoint", "expires_in_days": 7})
        assert r.status_code == 200
        d = r.json()
        for k in ["id", "token", "vendor", "expires_at", "created_at"]:
            assert k in d
        sid, token = d["id"], d["token"]

        # list
        lst = trader_sess.get(f"{API}/shares/vendor").json()
        assert any(x["id"] == sid for x in lst)

        # public read without auth
        pub = requests.get(f"{API}/public/shares/vendor/{token}")
        assert pub.status_code == 200
        pd = pub.json()
        assert "vendor" in pd and "deals" in pd
        assert "expires_at" in pd

        # invalid token -> 404
        bad = requests.get(f"{API}/public/shares/vendor/notarealtoken123")
        assert bad.status_code == 404

        # revoke
        rev = trader_sess.delete(f"{API}/shares/vendor/{sid}")
        assert rev.status_code == 200
        # after revoke public lookup should 404
        pub2 = requests.get(f"{API}/public/shares/vendor/{token}")
        assert pub2.status_code == 404

    def test_expired_share_returns_410(self, admin_sess):
        # Create a share, then directly age it via reseed/admin? We cannot mutate expiry through API.
        # Instead, create with 0 days and check immediately (expires_at == now-ish; may be in past).
        r = admin_sess.post(f"{API}/shares/vendor",
                            json={"vendor": "PulsePoint", "expires_in_days": 0})
        assert r.status_code == 200
        token = r.json()["token"]
        # request public — expires_at is "now" so just-past
        import time; time.sleep(1)
        pub = requests.get(f"{API}/public/shares/vendor/{token}")
        assert pub.status_code == 410


# ---------- Existing endpoints (regression with auth where needed) ----------
class TestDashboard:
    def test_overview(self, session):
        r = session.get(f"{API}/dashboard/overview")
        assert r.status_code == 200
        d = r.json()
        for k in ["total_budget", "active_campaigns", "working_media_pct",
                  "verified_reach_pct", "avg_supply_score"]:
            assert k in d["kpis"]


class TestCampaigns:
    def test_list_seeded(self, session):
        r = session.get(f"{API}/campaigns")
        assert r.status_code == 200
        camps = r.json()
        assert len(camps) >= 7

    def test_create_persists(self, trader_sess, session):
        payload = {
            "name": "TEST_CampaignIter3", "brand": "TestBrand",
            "indication": "Type 2 Diabetes", "campaign_type": "DTC",
            "budget": 100000, "flight_start": "2026-02-01", "flight_end": "2026-04-30",
            "outcome_kpi": "Script Lift", "channels": ["Display"],
        }
        r = trader_sess.post(f"{API}/campaigns", json=payload)
        assert r.status_code == 200
        names = [x["name"] for x in session.get(f"{API}/campaigns").json()]
        assert "TEST_CampaignIter3" in names


class TestAudiences:
    def test_list(self, session):
        r = session.get(f"{API}/audiences")
        assert r.status_code == 200
        assert len(r.json()) == 8


class TestPMPs:
    def test_list_sorted(self, session):
        r = session.get(f"{API}/pmps")
        assert r.status_code == 200
        pmps = r.json()
        assert len(pmps) == 8
        scores = [p["outcome_adjusted_score"] for p in pmps]
        assert scores == sorted(scores, reverse=True)


class TestVendors:
    def test_list(self, session):
        r = session.get(f"{API}/vendors")
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestRTB:
    def test_simulate(self, session):
        r = session.post(f"{API}/rtb/simulate", json={
            "outcome_probability": 0.7, "audience_quality_score": 0.8,
            "supply_quality_score": 0.75, "rx_lift_weight": 1.2,
            "engagement_quality": 0.65, "data_cost_multiplier": 1.3, "base_value": 12.0,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["decision"] in ("BID", "LOW_BID", "NO_BID")
        assert len(d["stream"]) == 24


class TestUpload:
    def test_upload_invalid_schema_rejected(self, trader_sess):
        s = requests.Session()
        s.headers.update({"Authorization": trader_sess.headers["Authorization"]})
        files = {"file": ("test.csv", io.BytesIO(b"vendor,score\nA,88\n"), "text/csv")}
        r = s.post(f"{API}/upload/pmps", files=files)
        assert r.status_code == 400

    def test_upload_valid_script_lift(self, trader_sess):
        s = requests.Session()
        s.headers.update({"Authorization": trader_sess.headers["Authorization"]})
        csv_text = (
            "week,exposed_rx_index,control_rx_index,lift_pct\n"
            "TEST_W1,101.2,100.1,1.1\nTEST_W2,103.5,100.5,2.99\n"
        )
        files = {"file": ("sl.csv", io.BytesIO(csv_text.encode()), "text/csv")}
        r = s.post(f"{API}/upload/script_lift", files=files)
        assert r.status_code == 200
        assert r.json()["rows_inserted"] == 2


class TestScenarios:
    def test_crud(self, session):
        payload = {"name": "TEST_S_iter3",
                   "params": {"x": 1}, "result": {"final_bid_cpm": 1.2, "decision": "BID"}}
        r = session.post(f"{API}/scenarios", json=payload)
        assert r.status_code == 200
        sid = r.json()["id"]
        d = session.delete(f"{API}/scenarios/{sid}")
        assert d.status_code == 200


class TestCreatives:
    def test_list_filter(self, session):
        camps = session.get(f"{API}/campaigns").json()
        cid = [c for c in camps if not c["name"].startswith("TEST_")][0]["id"]
        r = session.get(f"{API}/creatives", params={"campaign_id": cid})
        assert r.status_code == 200
