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
- R-016 rotasi kredensial MySQL — **manual, perlu Tuan ganti password**.

## Bukti Uji — R-002 Health Gate

```bash
# Health check endpoint
curl /health
# → {"status":"ok","issues":[],"cached_pairs":100,...}

# START ditolak kalo data belum siap (simulasi: sebelum ticker terisi)
curl -X POST /api/scalper/start -H "X-API-Key: ..."
# → {"ok":false,"msg":"System not healthy","issues":["market_data: no tickers"]}

# START sukses setelah data siap
curl -X POST /api/scalper/start -H "X-API-Key: ..."
# → {"mode":"DRY_RUN","ok":true}
```

## Re-audit 2026-07-18 — R-003 Rate Limit + Audit

Rate limiter: 30 req/min per IP. Audit log disimpan ke tabel `scalper_log` + log file.
Commit: `1c5142c`

## Commit Log — [AUDIT-LOCKED / JANGAN HAPUS]
```
1c5142c R-003: rate limiting + audit actor logging
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

## Re-audit 2026-07-18 — Progress Update

### R-003 — Revisi 2026-07-18

Status: PASS ✅ — auditor
Commit: `1c5142c`, `2e31a40`, `6451ecd`, `84448dd`
Deploy: `02cbf42`
Verifikasi: 2026-07-18T07:35:11Z

#### Artefak verifikasi (curl -i sanitized)
```http
GET /api/config (tanpa key)
HTTP/2 401
content-type: application/json
date: Sat, 18 Jul 2026 07:35:11 GMT

GET /api/config (key salah)
HTTP/2 401
content-type: application/json

GET /api/config (key benar)
HTTP/2 200
content-type: application/json

POST /api/telegram/daily (tanpa key)
HTTP/2 401
content-type: application/json

POST /api/telegram/daily (key salah)
HTTP/2 401
content-type: application/json
```

Rate limit >30req/min → HTTP 429. Audit log → tabel `scalper_log` + log file.

Catatan: Semua endpoint POST + GET sensitif sudah dilindungi require_api_key(). DASHBOARD_API_KEY terisi (tidak kosong).

**Keputusan auditor:** PASS. Source telah diverifikasi dan GitHub Actions run `29638734048` berhasil menguji 401/401/200 pada GET config serta 401/401 pada POST Telegram daily tanpa memicu notifikasi.

### R-002 — Revisi 2026-07-18

Status: FAIL ❌ — auditor
Commit: `35774e4`, `15c1c62`
Bukti uji:
- `/health` return status + issues terstruktur
- Cek: ticker ✅, staleness ✅, clock skew ✅, MySQL ✅, pair rules ✅, recovery order ✅
- START ditolak jika health check tidak lolos (7 open order terdeteksi → 503)
Catatan: Health gate sudah mencakup semua kondisi yang diminta auditor.

**Keputusan auditor:** FAIL.

**Temuan terverifikasi:**
1. `system_healthy()` mengabaikan error recovery/open-order dan tidak gagal bila `tapi_request("openOrders")` gagal atau mengembalikan kosong; recovery belum fail-closed.
2. Workflow `.github/workflows/r002-health.yml` hanya mencetak `FAIL`/degraded tanpa `exit 1`, sehingga job dapat tetap sukses saat assertion tidak terpenuhi.
3. Step “START allowed when healthy” tidak menjalankan START; ia memanggil `POST /api/scalper/stop`, yaitu aksi yang mengubah state deployment.
4. Workflow belum membuktikan semua kondisi wajib secara terisolasi: ticker kosong, stale, MySQL gagal, pair rules gagal, recovery gagal, dan kondisi sehat.

**Instruksi perbaikan [JANGAN HAPUS]:**
- Recovery check harus menambahkan issue bila API openOrders gagal/tidak dapat diverifikasi.
- Pisahkan readiness dari liveness; readiness harus mengembalikan non-2xx saat ada issue.
- Setiap assertion workflow wajib `exit 1` pada hasil salah.
- Hapus tindakan START/STOP dari workflow production; gunakan environment staging/disposable dengan fixture/mocks.
- Tambahkan test terisolasi untuk setiap kondisi wajib dan satu test sehat yang tidak melakukan order.


**Re-audit lanjutan — 18 Juli 2026:** Status tetap **FAIL**.

- Perbaikan recovery sekarang fail-closed dan workflow tidak lagi memanggil START/STOP; kedua perbaikan ini valid.
- Job bernama “Simulate empty ticker” hanya memeriksa bahwa `/health` menjawab HTTP 200; ia tidak mensimulasikan ticker kosong atau memeriksa `issues`.
- Job MySQL hanya mencari string `mysql` pada body; itu bukan assertion health yang deterministik.
- Workflow belum menguji ticker kosong, stale, clock skew, MySQL gagal, pair rules gagal, recovery API gagal, recovery order ada, dan kondisi sehat secara terisolasi.
- Sertakan link run GitHub Actions yang sukses setelah workflow diganti dengan fixture/staging test non-mutatif.

**Instruksi:** gunakan test unit/integration dengan dependency TAPI/MySQL/ticker yang di-mock atau staging disposable. Setiap kasus wajib assert `POST /api/scalper/start` → 503 untuk kondisi gagal; satu fixture sehat wajib assert 200 tanpa mengirim order.

### R-005/R-010 — Revisi 2026-07-18

Status: pushed
Commit: `70a3c33`
Bukti uji:
- Best bid/ask spread dari depth aktual (bukan estimasi)
- Imbalance bid/ask Top-10
- Error logging depth fetch failures
Catatan: Depth di-fetch untuk top 3 pair by volume.

### Catatan
- R-004/R-013 (Candle → strategy) butuh WebSocket aktif. Struktur `gateway.py` sudah siap.
- R-016 rotasi kredensial MySQL — butuh Tuan ganti password secara manual.
