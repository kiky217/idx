# IDX — Change Log

> Catatan perubahan proyek IDX (Indodax Scalping Bot).
> Setiap kali ada perubahan, dicatat di sini untuk evaluasi lintas sesi.

---

## 2026-07-18 — Sesi 1: Bedah 9router + Setup IDX

### Ringkasan
Sesi ini mencakup bedah menyeluruh 9router dan Headroom, setup AEGERS untuk IDX, upgrade dashboard besar-besaran, dan integrasi MySQL.

### Yang Dirubah

#### Dashboard (app.py)
| # | File | Perubahan | Detail |
|---|------|-----------|--------|
| 1 | `app.py` | Import tambahan | `threading`, `Path`, `pymysql` |
| 2 | `app.py` | Config persistence | `config.json` — semua setting scalper/risk/UI tersimpan otomatis |
| 3 | `app.py` | Chart data ring buffer | `push_chart_data()` / `get_chart_data()` — 500 titik per pair |
| 4 | `app.py` | **Dashboard Bootstrap 5** | Ganti custom CSS → Bootstrap 5 dark theme |
| 5 | `app.py` | **Tab system** | Dashboard / Portfolio / Chart / Settings |
| 6 | `app.py` | **Chart.js** | Price chart dengan timeframe 15m/30m/1h/4h/1d |
| 7 | `app.py` | **Settings panel** | 12 config field — semua parameter scalper & risk bisa diubah dari dashboard |
| 8 | `app.py` | **Scalper START/STOP** | Tombol langsung dari dashboard |
| 9 | `app.py` | **Double timezone** | WIB + UTC berdampingan |
| 10 | `app.py` | **Search + Filter pairs** | Search bar + filter (Semua/Dimiliki/Top) + sort (Nama/Volume/Harga) |
| 11 | `app.py` | **Card / List view** | Toggle antara grid card dan tabel kompak (kaya Indodax) |
| 12 | `app.py` | **Portfolio tab** | Lihat saldo + aset + nilai IDR real-time |
| 13 | `app.py` | **All pairs** | Dari 2 pair (owned) → 497 pair IDR (max 100 ditampilkan) |
| 14 | `app.py` | **Config API** | GET/POST `/api/config` — baca & ubah setting dari dashboard |
| 15 | `app.py` | **Chart API** | GET `/api/chart/<pair>` — data chart ring buffer |
| 16 | `app.py` | **Portfolio API** | GET `/api/portfolio` — balance + aset + nilai |
| 17 | `app.py` | **Pairs API** | GET `/api/pairs` — daftar semua pair |
| 18 | `app.py` | **Bugfix: duplicate IDs** | Nav-link dan tab-content punya ID sama → dipisah `nav-*` vs `tab-*` |
| 19 | `app.py` | **Bugfix: chart load** | `switchTab` cari `getElementById('chart')` → typo, jadi `tab-chart` |
| 20 | `app.py` | **Bugfix: chart null** | `currentPair` null pas pertama buka → fallback ke pair pertama |
| 21 | `app.py` | **Bugfix: chart refresh** | Chart gak auto-refresh → interval 10 detik |

#### Infrastructure
| # | Item | Perubahan | Detail |
|---|------|-----------|--------|
| 1 | `requirements.txt` | Tambah `pymysql` | Dependency MySQL |
| 2 | `docker-compose.yml` | (Tidak diubah) | Sesuai instruksi |
| 3 | System timezone | Set `Asia/Jakarta` | WIB (UTC+7) |

#### MySQL
| # | Item | Detail |
|---|------|--------|
| 1 | Database | `idx_db` created |
| 2 | User | `idx2026@` / `idx2026@` |
| 3 | Host | `delta_mysql:3306` (Docker DNS) |
| 4 | Tabel | `trades`, `pnl_daily`, `signals`, `config_history`, `scalper_log` |

#### AEGERS
| # | Item | Detail |
|---|------|--------|
| 1 | Profile | `/root/library/idx/profile.md` |
| 2 | Evidence manifest | `/root/library/idx/evidence-manifest.tsv` |
| 3 | Risk register | `/root/library/idx/risk-register.tsv` |

#### Referensi & Skill
| # | Item | Perubahan |
|---|------|-----------|
| 1 | `indodax-api` skill | Update rate limit (20 req/detik/akun/pair) |
| 2 | `library/docs/indodax.md` | Update rate limit |
| 3 | `9router` skill | Update infra Docker path |
| 4 | `headroom-ai` skill | Rewrite lengkap (arsitektur, pipeline, Rust core) |
| 5 | `library/docs/9router.md` | Update infra Docker |
| 6 | `library/docs/headroom-ai.md` | Rewrite lengkap |
| 7 | `guide.md` | Fix default provider (ZERO-DEEPSEEK), tambah project IDX |
| 8 | `MEMORY.md` | Tambah IDX project + model deepseek-v4-pro |

#### Screenshot Reference
| File | Deskripsi |
|------|-----------|
| `/root/data_temp/contoh-capture-indodax.PNG` | Referensi layout Indodax |
| `/tmp/indodax-btc.png` | Screenshot Indodax BTC/IDR |
| `/tmp/idx-ultipro.png` | Screenshot dashboard baru |
| `/tmp/idx-clock.png` | Screenshot dual clock |

### Yang Ditambah (Fitur Baru)

| Fitur | Status | Keterangan |
|-------|--------|------------|
| Dashboard Bootstrap 5 | ✅ | Dark theme, responsive |
| Tab: Dashboard | ✅ | Ticker, stats, signal, risk, trade log |
| Tab: Portfolio | ✅ | Balance, aset, nilai IDR |
| Tab: Chart | ✅ | Chart.js, timeframe, auto-refresh |
| Tab: Settings | ✅ | 12 parameter, save config |
| Search filter | ✅ | Cari pair, filter owned, sort by |
| Card/List view | ✅ | Toggle tampilan |
| Dual clock | ✅ | WIB + UTC |
| Scalper START/STOP | ✅ | Tombol langsung |
| Config persistence | ✅ | config.json auto-save |
| MySQL integration | ✅ | 5 tabel, user khusus |
| Backup app.py | ✅ | `/docker/idx/app.py.bak.*` |

### Yang Belum

| Item | Status | Rencana |
|------|--------|---------|
| Ensemble strategy (AkiraBot) | ❌ | Integrasi multi-indicator + regime filter |
| Circuit breaker | ❌ | Stop kalo 3 loss berturut |
| Backtest | ❌ | Test historis dari dashboard |
| Telegram notif | ⚠️ | Bot valid, tapi notif trade belum jalan |
| Order book depth | ❌ | Tambah visual orderbook |
| **WebSocket Market Gateway** | 🆕 | `app/gateway.py` — struktur dasar siap |
| **Candle Engine 1m/5m/15m** | 🆕 | `app/gateway.py` — struktur dasar siap |
| **Blueprint Compliance** | 📋 | Audit di `/root/library/idx/blueprint-compliance-audit.md` |
| **MySQL Restructure** | ✅ | 14 tabel sesuai blueprint |

### Catatan Penting

- **Combo 9router jangan diubah** — sesuai instruksi
- **ZERO-DEEPSEEK** adalah default provider Hermes
- **Caveman & Ponytail FULL** — diaktifkan sesi ini
- **9router container sempat blackout** — exit 137 (OOM), udah direstart
- **Dashboard backup** ada di `/docker/idx/app.py.bak.*`
- **Reference Indodax** di `/root/data_temp/contoh-capture-indodax.PNG`
