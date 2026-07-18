#!/usr/bin/env python3
"""
R-002: Unit test for system_healthy() with mocked dependencies.
Tests all conditions without touching production.
"""
import sys, os, time, json
from unittest.mock import patch, MagicMock

# Mock database and cache before importing app
sys.path.insert(0, '/docker/idx')

# Mock _get/_set
_test_cache = {}
def mock_get(k):
    return _test_cache.get(k)
def mock_set(k, v):
    _test_cache[k] = v

# Mock tapi_request
_test_tapi = {}
def mock_tapi(method):
    return _test_tapi.get(method)

import app
app._get = mock_get
app._set = mock_set
app.tapi_request = mock_tapi
app.db_exec = MagicMock(side_effect=Exception("MySQL mocked down"))

passed = 0
failed = 0

def test(name, fn):
    global passed, failed
    _test_cache.clear()
    _test_tapi.clear()
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

# ── Tests ──

def test_no_tickers():
    issues = app.system_healthy()
    assert any("no tickers" in i for i in issues), f"Expected no tickers, got {issues}"

def test_stale_tickers():
    mock_set("tickers", {"btc_idr": {"last": "100"}})
    mock_set("age_ts", time.time() - 60)
    issues = app.system_healthy()
    assert any("stale" in i for i in issues), f"Expected stale, got {issues}"

def test_fresh_tickers():
    mock_set("tickers", {"btc_idr": {"last": "100"}})
    mock_set("age_ts", time.time() - 5)
    issues = app.system_healthy()
    assert not any("stale" in i for i in issues), f"Unexpected stale, got {issues}"

def test_clock_skew():
    mock_set("tickers", {"btc_idr": {"last": "100"}})
    mock_set("age_ts", time.time())
    mock_set("server_time", {"ts": int(time.time()) - 180})
    issues = app.system_healthy()
    assert any("clock_skew" in i for i in issues), f"Expected clock skew, got {issues}"

def test_mysql_down():
    mock_set("tickers", {"btc_idr": {"last": "100"}})
    mock_set("age_ts", time.time())
    app.db_exec = MagicMock(side_effect=Exception("MySQL unreachable"))
    issues = app.system_healthy()
    assert any("mysql" in i for i in issues), f"Expected mysql issue, got {issues}"

def test_recovery_open_orders():
    mock_set("tickers", {"btc_idr": {"last": "100"}})
    mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = {"orders": {"btc_idr": [{"order_id": "1"}]}}
    issues = app.system_healthy()
    assert any("recovery" in i for i in issues), f"Expected recovery, got {issues}"

def test_recovery_api_fail():
    mock_set("tickers", {"btc_idr": {"last": "100"}})
    mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = None
    issues = app.system_healthy()
    assert any("recovery" in i for i in issues), f"Expected recovery fail-closed, got {issues}"

def test_all_healthy():
    mock_set("tickers", {"btc_idr": {"last": "100"}})
    mock_set("age_ts", time.time() - 2)
    _test_tapi["openOrders"] = {"orders": {}}
    app.db_exec = MagicMock(return_value=MagicMock(fetchone=lambda: {"c": 510}))
    issues = [i for i in app.system_healthy() if "mysql" not in i]
    assert len(issues) == 0, f"Expected 0 issues (excl mysql), got {issues}"

# ── Run ──
print("R-002 Health Gate Unit Tests\n")
test("No tickers → issue detected", test_no_tickers)
test("Stale ticker >30s → issue detected", test_stale_tickers)
test("Fresh ticker → no stale issue", test_fresh_tickers)
test("Clock skew >120s → issue detected", test_clock_skew)
test("MySQL unreachable → issue detected", test_mysql_down)
test("Open orders → recovery issue", test_recovery_open_orders)
test("OpenOrders API fail → fail-closed", test_recovery_api_fail)
test("All conditions healthy → no issues", test_all_healthy)

print(f"\n{'='*40}")
print(f"Total: {passed} passed, {failed} failed")
print(f"{'='*40}")
sys.exit(0 if failed == 0 else 1)
