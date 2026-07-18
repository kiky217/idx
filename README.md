# IDX — Indodax Scalping Dashboard

**Status:** Production (DRY RUN)
**Stack:** Python Flask + MySQL 8.0 + Docker
**Domain:** https://idx.srv1804652.hstgr.cloud
**Repo:** https://github.com/kiky217/idx

---

## 🔬 Audit Status

Semua temuan audit di-track di [`correction/README.md`](correction/README.md).

| ID | Temuan | Status |
|----|--------|--------|
| R-001 | LIVE mode terkunci | 🔄 pushed |
| R-002 | Health gate | 🔄 pushed |
| R-003 | Autentikasi + rate limit | 🔄 pushed |
| R-004 | Signal v2 (EMA20/50) | 🔄 pushed |
| R-005 | Order book spread | 🔄 pushed |
| R-006 | Sell amount eksplisit | 🔄 pushed |
| R-007 | State persistence | 🔄 pushed |
| R-008 | Decimal precision | 🔄 pushed |
| R-009 | Pair ranking by volume | 🔄 pushed |
| R-010 | Depth watchlist | 🔄 pushed |
| R-011 | Daily reset kalender | 🔄 pushed |
| R-012 | Exposure total | 🔄 pushed |
| R-013 | Candle chart | 🔄 partial |
| R-014 | Single gunicorn worker | 🔄 pushed |
| R-015 | WS token env var | 🔄 pushed |
| R-016 | MySQL credentials | 🔄 pushed |

## 🔧 Fitur

| Fitur | Status |
|-------|--------|
| Dashboard Bootstrap 5 | ✅ |
| Live ticker 497 pair IDR | ✅ |
| Search + filter pair | ✅ |
| Chart.js price chart | ✅ |
| Portfolio (saldo + aset) | ✅ |
| Scalper ENGINE start/stop | ✅ |
| Risk manager (daily limits) | ✅ |
| Telegram notifikasi | ✅ |
| API Key auth | ✅ (X-API-Key header) |
| Rate limiter | ✅ (30 req/min/IP) |
| Audit log | ✅ (tabel scalper_log) |
| Health check endpoint | ✅ (/health) |
| DRY RUN mode (terkunci) | ✅ |
| Dual timezone (WIB/UTC) | ✅ |
| WebSocket gateway | 🆕 (gateway.py) |
| Candle engine 1m/5m/15m | 🆕 (gateway.py) |

## 📦 File Structure

| File | Fungsi |
|------|--------|
| `app.py` | Flask dashboard + API + HTML |
| `gateway.py` | WebSocket market gateway + candle |
| `scalper.py` | Scalper engine |
| `indodax_signal.py` | Signal engine v2 (EMA20/50) |
| `executor.py` | Trade executor |
| `risk.py` | Risk manager |
| `pnl.py` | PnL tracking |
| `telegram.py` | Telegram bot |
| `mysql-schema.sql` | Database schema (14 tabel) |
| `blueprint.md` | AkiraBot Precision Scalper blueprint |
| `correction/` | Audit correction log |

## 🔗 Endpoints

| Endpoint | Method | Auth | Fungsi |
|----------|--------|------|--------|
| `/` | GET | - | Dashboard UI |
| `/health` | GET | - | Health check |
| `/api/live` | GET | - | Live ticker data |
| `/api/config` | GET | ✅ | Config |
| `/api/config` | POST | ✅ | Update config |
| `/api/portfolio` | GET | ✅ | Balance + aset |
| `/api/scalper/start` | POST | ✅ | Start engine |
| `/api/scalper/stop` | POST | ✅ | Stop engine |
| `/api/scalper/trades` | GET | ✅ | Trade log |
| `/api/pnl/*` | GET | ✅ | PnL data |
| `/api/telegram/*` | POST | ✅ | Telegram notify |
| `/api/chart/<pair>` | GET | - | Chart data |
| `/api/pairs` | GET | - | All pairs |
| `/ticker/<pair>` | GET | - | Single ticker |
| `/api/tickers` | GET | - | All tickers |

## 🐳 Docker

```bash
cd /docker/idx
docker compose up -d
```
