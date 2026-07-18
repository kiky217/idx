# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md`
**Format status:** OPEN | PASS | FAIL | BLOCKED
**Urutan kerja:** R-016 → R-003 → R-001 → R-002 → ...

---

## IDX-R-016 — Kredensial default MySQL

**Status:** OPEN
1. ✅ `.env` di `.gitignore`
2. ❌ Rotasi — manual
3. ✅ Startup fail-closed
4. ✅ `get_db()` validasi + return connect
5. ✅ Secret scan clean

## IDX-R-003 — Autentikasi

**Status:** OPEN
- ✅ `DASHBOARD_API_KEY` fail-closed (503 jika kosong)
- ✅ Semua POST + portfolio + PnL dilindungi

## IDX-R-001 — LIVE gate

**Status:** OPEN
1. ✅ `SCALPER_DRY_RUN` di-override oleh `ENABLE_LIVE_TRADING`
2. ✅ `load_config()` force dry_run=True startup
3. ✅ `POST /api/config` tolak dry_run=false (403)
4. ✅ `DEFAULT_CONFIG` selalu `dry_run: True`
5. ✅ Restart tidak aktifkan LIVE tanpa gate

**Bukti:**
```bash
curl -X POST /api/config -d '{"scalper":{"dry_run":false}}' -H "X-API-Key: ..."
# → 403
curl /api/config -H "X-API-Key: ..." | jq .scalper.dry_run
# → true
```

## IDX-R-002 — Health gate

**Status:** OPEN

## Ringkasan

| ID | Status |
|----|--------|
| R-016 | 🔄 OPEN |
| R-003 | 🔄 OPEN |
| R-001 | 🔄 OPEN |
| R-002 | 🔄 OPEN |
| R-004–015 | 🔄 OPEN |
