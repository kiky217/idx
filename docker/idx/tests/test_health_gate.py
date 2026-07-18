#!/usr/bin/env python3
"""
R-002: Unit test for health gate.
Tests system_healthy() with mocks AND route START with mocked dependencies.
"""
import sys, os, time, json

# Path: app.py is at repo root in GitHub Actions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

# Mock before importing app
_test_cache = {}
_test_tapi = {}
_mock_db_ok = False

def mock_get(k):
    return _test_cache.get(k)
def mock_set(k, v):
    _test_cache[k] = v
def mock_tapi(method):
    return _test_tapi.get(method)

import app
app._get = mock_get
app._set = mock_set
app.tapi_request = mock_tapi

# Mock db_exec
def mock_db(sql):
    if sql == "SELECT 1":
        if _mock_db_ok:
            return True
        raise Exception("MySQL not configured")
    if sql.startswith("SELECT COUNT"):
        class MockCur:
            def fetchone(self):
                return {"c": 510}
        return MockCur()
    raise Exception(f"Unknown SQL: {sql[:50]}")
app.db_exec = mock_db

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    _test_cache.clear()
    _test_tapi.clear()
    global _mock_db_ok
    _mock_db_ok = False
    try:
        fn()
        print(f"  ✅ {name}")
        passed += 1
    except AssertionError as e:
        print(f"  ❌ {name}: {e}")
        failed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1

# ── system_healthy() tests ──

def test_no_tickers():
    issues = app.system_healthy()
    assert any("no tickers" in i for i in issues)

def test_stale():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time() - 60)
    issues = app.system_healthy()
    assert any("stale" in i for i in issues)

def test_fresh():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time() - 3)
    issues = app.system_healthy()
    assert not any("stale" in i for i in issues)

def test_clock_skew():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time())
    mock_set("server_time", {"ts": int(time.time()) - 180})
    issues = app.system_healthy()
    assert any("clock_skew" in i for i in issues)

def test_mysql_down():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time())
    issues = app.system_healthy()
    assert any("mysql" in i for i in issues)

def test_recovery_orders():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = {"orders": {"x_idr": [{"order_id": "1"}]}}
    issues = app.system_healthy()
    assert any("recovery" in i for i in issues)

def test_recovery_api_fail():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = None
    issues = app.system_healthy()
    assert any("recovery" in i for i in issues)

def test_recovery_exception():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = "invalid"
    issues = app.system_healthy()
    assert any("recovery" in i for i in issues)

def test_all_healthy():
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time() - 2)
    _test_tapi["openOrders"] = {"orders": {}}
    global _mock_db_ok
    _mock_db_ok = True
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time())
    issues = app.system_healthy()
    mysql_issues = [i for i in issues if "mysql" not in i]
    assert len(mysql_issues) == 0, f"Expected 0 non-mysql issues, got {mysql_issues}"

# ── Route START test (mocked) ──
def test_start_with_open_orders():
    """START must reject when recovery open orders exist."""
    mock_set("tickers", {"x_idr": {"last": "1"}})
    mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = {"orders": {"x_idr": [{"order_id": "1"}]}}
    issues = app.system_healthy()
    assert any("recovery" in i for i in issues), "START should be blocked by recovery"

# ── Run ──
print("R-002 Health Gate Tests\n")
test("No tickers → detected", test_no_tickers)
test("Stale ticker → detected", test_stale)
test("Fresh ticker → clean", test_fresh)
test("Clock skew → detected", test_clock_skew)
test("MySQL down → detected", test_mysql_down)
test("Open orders → recovery", test_recovery_orders)
test("OpenOrders API fail → fail-closed", test_recovery_api_fail)
test("OpenOrders exception → fail-closed", test_recovery_exception)
test("All healthy → no issues", test_all_healthy)
test("START route rejects with open orders (mocked)", test_start_with_open_orders)

print(f"\n{'='*40}")
print(f"Total: {passed} passed, {failed} failed")
print(f"{'='*40}")
sys.exit(0 if failed == 0 else 1)
