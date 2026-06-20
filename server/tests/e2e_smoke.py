"""End-to-end smoke test against a running server + real MongoDB.

Exercises the full authenticated flow over HTTP:
  register -> read OTP from DB -> verify-otp (JWT) -> /auth/me
  -> watchlist add/list/delete -> portfolio add/list/delete
  -> profile get/update -> alerts run-now -> delete account (cleanup)

Run:  ./.venv/Scripts/python.exe tests/e2e_smoke.py
Requires the server running on :8000 and a reachable MONGO_URI.
"""
import json
import sys
import time
import urllib.request

sys.path.insert(0, ".")
from config.settings import settings  # noqa: E402
from pymongo import MongoClient  # noqa: E402

BASE = "http://127.0.0.1:8000"
EMAIL = f"e2e{int(time.time())}@stocksense-qa.dev"
PASSWORD = "Sup3rStr0ng!Pass"

passed = 0
failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {extra}")


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=45)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


print(f"E2E user: {EMAIL}\n")

# 1. Register
st, res = call("POST", "/auth/register", {"email": EMAIL, "password": PASSWORD, "name": "E2E"})
check("register -> 200", st == 200, f"got {st} {res}")

# 2. Read OTP straight from Mongo
mc = MongoClient(settings.MONGO_URI)
otp_doc = mc[settings.MONGO_DB_NAME]["otp_verification"].find_one({"email": EMAIL})
check("OTP stored in DB", bool(otp_doc and otp_doc.get("otp")))
otp = otp_doc["otp"] if otp_doc else "000000"

# 3. Verify OTP -> token
st, res = call("POST", "/auth/verify-otp", {"email": EMAIL, "otp": otp})
check("verify-otp -> 200 + token", st == 200 and bool(res.get("token")), f"got {st} {res}")
token = res.get("token")

# 4. /auth/me
st, res = call("GET", "/auth/me", token=token)
check("auth/me returns user", st == 200 and res.get("user", {}).get("email") == EMAIL, f"got {st}")

# 5. Watchlist add/list/delete
st, res = call("POST", "/api/watchlist", {"symbol": "AAPL", "threshold_pct": 5}, token=token)
check("watchlist add -> 200", st == 200 and res.get("id"), f"got {st} {res}")
wl_id = res.get("id")
st, res = call("GET", "/api/watchlist", token=token)
check("watchlist list shows AAPL", st == 200 and any(i["symbol"] == "AAPL" for i in res.get("items", [])))
st, res = call("DELETE", f"/api/watchlist/{wl_id}", token=token)
check("watchlist delete -> 200", st == 200, f"got {st} {res}")

# 6. Portfolio add/list/delete
st, res = call("POST", "/api/portfolio",
               {"symbol": "MSFT", "quantity": 10, "buy_price": 300, "buy_date": "2025-01-15"}, token=token)
check("portfolio add -> 200", st == 200 and res.get("id"), f"got {st} {res}")
pf_id = res.get("id")
st, res = call("GET", "/api/portfolio", token=token)
check("portfolio list + totals", st == 200 and "totals" in res and any(i["symbol"] == "MSFT" for i in res.get("items", [])))
st, res = call("DELETE", f"/api/portfolio/{pf_id}", token=token)
check("portfolio delete -> 200", st == 200, f"got {st} {res}")

# 7. Profile get/update
st, res = call("GET", "/api/profile", token=token)
check("profile get", st == 200 and res.get("profile", {}).get("email") == EMAIL)
st, res = call("PUT", "/api/profile", {"name": "E2E Updated", "alert_threshold_pct": 7.5}, token=token)
check("profile update -> 200", st == 200, f"got {st} {res}")

# 8. Alerts run-now
st, res = call("POST", "/api/alerts/run-now", token=token)
check("alerts run-now returns summary", st == 200 and "summary" in res, f"got {st}")

# 9. Auth guard: no token => 401
st, res = call("GET", "/api/watchlist")
check("unauth watchlist -> 401", st == 401, f"got {st}")

# 10. Cleanup: delete account
st, res = call("DELETE", "/api/profile", token=token)
check("delete account (cleanup) -> 200", st == 200, f"got {st} {res}")
leftover = mc[settings.MONGO_DB_NAME]["users"].find_one({"email": EMAIL})
check("user removed from DB", leftover is None)

print(f"\n==== {passed} passed, {failed} failed ====")
sys.exit(1 if failed else 0)
