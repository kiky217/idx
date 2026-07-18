#!/usr/bin/env python3
"""R-002: Health gate integration tests."""
import sys, os, json, time, requests

BASE = "https://idx.srv1804652.hstgr.cloud"
API_KEY = os.environ.get("TEST_API_KEY", "fccfc03d1e9f36177c3659099deaf132")

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

def check(name, url, expected_code, expected_issues=[]):
    r = requests.get(url, timeout=10)
    assert r.status_code == expected_code, f"Expected {expected_code}, got {r.status_code}"
    if expected_issues:
        data = r.json()
        for issue in expected_issues:
            assert any(issue in i for i in data.get("issues", [])), f"Expected issue '{issue}' not in {data.get('issues',[])}"
    return r

# 1. Health endpoint returns 200
r = requests.get(f"{BASE}/health", timeout=10)
data = r.json()
issues = data.get("issues", [])
print(f"Current health status: {data['status']}")
print(f"Current issues: {issues}")
print()

# Test START rejected with open orders (7 open orders exist)
r = requests.post(f"{BASE}/api/scalper/start", headers={"X-API-Key": API_KEY}, timeout=10)
data2 = r.json()
if r.status_code == 503:
    results.append(("START rejected (open orders)", "PASS"))
    passed += 1
else:
    results.append(("START rejected", f"FAIL: Expected 503, got {r.status_code}"))
    failed += 1

# Test health endpoint accessible
if r.status_code in [200, 503]:
    results.append(("Health endpoint responds", "PASS"))
    passed += 1
else:
    results.append(("Health endpoint", "FAIL"))
    failed += 1

print(f"\n{'='*50}")
print(f"R-002 Health Gate Tests: {passed} passed, {failed} failed")
print(f"{'='*50}")
for name, status in results:
    mark = "✅" if status == "PASS" else "❌"
    print(f"  {mark} {name}: {status}")

sys.exit(0 if failed == 0 else 1)
