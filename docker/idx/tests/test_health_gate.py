#!/usr/bin/env python3
"""
R-002: Unit test for health gate.
Tests system_healthy() with mocks. API key optional (only for auth tests).
"""
import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')
API_KEY = os.environ.get("DASHBOARD_API_KEY", "")

_test_cache = {}
_test_tapi = {}
_mock_db_ok = False

def mock_get(k): return _test_cache.get(k)
def mock_set(k, v): _test_cache[k] = v
def mock_tapi(m): return _test_tapi.get(m)

import app
app._get = mock_get
app._set = mock_set
app.tapi_request = mock_tapi

class MockCur:
    def fetchone(self): return {"c": 510}

_mock_db_called = []
def mock_db(sql):
    _mock_db_called.append(sql[:30])
    if "SELECT 1" in sql:
        if _mock_db_ok: return True
        raise Exception("MySQL not configured")
    if "COUNT" in sql:
        return MockCur()
    raise Exception(f"Unknown SQL: {sql[:50]}")
app.db_exec = mock_db

passed = 0; failed = 0

def test(name, fn):
    global passed, failed
    _test_cache.clear(); _test_tapi.clear()
    global _mock_db_ok; _mock_db_ok = False
    _mock_db_called.clear()
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

# Tests
def test_no_tickers():
    i = app.system_healthy(); assert any("no tickers" in x for x in i)

def test_stale():
    mock_set("tickers", {"x":{"last":"1"}}); mock_set("age_ts", time.time()-60)
    i = app.system_healthy(); assert any("stale" in x for x in i)

def test_fresh():
    mock_set("tickers", {"x":{"last":"1"}}); mock_set("age_ts", time.time()-3)
    i = app.system_healthy(); assert not any("stale" in x for x in i)

def test_clock_skew():
    mock_set("tickers", {"x":{"last":"1"}}); mock_set("age_ts", time.time())
    mock_set("server_time", {"ts": int(time.time())-180})
    i = app.system_healthy(); assert any("clock_skew" in x for x in i)

def test_mysql_down():
    mock_set("tickers", {"x":{"last":"1"}}); mock_set("age_ts", time.time())
    i = app.system_healthy(); assert any("mysql" in x for x in i)

def test_recovery():
    mock_set("tickers", {"x":{"last":"1"}}); mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = {"orders": {"x_idr": [{"order_id":"1"}]}}
    i = app.system_healthy(); assert any("recovery" in x for x in i)

def test_recovery_fail():
    mock_set("tickers", {"x":{"last":"1"}}); mock_set("age_ts", time.time())
    _test_tapi["openOrders"] = None
    i = app.system_healthy(); assert any("recovery" in x for x in i)

def test_all_healthy():
    global _mock_db_ok
    mock_set("tickers", {"x":{"last":"1"}}); mock_set("age_ts", time.time()-2)
    _test_tapi["openOrders"] = {"orders": {}}
    _mock_db_ok = True
    i = app.system_healthy()
    non_mysql = [x for x in i if "mysql" not in x]
    assert len(non_mysql) == 0, f"Got issues: {non_mysql}"

# Run
tests = [test_no_tickers, test_stale, test_fresh, test_clock_skew,
         test_mysql_down, test_recovery, test_recovery_fail, test_all_healthy]
for fn in tests: test(fn.__doc__ or fn.__name__, fn)

print(f"\n{'='*40}")
print(f"Total: {passed} passed, {failed} failed")
print(f"{'='*40}")
sys.exit(0 if failed == 0 else 1)
