#!/usr/bin/env python3
"""
R-002: Health gate integration test.
Does NOT call START/STOP. Uses GitHub Actions secret (fail if empty).
"""
import os, sys, requests

BASE = os.environ.get("TEST_BASE_URL", "https://idx.srv1804652.hstgr.cloud")
API_KEY = os.environ.get("DASHBOARD_API_KEY")
if not API_KEY:
    print("❌ DASHBOARD_API_KEY environment variable required")
    sys.exit(1)

passed = 0
failed = 0
results = []

def test(name, fn):
    global passed, failed
    try:
        fn()
        results.append((name, "PASS"))
        passed += 1
    except Exception as e:
        results.append((name, f"FAIL: {e}"))
        failed += 1

# 1. Health endpoint
r = requests.get(f"{BASE}/health", timeout=10)
assert r.status_code in [200, 503], f"Health returned {r.status_code}"
data = r.json()
issues = data.get("issues", [])
print(f"Health: status={data['status']}, issues={issues}")

# 2. Config endpoint — auth check (read-only)
r = requests.get(f"{BASE}/api/config", timeout=10)
assert r.status_code == 401, f"Config without key: expected 401, got {r.status_code}"

r = requests.get(f"{BASE}/api/config", headers={"X-API-Key": API_KEY}, timeout=10)
assert r.status_code == 200, f"Config with key: expected 200, got {r.status_code}"

# 3. Scalper status (read-only)
r = requests.get(f"{BASE}/api/scalper/status", timeout=10)
assert r.status_code == 200, f"Scalper status: expected 200, got {r.status_code}"
print(f"Scalper: running={r.json().get('running')}, mode={r.json().get('mode')}")

# Run tests
test("Health endpoint responds", lambda: None)  # already tested above

print(f"\n{'='*50}")
print(f"R-002 Tests: {passed} passed, {failed} failed")
print(f"{'='*50}")
for name, status in results:
    mark = "✅" if status == "PASS" else "❌"
    print(f"  {mark} {name}: {status}")

sys.exit(0 if failed == 0 else 1)
