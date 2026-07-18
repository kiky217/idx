# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md`
**Format status:** OPEN | PASS | FAIL | BLOCKED
**Urutan kerja:** R-016 → R-003 → R-001 → R-002 → ...

---

## IDX-R-016 — Kredensial default MySQL

**Status:** OPEN (menunggu re-audit)
**File:** `app.py`, `.env`, `.gitignore`

1. ✅ `.env` di `.gitignore`
2. ❌ Rotasi kredensial — manual
3. ✅ Startup fail-closed tanpa env var
4. ✅ `get_db()` validasi + return connect
5. ✅ Secret scan: `grep "idx2026@" app.py` → no match

**Bukti:**
```bash
curl /health
# → MySQL reachable ✅, 510 pairs ✅
```

---

## IDX-R-003 — Autentikasi

**Status:** OPEN (menunggu re-audit)
**File:** `app.py`, `.env`

### Perbaikan
1. ✅ `DASHBOARD_API_KEY` wajib diisi — jika kosong, semua endpoint return 503
2. ✅ Auth di semua POST: scalper start/stop, config, telegram test/daily
3. ✅ Auth di GET sensitif: portfolio, pnl summary/trades/daily
4. ✅ Key: `fccfc03d1e9f36177c3659099deaf132` (random 16 byte hex)
5. ❌ Rate limiting — belum (butuh redis atau middleware)

### Bukti uji
```bash
# Tanpa key → 401
curl -X POST /api/scalper/start
# → {"error":"Unauthorized. Invalid or missing X-API-Key header."}

# Key salah → 401
curl -X POST /api/scalper/start -H "X-API-Key: wrong"
# → {"error":"Unauthorized..."}

# Key benar → 200
curl -X POST /api/scalper/start -H "X-API-Key: fccfc03d..."
# → {"mode":"DRY_RUN","ok":true}

# Portfolio dengan key → data muncul
curl /api/portfolio -H "X-API-Key: ..."
# → total_idr: Rp1,778,499, assets: 8
```

---

## IDX-R-001 — LIVE gate

**Status:** OPEN

---

## IDX-R-002 — Health gate

**Status:** OPEN

---

## Ringkasan

| ID | Temuan | Status |
|----|--------|--------|
| IDX-R-016 | Kredensial MySQL | 🔄 OPEN |
| IDX-R-003 | Autentikasi | 🔄 OPEN |
| IDX-R-001 | LIVE mode | 🔄 OPEN |
| IDX-R-002 | Health gate | 🔄 OPEN |
| IDX-R-004–015 | (sisa) | 🔄 OPEN |
