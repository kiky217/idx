# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Status:** Aktif
**Acuan:** `audit_idx_1.md` (15 temuan S-01 s/d S-15)

---

## S-01 — LIVE mode dikunci

**Status:** ✅ FIXED
**File:** `app.py`
**Temuan:** Config API dapat mengubah `DRY_RUN` → `LIVE` melalui POST `/api/config` dengan `{"scalper":{"dry_run":false}}`.

**Koreksi:**
1. Route `POST /api/config` sekarang menolak `dry_run=false` dengan HTTP 403 dan pesan error.
2. LIVE mode hanya bisa diaktifkan via env var `ENABLE_LIVE_TRADING=true`.
3. Dropdown Mode di Settings tab di-disable, hanya menampilkan "DRY RUN".

**Kode:**
```python
if not sc["dry_run"]:
    return jsonify({"error": "LIVE mode is disabled. Set ENABLE_LIVE_TRADING=true in environment to enable."}), 403
```

**Verifikasi:**
```bash
curl -X POST /api/config -d '{"scalper":{"dry_run":false}}'
# → 403 "LIVE mode is disabled"
```

---

## S-03 — Health gate START

**Status:** ✅ FIXED
**File:** `app.py`
**Temuan:** Tombol START aktif meski data market belum siap (pairs loading, ticker kosong).

**Koreksi:**
1. Route `POST /api/scalper/start` sekarang memeriksa `_get("tickers")` sebelum mengizinkan start.
2. Jika ticker kosong, return 503 "Market data not ready".
3. Frontend `updateHealthStatus()` mendisable tombol START selama `scan_count` masih undefined.

**Kode:**
```python
tickers = _get("tickers")
if not tickers or len(tickers) == 0:
    return jsonify({"ok": False, "msg": "Market data not ready. Wait for ticker data."}), 503
```

**Verifikasi:**
```bash
curl -X POST /api/scalper/start
# → 503 "Market data not ready" (kalo data belum siap)
```

---

## S-02 — Autentikasi (Belum)

**Status:** ❌ BELUM
**Prioritas:** Berikutnya
**Catatan:** Dashboard masih publik. Rencana: tambah API key header check untuk semua POST endpoint.

---

## S-04 s/d S-15 (Belum)

**Status:** ❌ BELUM
**Catatan:** Menunggu prioritas setelah S-02 selesai.

---

## Ringkasan

| Temuan | Status | Prioritas |
|--------|--------|-----------|
| S-01 — LIVE mode terkunci | ✅ FIXED | 1 |
| S-03 — Health gate START | ✅ FIXED | 3 |
| S-02 — Auth | ❌ | 2 |
| S-04 — Signal EMA20/50 | ❌ | 4 |
| S-05 — Order book | ❌ | 5 |
| S-06 — Sell amount | ❌ | 6 |
| S-07 — State Redis | ❌ | 7 |
| S-08 — Decimal | ❌ | 8 |
| S-09 — 100 pair | ❌ | 9 |
| S-10 — Depth | ❌ | 10 |
| S-11 — Daily reset | ❌ | 11 |
| S-12 — Exposure | ❌ | 12 |
| S-13 — Candle chart | ❌ | 13 |
| S-14 — Multi-worker | ❌ | 14 |
| S-15 — WS token | ❌ | 15 |
