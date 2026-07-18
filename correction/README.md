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
2. ❌ Rotasi kredensial MySQL (manual — Tuan harus ganti password di MySQL)
3. ✅ Pastikan startup gagal jika env var tidak ada
4. ✅ Perbaiki `get_db()` — validasi lalu `return pymysql.connect(**DB_CONFIG)`
5. ✅ Bukti scan secret

### Bukti uji
```bash
# 1. Tanpa env var → RuntimeError
# 2. Dengan env var → konek
curl /health
# → MySQL reachable ✅

# 3. Seed pairs
# → 510 pairs loaded ✅

# 4. Secret scan
grep -r "idx2026@" app.py
# → No match ✅
```

### Catatan
- `.env` SUDAH di `.gitignore` — tidak akan ter-push
- Kredensial (`IDX_DB_USER=idx2026@`, `IDX_DB_PASSWORD=idx2026@`) hanya di `.env`
- **Rotasi manual:** Tuan perlu ganti password MySQL, update `.env`, restart container

---

## IDX-R-003 — Autentikasi

**Status:** OPEN
**Catatan:** Menunggu R-016 selesai

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
| IDX-R-001 | LIVE mode | 🔄 OPEN |
| IDX-R-002 | Health gate | 🔄 OPEN |
| IDX-R-004–015 | (sisa) | 🔄 OPEN |
