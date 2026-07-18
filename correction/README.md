# Correction Log — IDX

**Mulai:** 18 Juli 2026
**Acuan:** `audit_idx_1.md`
**Format status:** OPEN | PASS | FAIL | BLOCKED
**Urutan kerja:** R-016 → R-003 → R-001 → R-002 → R-006 → R-008 → ...

---

## IDX-R-016 — Kredensial default MySQL

**Status:** OPEN (menunggu re-audit)
**File:** `app.py`, `.env`, `.gitignore`

### Instruksi auditor
1. ✅ Tambah `.env` ke `.gitignore`
2. ❌ **Rotasi kredensial** — manual. Tuan harus ganti password MySQL, update `.env`
3. ✅ Startup gagal jika env var tidak ada (fail-closed)
4. ✅ `get_db()` — validasi lalu `return pymysql.connect(**DB_CONFIG)`
5. ✅ Scan secret: `grep -r "idx2026@" app.py` → No match

### Bukti uji
```bash
# Health check
curl /health
# → MySQL reachable ✅, 510 pairs seeded ✅

# Secret scan
grep "idx2026@" app.py
# → (no output) ✅
```

---

## IDX-R-003 — Autentikasi

**Status:** OPEN
**Catatan:** `DASHBOARD_API_KEY` wajib diisi. Jika kosong, endpoint kontrol harus 503.

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
| IDX-R-016 | Kredensial MySQL | 🔄 OPEN (re-audit) |
| IDX-R-003 | Autentikasi | 🔄 OPEN |
| IDX-R-001 | LIVE mode terkunci | 🔄 OPEN |
| IDX-R-002 | Health gate | 🔄 OPEN |
| IDX-R-004–015 | (sisa) | 🔄 OPEN |
