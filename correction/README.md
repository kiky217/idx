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

Status: pushed
Commit: `1c5142c`, `2e31a40`, `6451ecd`
Bukti uji:
- tanpa API key → 401
- API key salah → 401
- API key benar → 200
- Rate limit >30req/min → 429
- Audit log tersimpan di tabel `scalper_log`
Catatan: Endpoint GET /api/config, GET /api/scalper/trades, semua POST sudah dilindungi.

### R-002 — Revisi 2026-07-18

Status: pushed
Commit: `35774e4`
Bukti uji:
- `/health` return status + issues terstruktur
- Cek: ticker, staleness, clock skew, MySQL, pair rules, recovery order (7 open order terdeteksi)
- START ditolak jika health check tidak lolos
Catatan: Recovery order terdeteksi dengan benar (7 open order dari Indodax).

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
