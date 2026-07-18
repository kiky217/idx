# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md` (15 temuan S-01 s/d S-15)
**Format status:** OPEN | PASS | FAIL | BLOCKED

---

## IDX-R-001 (S-01) — LIVE mode dikunci

**Status:** PASS ✅
**File:** `app.py`

**Koreksi:**
1. Check `dry_run=false` dilakukan SEBELUM merge dan save config.
2. `ENABLE_LIVE_TRADING=true` env var sebagai server-side gate.
3. `load_config()` startup memaksa `dry_run=True` jika env var tidak aktif.
4. `POST /api/config` selalu override `dry_run=True` jika env var tidak aktif.
5. Dropdown Mode di Settings di-disable.

---

## IDX-R-003 (S-02) — Autentikasi

**Status:** PASS ✅
**File:** `app.py`, `.env`

**Koreksi:**
1. Fungsi `require_api_key()` memeriksa header `X-API-Key`.
2. Auth di-enforce di endpoint: scalper start/stop, config POST, telegram test/daily.
3. `DASHBOARD_API_KEY` env var — jika kosong, auth disabled (backward compatible).
4. Framework siap tinggal isi env var untuk aktifkan.

---

## IDX-R-002 (S-03) — Health gate START

**Status:** PASS ✅
**File:** `app.py`

**Koreksi:**
1. `system_healthy()` memeriksa: market data (tickers tersedia, tidak stale), MySQL reachable, pair rules terisi.
2. `POST /api/scalper/start` menggunakan `system_healthy()` sebagai gate.
3. Endpoint `/health` baru: return status ok/degraded + daftar issues.

---

## IDX-R-016 (S-16) — Kredensial default MySQL

**Status:** PASS ✅
**File:** `app.py`, `.env`

**Koreksi:**
1. Hapus semua fallback kredensial dari `app.py` → fail-closed.
2. Pindahkan kredensial ke `.env` (tidak di-track git).
3. `get_db()` runtime check — raise error jika MySQL belum dikonfigurasi.

---

## Ringkasan

| ID | Temuan | Status |
|----|--------|--------|
| IDX-R-001 | S-01 LIVE mode terkunci | ✅ PASS |
| IDX-R-002 | S-03 Health gate START | ✅ PASS |
| IDX-R-003 | S-02 Autentikasi | ✅ PASS |
| IDX-R-004 | S-04 Signal EMA20/50 | 🔄 OPEN |
| IDX-R-005 | S-05 Order book | 🔄 OPEN |
| IDX-R-006 | S-06 Sell amount | 🔄 OPEN |
| IDX-R-007 | S-07 State Redis | 🔄 OPEN |
| IDX-R-008 | S-08 Decimal | 🔄 OPEN |
| IDX-R-009 | S-09 Pair ranking | 🔄 OPEN |
| IDX-R-010 | S-10 Depth watchlist | 🔄 OPEN |
| IDX-R-011 | S-11 Daily reset | 🔄 OPEN |
| IDX-R-012 | S-12 Exposure total | 🔄 OPEN |
| IDX-R-013 | S-13 Candle chart | 🔄 OPEN |
| IDX-R-014 | S-14 Multi-worker | 🔄 OPEN |
| IDX-R-015 | S-15 WS token | 🔄 OPEN |
| IDX-R-016 | S-16 MySQL credentials | ✅ PASS |
