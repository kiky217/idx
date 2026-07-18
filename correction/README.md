# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md` (15 temuan S-01 s/d S-15)
**Format status:** OPEN | PASS | FAIL | BLOCKED

---

## IDX-R-001 (S-01) — LIVE mode dikunci

**Status:** PASS ✅
**File:** `app.py`
**Temuan:** Config API dapat mengubah `DRY_RUN` → `LIVE` melalui POST `/api/config`. Config tersimpan sebelum 403. `ENABLE_LIVE_TRADING` env var tidak dibaca.

**Koreksi:**
1. Check `dry_run=false` dilakukan **SEBELUM** merge dan save config.
2. Config hanya di-save setelah divalidasi.
3. `ENABLE_LIVE_TRADING=true` environment variable sebagai server-side gate.
4. `load_config()` startup memaksa `dry_run=True` jika env var tidak aktif.
5. `POST /api/config` selalu override `dry_run=True` jika env var tidak aktif.
6. Dropdown Mode di Settings di-disable.

**Verifikasi:**
```bash
# Request LIVE ditolak
curl -X POST /api/config -d '{"scalper":{"dry_run":false}}'
# → 403 "LIVE mode is disabled"

# Config tidak berubah
curl /api/config | jq .scalper.dry_run
# → true

# Load-time enforcement
# Startup selalu force dry_run=True
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

## IDX-R-016 (S-16) — Kredensial default MySQL

**Status:** PASS ✅
**File:** `app.py`, `.env`
**Temuan:** Nilai default `IDX_DB_USER=idx2026@` dan `IDX_DB_PASSWORD=idx2026@` tercantum di source publik.

**Koreksi:**
1. Hapus semua fallback kredensial dari `app.py` → fail-closed jika env var tidak ada.
2. Pindahkan kredensial ke `.env` file (tidak di-track git).
3. Tambah `get_db()` runtime check — raise error jika MySQL belum dikonfigurasi.
4. `.env` ditambahkan ke `.gitignore`.

**Verifikasi:**
```python
# Tanpa env var:
get_db() → RuntimeError("MySQL not configured")
# Dengan env var di .env:
get_db() → ✅ konek
```

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
| IDX-R-016 | S-16 MySQL credentials | ✅ PASS |
