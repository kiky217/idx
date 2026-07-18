# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md` (15 temuan S-01 s/d S-15)
**Format status:** OPEN | PASS | FAIL | BLOCKED

---

## IDX-R-001 (S-01) — LIVE mode dikunci

**Status:** OPEN
**File:** `app.py`

**Koreksi:**
1. Check `dry_run=false` dilakukan SEBELUM merge dan save config.
2. `ENABLE_LIVE_TRADING=true` env var sebagai server-side gate.
3. `load_config()` startup memaksa `dry_run=True` jika env var tidak aktif.
4. `POST /api/config` selalu override `dry_run=True` jika env var tidak aktif.
5. Dropdown Mode di Settings di-disable.

---

## IDX-R-003 (S-02) — Autentikasi

**Status:** OPEN
**File:** `app.py`, `.env`

**Koreksi:**
1. Fungsi `require_api_key()` memeriksa header `X-API-Key`.
2. Auth di-enforce di endpoint: scalper start/stop, config POST, telegram test/daily.
3. `DASHBOARD_API_KEY` env var — jika kosong, auth disabled (backward compatible).
4. Framework siap tinggal isi env var untuk aktifkan.

---

## IDX-R-002 (S-03) — Health gate START

**Status:** OPEN
**File:** `app.py`

**Koreksi:**
1. `system_healthy()` memeriksa: market data (tickers tersedia, tidak stale), MySQL reachable, pair rules terisi.
2. `POST /api/scalper/start` menggunakan `system_healthy()` sebagai gate.
3. Endpoint `/health` baru: return status ok/degraded + daftar issues.

---

## IDX-R-016 (S-16) — Kredensial default MySQL

**Status:** OPEN
**File:** `app.py`, `.env`

**Koreksi:**
1. Hapus semua fallback kredensial dari `app.py` → fail-closed.
2. Pindahkan kredensial ke `.env` (tidak di-track git).
3. `get_db()` runtime check — raise error jika MySQL belum dikonfigurasi.

---

## Ringkasan

| ID | Temuan | Status |
|----|--------|--------|
| IDX-R-001 | S-01 LIVE mode terkunci | 🔄 OPEN |
| IDX-R-002 | S-03 Health gate START | 🔄 OPEN |
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
| IDX-R-016 | S-16 MySQL credentials | 🔄 OPEN |


---

## Instruksi Auditor — Re-audit 18 Juli 2026

Label `PASS` hanya boleh dipasang setelah source, deployment, dan uji bukti untuk ID terkait telah diverifikasi. Berikut instruksi yang harus dikerjakan.

### IDX-R-016 — Kredensial MySQL

1. Tambahkan `.env` ke `.gitignore`; jangan commit secret atau salin ke README/log.
2. Rotasi segera kredensial MySQL yang pernah memakai nilai lama.
3. Pastikan startup gagal dengan pesan aman jika salah satu `IDX_DB_*` tidak tersedia.
4. Perbaiki `get_db()` agar setelah validasi ia menjalankan `return pymysql.connect(**DB_CONFIG)`.
5. Lampirkan bukti scan secret dan uji startup tanpa nilai secret sebelum meminta `PASS`.

### IDX-R-003 — Autentikasi

1. Untuk deployment publik, `DASHBOARD_API_KEY` wajib ada; jika kosong, endpoint kontrol harus fail-closed (503), bukan auth dinonaktifkan.
2. Terapkan `require_api_key()` pada semua endpoint yang memiliki efek atau membuka data sensitif, termasuk `/api/telegram/daily`, portfolio, trade/PnL, dan config.
3. Tambahkan pembatasan brute-force/rate-limit, audit actor, serta jangan mencetak API key ke log.
4. Uji: tanpa header = 401/503; header salah = 401; header benar = hanya endpoint yang diizinkan.

### IDX-R-001 — Live gate

1. Tetapkan satu sumber kebenaran: default selalu DRY_RUN.
2. Jangan biarkan `SCALPER_DRY_RUN=false` menyalakan LIVE secara mandiri.
3. Jika LIVE didukung, `ENABLE_LIVE_TRADING=true` harus diverifikasi server-side saat startup dan saat eksekusi, dengan approval/TTL/audit yang eksplisit.
4. Tambahkan test: config API tidak dapat menyalakan LIVE; restart tidak dapat mengaktifkan LIVE tanpa gate; executor tetap dry-run saat gate tidak lengkap.

### IDX-R-002 — Health gate

1. Setelah perbaikan `get_db()`, pastikan query MySQL dan pair rules benar-benar sukses; jangan menelan exception pair rules.
2. Tolak START jika: ticker kosong/stale, MySQL/pair rules gagal, stream tidak sehat, atau ada recovery order.
3. Endpoint `/health` harus memberi alasan terstruktur dan START harus diuji untuk setiap kondisi gagal.
4. Jangan mengubah label menjadi `PASS` hanya karena fungsi ada; sertakan hasil uji endpoint dan log tersanitasi.

### Urutan kerja

`R-016 → R-003 → R-001 → R-002 → R-006 → R-008 → R-007/R-011/R-012 → R-004/R-005/R-009/R-010/R-013/R-015 → R-014`

Setelah satu ID selesai, tulis bukti uji di file ini dan ubah statusnya menjadi `OPEN` untuk re-audit. Auditor yang menetapkan `PASS` setelah bukti cocok.
