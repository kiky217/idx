# Re-audit Source-only — IDX

**Tanggal:** 18 Juli 2026  
**Scope:** Static review source pada branch `master`.  
**Tidak dilakukan:** menjalankan container, database, WebSocket, order, atau pengujian endpoint runtime.

> **[AUDIT-LOCKED / JANGAN HAPUS]** Semua status di bawah adalah `OPEN`. Tidak ada klaim `PASS` atau hasil runtime dalam laporan ini.

| ID | Status | Bukti source | Prasyarat PASS |
|---|---|---|---|
| R-001 | OPEN | Gate `ENABLE_LIVE_TRADING` ada pada scalper. | Uji restart dan executor dengan gate mati. |
| R-002 | OPEN | Cek MySQL dan pair rules ada. | Gate untuk timestamp hilang, stream, recovery order, dan uji failure path. |
| R-003 | OPEN | Auth fail-closed ada. | Lindungi `/api/telegram/daily`, `/api/scalper/trades`, GET `/api/config`; uji 401/503. |
| R-004 | OPEN | EMA20/50 dan ATR ada. | Candle 15m → 5m → 1m yang benar-benar terhubung ke strategi. |
| R-005 | OPEN | Depth diambil. | Best bid/ask dan imbalance digunakan oleh SignalEngine/risk gate. |
| R-006 | OPEN | SELL memakai saldo coin aktual. | Quantization, minimum order, locked balance, dan contract test. |
| R-007 | OPEN | Risk state disimpan ke file. | Persistence/reconciliation order dan uji restart. |
| R-008 | OPEN | `Decimal` di-import. | Kalkulasi harga/jumlah/fee dipindah dari `float`. |
| R-009 | OPEN | Ranking `vol_idr` ada. | Uji likuiditas/spread pada data aktual. |
| R-010 | OPEN | Depth top pair dipanggil. | Observability error dan konsumsi depth aktif. |
| R-011 | OPEN | Reset kalender ada. | Timezone Asia/Jakarta dan uji lintas tengah malam. |
| R-012 | OPEN | Fungsi exposure ada. | Enforcement pada `can_trade()`. |
| R-013 | OPEN | CandleEngine ada. | WebSocket → candle → chart/strategy teruji end-to-end. |
| R-014 | OPEN | Gunicorn satu worker di Dockerfile. | Verifikasi proses runtime. |
| R-015 | OPEN | Token environment tersedia. | Hapus fallback hardcoded; test auth/ack/reconnect WebSocket. |
| R-016 | OPEN | Fallback credential dihapus dan `.env` di-ignore. | Bukti rotasi secret dan startup database. |

## Urutan perbaikan

`R-003 → R-002 → R-005/R-010 → R-004/R-013 → R-008 → R-011/R-012 → R-007/R-015 → R-006/R-009/R-014 → R-001/R-016`

Status hanya boleh berubah menjadi `PASS` setelah auditor memeriksa bukti source dan pengujian yang relevan.
