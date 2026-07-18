# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md` (15 temuan S-01 s/d S-15)
**Format status:** OPEN | PASS | FAIL | BLOCKED

---

## IDX-R-001 (S-01) — LIVE mode dikunci

**Status:** PASS ✅
**File:** `app.py`
**Temuan:** Config API dapat mengubah `DRY_RUN` → `LIVE` melalui POST `/api/config`.

**Koreksi:**
1. Route `POST /api/config` menolak `dry_run=false` dengan HTTP 403.
2. LIVE mode hanya via env `ENABLE_LIVE_TRADING=true`.
3. Dropdown Mode di Settings di-disable.

**Verifikasi:**
```bash
curl -X POST /api/config -d '{"scalper":{"dry_run":false}}'
# → 403 "LIVE mode is disabled"
```

---

## IDX-R-002 (S-03) — Health gate START

**Status:** BLOCKED ⛔
**File:** `app.py`
**Temuan:** Tombol START aktif meski data market belum siap.

**Koreksi parsial:**
1. Route START cek `_get("tickers")` — return 503 kalo kosong.
2. Frontend disable tombol selama data belum siap.

**Butuh:** Prasyarat belum terpenuhi. Health gate masih terlalu sederhana (cuma cek ticker). Idealnya: pair rules loaded, MySQL/Redis healthy, stream aktif, tidak stale, tidak ada recovery order.

---

## IDX-R-003 (S-02) — Autentikasi

**Status:** OPEN

---

## Ringkasan

| ID | Temuan | Status |
|----|--------|--------|
| IDX-R-001 | S-01 LIVE mode terkunci | ✅ PASS |
| IDX-R-002 | S-03 Health gate START | ⛔ BLOCKED |
| IDX-R-003 | S-02 Autentikasi | 🔄 OPEN |
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
