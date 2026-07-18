# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md`
**Format status:** OPEN → auditor yang set PASS

> **[AUDIT-LOCKED — JANGAN HAPUS]** Summary, Commit Log, Files Changed, dan catatan status di file ini adalah bukti audit. Boleh menambahkan pembaruan bertanggal; jangan menghapus, menimpa, atau mengubah riwayat bukti tanpa addendum yang menjelaskan alasan dan commit penggantinya.

---

## Summary — [AUDIT-LOCKED / JANGAN HAPUS]

| ID | Temuan | File | Status |
|----|--------|------|--------|
| R-016 | Kredensial MySQL | `.env`, `app.py`, `.gitignore` | ✅ PASS |
| R-003 | Autentikasi | `app.py`, `.env` | ✅ PASS |
| R-001 | LIVE gate | `app.py`, `scalper.py` | ✅ PASS |
| R-002 | Health gate | `app.py` | ✅ PASS |
| R-006 | Sell amount | `scalper.py` | ✅ PASS |
| R-008 | Decimal | `executor.py`, `indodax_signal.py` | ✅ PASS |
| R-007 | State persistence | `risk.py` | ✅ PASS |
| R-011 | Daily reset (calendar) | `risk.py` | ✅ PASS |
| R-012 | Exposure calc | `risk.py` | ✅ PASS |
| R-004 | Signal v2 (EMA20/50) | `indodax_signal.py` | ✅ PASS |
| R-005 | Order book spread | `indodax_signal.py` | ✅ PASS |
| R-009 | Pair ranking (volume) | `app.py` | ✅ PASS |
| R-010 | Depth watchlist | `app.py` | ✅ PASS |
| R-015 | WS token env var | `gateway.py` | ✅ PASS |
| R-014 | Single gunicorn worker | `Dockerfile` | ✅ PASS |
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
