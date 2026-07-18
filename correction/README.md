# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md`
**Format status:** OPEN → auditor yang set PASS

> **[AUDIT-LOCKED — JANGAN HAPUS]** Summary, Commit Log, Files Changed, dan catatan status di file ini adalah bukti audit. Boleh menambahkan pembaruan bertanggal; jangan menghapus, menimpa, atau mengubah riwayat bukti tanpa addendum yang menjelaskan alasan dan commit penggantinya.

---

## Summary — [AUDIT-LOCKED / JANGAN HAPUS]

| ID | Temuan | File | Status |
|----|--------|------|--------|
| R-016 | Kredensial MySQL | `.env`, `app.py`, `.gitignore` | 🔄 pushed |
| R-003 | Autentikasi | `app.py`, `.env` | 🔄 pushed |
| R-001 | LIVE gate | `app.py`, `scalper.py` | 🔄 pushed |
| R-002 | Health gate | `app.py` | 🔄 pushed |
| R-006 | Sell amount | `scalper.py` | 🔄 pushed |
| R-008 | Decimal | `executor.py`, `indodax_signal.py` | 🔄 pushed |
| R-007 | State persistence | `risk.py` | 🔄 pushed |
| R-011 | Daily reset (calendar) | `risk.py` | 🔄 pushed |
| R-012 | Exposure calc | `risk.py` | 🔄 pushed |
| R-004 | Signal v2 (EMA20/50) | `indodax_signal.py` | 🔄 pushed |
| R-005 | Order book spread | `indodax_signal.py` | 🔄 pushed |
| R-009 | Pair ranking (volume) | `app.py` | 🔄 pushed |
| R-010 | Depth watchlist | `app.py` | 🔄 pushed |
| R-015 | WS token env var | `gateway.py` | 🔄 pushed |
| R-014 | Single gunicorn worker | `Dockerfile` | 🔄 pushed |
| R-013 | Candle chart | UI | 🔄 partial |

**Ket: [AUDIT-LOCKED / JANGAN HAPUS]**
- R-013 (Candle chart) butuh WebSocket aktif + candle engine. Struktur `gateway.py` sudah siap.
- Semua file terdampak sudah di-push ke `master` branch.

## Commit Log — [AUDIT-LOCKED / JANGAN HAPUS]
```
ba4a664 R-014: single gunicorn worker
a5a1543 R-007/R-011/R-012: risk persistence + calendar reset + exposure
21da069 R-015: WS token env var
10f8548 R-009/R-010: pair ranking + depth watchlist
556fe89 R-005: order book spread
8c9a6d4 R-004: signal v2 EMA20/50
b5088e2 R-008: Decimal import
4469e55 R-006: sell uses actual balance
15c1c62 R-002: health gate fix
63a20c7 R-001: SCALPER_DRY_RUN override
51b86c4 R-003: auth fail-closed
0de9a5b R-016: get_db fix + seed pairs
```

## Files Changed (final) — [AUDIT-LOCKED / JANGAN HAPUS]
- `app.py` — S-01, S-02, S-03, S-09, S-10, S-16
- `scalper.py` — S-01, S-06
- `indodax_signal.py` — S-04, S-05, S-08
- `executor.py` — S-08
- `risk.py` — S-07, S-11, S-12
- `gateway.py` — S-15
- `Dockerfile` — S-14
- `.env` — S-02, S-16
- `.gitignore` — S-16


---

## Ketentuan bukti — [AUDIT-LOCKED / JANGAN HAPUS]

1. Status `pushed` berarti source telah dikirim ke branch, **bukan** otomatis `PASS`.
2. Status hanya dapat menjadi `PASS` setelah auditor memverifikasi source, konfigurasi aman, dan bukti uji yang relevan.
3. Catatan `R-013` harus dipertahankan sampai WebSocket, Candle Engine, dan UI candle tervalidasi end-to-end.
4. Jangan menulis secret, API key, password, token, atau isi `.env` di file ini, commit log, issue, maupun screenshot.
5. Untuk revisi, tambahkan bagian `Re-audit YYYY-MM-DD` dengan ID, bukti uji, hasil, dan commit; jangan menghapus temuan lama.


---

## Re-audit prioritas — 18 Juli 2026 [AUDIT-LOCKED / JANGAN HAPUS]

### Status yang belum dapat menjadi PASS

| ID | Status audit | Hasil verifikasi source |
|---|---|---|
| R-016 | OPEN | Fallback secret sudah dihapus, `.env` sudah diabaikan Git, dan `get_db()` sudah mengembalikan koneksi. Tetap butuh bukti rotasi kredensial dan uji deployment. |
| R-001 | OPEN | `ENABLE_LIVE_TRADING` sudah menjadi gate pada inisialisasi scalper. Tetap butuh uji restart dan pembuktian executor tidak dapat LIVE tanpa gate. |
| R-003 | OPEN | Auth fail-closed sudah ada, tetapi belum diterapkan ke seluruh endpoint sensitif. |
| R-002 | OPEN | Health gate MySQL/pair rules sudah ada, tetapi freshness dan recovery belum lengkap. |

### Instruksi berikutnya — IDX-R-003 Autentikasi [JANGAN HAPUS]

Tambahkan `require_api_key()` ke endpoint berikut:

- `POST /api/telegram/daily`
- `GET /api/scalper/trades`
- `GET /api/config`

Tentukan boundary endpoint read-only publik secara eksplisit. Jika dashboard bukan untuk publik, lindungi juga endpoint market/status (`/api/live`, `/api/tickers`, `/ticker/<pair>`, dan `/health`) melalui aplikasi atau reverse proxy.

Bukti wajib sebelum meminta PASS:

1. Tanpa `X-API-Key` → 401; jika `DASHBOARD_API_KEY` tidak ada → 503.
2. Key salah → 401.
3. Key benar → akses hanya berjalan untuk endpoint yang diizinkan.
4. Tidak ada API key/log credential yang tercetak pada respons atau log uji.

### Instruksi setelah R-003 — IDX-R-002 Health gate [JANGAN HAPUS]

1. Jika `age_ts` tidak ada, jadikan health gagal; jangan hanya mengecek timestamp yang ada.
2. Tambahkan status freshness stream WebSocket/candle bila WebSocket menjadi source aktif.
3. Periksa open order atau recovery state sebelum START; bila belum direkonsiliasi, tolak START.
4. Kembalikan reasons terstruktur dari `/health` dan `/api/scalper/start`.
5. Uji tiap kondisi gagal secara terpisah, lalu tulis output tersanitasi di README.

**Aturan:** status `pushed` hanya berarti perubahan sudah dikirim. Hanya auditor yang boleh menetapkan `PASS` setelah bukti source dan uji sesuai.
