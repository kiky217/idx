# IDX — Source Code Archive

**Tanggal:** 2026-07-18 12:24
**Total:** 15 files, 172KB, 3.310 baris

---

## File List

| File | Baris | Ukuran | Fungsi |
|------|-------|--------|--------|
| `app.py` | 1.109 | 51KB | Flask dashboard + API + HTML template |
| `gateway.py` | 233 | 8.6KB | WebSocket market gateway + candle engine |
| `scalper.py` | 196 | 7.5KB | Scalper engine (loop, signal processing) |
| `indodax_signal.py` | 190 | 6.0KB | Signal engine (EMA9/21, RSI, volume) |
| `executor.py` | 211 | 7.0KB | Trade executor (order placement) |
| `risk.py` | 109 | 4.2KB | Risk manager (config, limits) |
| `pnl.py` | 148 | 6.2KB | PnL storage and tracking |
| `telegram.py` | 109 | 3.9KB | Telegram bot integration |
| `mysql-schema.sql` | 385 | 16KB | MySQL 14-table schema |
| `blueprint.md` | 316 | 15KB | AkiraBot Blueprint v1.0 |
| `profile.md` | 143 | 4.5KB | AEGERS project profile |
| `CHANGELOG.md` | 120 | 5.8KB | Change log |
| `Dockerfile` | 14 | 350B | Docker build |
| `docker-compose.yml` | 22 | 553B | Docker compose |
| `requirements.txt` | 5 | 77B | Python dependencies |

## Architecture Overview

```
┌────────────────────────────────────────────────────┐
│  Container IDX                                      │
│  Python 3.12 + Flask + gunicorn                     │
│                                                     │
│  Threads: Flask API, Market Gateway, Candle Engine   │
│  State: In-memory dict (Redis planned)               │
│  DB: MySQL 8.0 (delta_mysql container)               │
│  Cache: In-memory dict + SQLite (config.json)        │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────┐     ┌──────────────────┐
│  delta_mysql   │     │  Indodax API     │
│  MySQL 8.0     │     │  REST + WebSocket │
└────────────────┘     └──────────────────┘
```

## Blueprint Compliance

| Section | Status |
|---------|--------|
| ✅ A. Foundation | Compose ✅, MySQL ✅, Redis ❌ |
| ❌ B. Market Gateway | REST ✅, WebSocket 🆕 (gateway.py) |
| ✅ C. Storage | MySQL 14 tabel ✅ |
| ❌ D. Candle/Indicators | Struktur 🆕 (gateway.py) |
| ❌ E. Strategy | Masih EMA9/21 |
| ❌ F. Paper Executor | Ada executor.py |
| ⚠️ G. Dashboard | Flask ✅, auth ❌ |
| ❌ H. Backtest | Belum |
| ❌ I. Paper Trading | Belum |
| ❌ J. Live Gate | Terkunci (DRY_RUN) |
