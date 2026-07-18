# AEGERS PROJECT PROFILE — IDX

## 1. Identity

- PROJECT_NAME: IDX — Indodax Crypto Scalping Bot
- PROJECT_CODE: IDX
- OWNER: Kiky Yudiansyah
- VERSION: 2.0
- STATUS: Running Production (sejak 2026-07-16, 46+ jam)
- CREATED_AT: 2026-07-15
- LAST_UPDATED: 2026-07-16 11:14

## 2. Purpose

- BUSINESS_GOAL: Auto-trading crypto scalping di Indodax exchange dengan logika signal + risk management + eksekusi otomatis
- TECHNICAL_GOAL: Flask web dashboard + signal engine + executor + risk manager + Telegram notifikasi. Containerized, Traefik-routed.
- PRIMARY_USERS: Kiky Yudiansyah (owner), Telegram group (notifikasi)
- SUCCESS_DEFINITION: Scalping profit konsisten, risk terkontrol, 0 loss dari bug, Telegram notif real-time

## 3. Scope

### IN_SCOPE
- ✅ Indodax API integration (ticker, order, balance)
- ✅ Signal engine (indodax_signal.py) — generate trading signals
- ✅ Trade executor (executor.py) — eksekusi order
- ✅ Risk manager (risk.py) — risk control
- ✅ Scalper engine (scalper.py) — scalping logic
- ✅ PnL tracking (pnl.py) — profit/loss
- ✅ Flask dashboard (app.py) — monitoring + control
- ✅ Telegram notifikasi (telegram.py, tg_patch.py)
- ✅ Docker container + Traefik routing
- ✅ Data persistence di /docker/idx/data/

### OUT_OF_SCOPE
- ❌ Multi-exchange support (hanya Indodax)
- ❌ Backtesting framework (belum)
- ❌ ML/AI-based prediction
- ❌ Mobile app

## 4. Constraints

- BUDGET: Indodax API rate limits, trading fees
- HARDWARE: VPS Hostinger (existing)
- OPERATING_SYSTEM: Linux (Docker)
- DEPLOYMENT_TARGET: Container (docker-compose)
- DEADLINE: Operational (running)
- COMPLIANCE: Indodax API ToS
- NO_GO_RULES: Jangan simpan secret di code/log. Jangan expose API key. Jangan loss dari bug.

## 5. Architecture Baseline

- FRONTEND: Flask + render_template_string (inline HTML)
- BACKEND: Python 3 (Flask, gunicorn)
- DATABASE: File-based (data/ directory)
- CACHE: None
- QUEUE: None (inline execution)
- AI: Zero (Hermes) — monitoring + logic improvement
- AUTOMATION: Scalper engine (auto trade)
- STORAGE: bind mount /docker/idx/data/ → /app/data
- DEPLOYMENT: Docker (idx:latest image)
- NETWORK: traefik_internal_net, domain idx.srv1804652.hstgr.cloud
- OBSERVABILITY: Flask dashboard + Telegram notif

## 6. Security Baseline

- AUTHENTICATION: None on dashboard (internal network via Traefik)
- AUTHORIZATION: None
- SECRET_STORAGE: .env file (bind mount ke container)
- PUBLIC_EXPOSURE: Domain idx.srv1804652.hstgr.cloud via Traefik (HTTPS)
- DATA_CLASSIFICATION: Trading data (sensitive), API keys (critical)
- LOGGING_POLICY: Flask log, no sensitive data
- AUDIT_POLICY: PnL tracker

## 7. Backup and Recovery

- BACKUP_SCOPE: /docker/idx/data/ + .env + source code
- RETENTION: 7 hari
- RECOVERY_LOCATION: /docker/idx/ (in-place)
- RPO: 1 hari
- RTO: 30 menit
- RESTORE_OWNER: Kiky

## 8. Cleanup Policy

- TRASH_LOCATION: /docker/idx/data/trash/
- RETENTION: 30 hari
- MANIFEST_REQUIRED: Yes
- PERMANENT_DELETE_APPROVER: Kiky

## 9. Acceptance Criteria

### FUNCTIONAL
- Signal engine generate sinyal akurat
- Executor place/cancel order sesuai logika
- Risk manager cegah over-leverage
- PnL tracking akurat
- Dashboard real-time
- Telegram notif jalan

### SECURITY
- API key tidak bocor
- Domain pakai HTTPS (Traefik + Let's Encrypt)
- Tidak ada endpoint publik tanpa auth

### RUNTIME
- Container restart otomatis (restart: unless-stopped)
- Tidak ada memory leak
- Response dashboard <5s

### REGRESSION
- Perubahan tidak merusak trading yg sedang jalan
- Rollback plan siap

### DOCUMENTATION
- AEGERS profile + stages lengkap
- Runbook operasional
- Evidence manifest

## 10. Approval Authority

- ARCHITECTURE_APPROVER: Kiky
- HIGH_RISK_APPROVER: Kiky
- CRITICAL_RISK_APPROVER: Kiky
- FINAL_ACCEPTANCE_OWNER: Kiky

## 11. Locked Decisions

- Hanya Indodax (no multi-exchange)
- Telegram notif via bot
- Docker container (no bare metal)
- Traefik routing (HTTPS)
- File-based storage (no database server)
- Python Flask (no framework migration)
- **WAJIB MENGIKUTI BLUEPRINT** — `/root/library/idx/akirabot-indodax-precision-scalper-blueprint.md`
- Blueprint adalah **ATURAN MUTLAK** untuk semua pengembangan IDX ke depannya
- Semua keputusan arsitektur, state machine, risk gate, dan tahapan pembangunan WAJIB sesuai blueprint

## 12. Open Questions

- ⚠️ Telegram "chat not found" error — chat ID perlu diverifikasi
- Scalping strategy detail — perlu didiskusikan
- Risk parameters — leverage, max loss, dll
- Apakah perlu backtest sebelum ubah logika?
