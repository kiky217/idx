# AKIRABOT INDODAX PRECISION SCALPER

Versi: 1.0 — Blueprint pembangunan

## 1. Tujuan dan batas realistis

AkiraBot adalah bot scalping spot khusus Indodax. Bot memantau market, memilih pair yang likuid, membentuk candle 1m/5m/15m dari data live, lalu hanya membuka posisi BUY ketika semua gerbang kualitas lolos.

Tidak ada sistem yang dapat menjamin win rate 100%. Target engineering adalah *selective precision*: bot lebih sering menolak setup daripada membuka posisi, seluruh keputusan dapat diaudit, dan live trading tetap terkunci sampai hasil paper trading memenuhi kriteria yang telah disepakati.

Sumber integrasi Indodax hanya dokumentasi resmi: https://github.com/btcid/indodax-official-api-docs

## 2. Batas sistem

| Termasuk | Tidak termasuk |
|---|---|
| Spot buy → hold → sell pada pair Indodax | Futures, leverage, margin, atau short selling |
| Public REST + Market Data WebSocket | Data exchange atau indikator eksternal |
| Private REST untuk saldo, order, dan riwayat | API key dengan izin withdraw |
| MySQL untuk histori/audit dan Redis untuk state live | Query MySQL per tick |
| Paper trading sebagai mode awal | Live trading otomatis pada tahap awal |

## 3. Arsitektur produksi

```text
Public REST ──┐
              ├─ Market Gateway ── Redis Live State ── Candle Engine
WebSocket ───┘                                         │
                                                        ▼
                                               Strategy / Risk Engine
                                                        │
Private REST ◄── Execution & Position Manager ◄────────┘
       │                    │
       └────────────── MySQL Audit Store ──────────────┘
```

### 3.1 Tanggung jawab komponen

| Komponen | Tindakan nyata |
|---|---|
| `market_gateway` | Memuat pair/rule, membuka WebSocket, memulihkan koneksi, dan melakukan REST reconciliation |
| `pair_selector` | Memberi ranking seluruh market dan mengaktifkan maksimum 10 pair untuk stream detail |
| `live_state` | Menyimpan harga, depth, trade flow, candle berjalan, indikator, posisi, dan cooldown di Redis |
| `candle_engine` | Mengubah event trade menjadi candle final 1m; mengagregasikan 5m dan 15m |
| `strategy_engine` | Menghasilkan status teknis deterministik, bukan narasi AI |
| `risk_engine` | Menghitung ukuran posisi, SL, TP, fee, slippage, RR bersih, dan blokir risiko |
| `execution_engine` | Memvalidasi rule pair, menyimpan intent, mengirim order, dan merekonsiliasi status order |
| `position_manager` | Mengelola TP1, break-even, TP2, emergency exit, dan recovery setelah restart |
| `audit_store` | Menulis candle final, sinyal, order, posisi, trade, dan event ke MySQL |
| `dashboard` | Membaca cache/status, tidak pernah memanggil Indodax langsung |

## 4. Sumber data dan penggunaan

| Sumber resmi | Pemakaian |
|---|---|
| `/api/pairs` | Canonical pair id, ticker id, minimum order, precision |
| `/api/price_increments` | Pembulatan harga order |
| `/api/summaries` | Snapshot awal dan rekonsiliasi seluruh market |
| OHLC history | Backfill candle saat start atau recovery |
| `market:summary-24h` | Ranking seluruh pair secara live |
| `market:trade-activity-{pair}` | Trade flow dan pembentukan candle 1m |
| `market:order-book-{pair}` | Spread, kedalaman, dan imbalance |
| `chart:tick-{pair}` | Pelengkap data harga live |
| Private REST | Saldo, trade, cancel, open order, riwayat, dan verifikasi posisi |

## 5. State machine bot

```text
BOOTSTRAP
  → SYNCING
  → SCANNING
  → WATCHING
  → CANDIDATE_BUY
  → ORDER_PENDING
  → POSITION_OPEN
  → TP1_TAKEN
  → POSITION_CLOSED

Kondisi global:
  STALE_DATA / COOLDOWN / DAILY_LIMIT / CIRCUIT_BREAKER
  → PAUSE_ENTRY
```

### 5.1 Aturan state

- `BOOTSTRAP`: muat konfigurasi, paksa `DRY_RUN=true`, cek database/cache.
- `SYNCING`: ambil pair rule, snapshot market, dan candle histori minimal 100 bar per timeframe.
- `SCANNING`: market summary menyusun ranking pair.
- `WATCHING`: pair Top-N menerima stream trade/depth dan membangun indikator.
- `CANDIDATE_BUY`: semua filter teknis lolos, tetapi order belum dikirim.
- `ORDER_PENDING`: intent tersimpan; bot menunggu fill/cancel/reject.
- `POSITION_OPEN`: buy terisi; position manager aktif.
- `TP1_TAKEN`: sebagian posisi terjual; SL dipindah ke break-even sesuai aturan.
- `POSITION_CLOSED`: seluruh posisi selesai; P/L dan fee final dicatat; pair masuk cooldown bila rugi.
- `PAUSE_ENTRY`: tidak boleh membuka order baru; posisi yang ada hanya dikelola untuk proteksi.

## 6. Logika data live

### 6.1 Pada event market summary

1. Validasi timestamp event.
2. `UPSERT` Redis `live:summary:{pair}`.
3. Hitung score universum: volume IDR, perubahan harga, volatilitas, kualitas harga.
4. Pilih 5–10 pair terbaik yang memenuhi aturan minimum.
5. Subscribe/unsubscribe stream detail sesuai watchlist.

### 6.2 Pada event trade activity pair aktif

1. Tolak event yang sequence/timestamp-nya lebih lama dari state terakhir.
2. Perbarui candle 1m yang sedang berjalan: open/high/low/close/volume.
3. Tambah `buy_count`, `sell_count`, buy/sell volume, VWAP, dan largest trade pada Redis.
4. Saat batas menit UTC terlewati, finalisasi candle 1m.
5. Simpan candle final dan statistik trade per menit secara batch ke MySQL.
6. Bentuk candle 5m/15m bila batas interval tercapai.

### 6.3 Pada event order book pair aktif

1. Perbarui best bid/ask dan timestamp terakhir.
2. Hitung `spread_pct`.
3. Hitung volume bid/ask Top 10 serta imbalance.
4. Deteksi sell wall besar dekat TP dan bid collapse dekat harga entry.
5. Simpan hanya metrik ringkas tiap 5–10 detik atau ketika sinyal/order terjadi.

## 7. Strategi tunggal: trend continuation + pullback + momentum confirmation

Bot tidak mencoba semua pola. Ia hanya mencari satu setup LONG spot yang dapat diuji berulang.

### 7.1 Gerbang keras

Semua syarat harus bernilai `PASS`. Satu `FAIL` berarti `WAIT_AND_SEE`.

| Gerbang | PASS |
|---|---|
| Data health | WebSocket segar, stream trade/depth tersedia, tidak ada posisi/order duplikat |
| Market quality | Spread dalam batas, likuiditas cukup, tidak ada anomali event |
| Trend 15m | EMA20 > EMA50, struktur higher-low valid, close tidak di bawah support utama |
| Momentum 5m | Pullback sehat, RSI pulih, Stochastic bullish cross, volume cukup |
| Trigger 1m | Bullish engulfing, reclaim support, atau breakout-retest valid |
| Microstructure | Buy volume mendukung, bid Top 10 kuat, tidak ada sell wall dekat target |
| Risk | RR bersih ≥ 1:2, target menutup fee/slippage, ukuran memenuhi minimum order |
| Account | Saldo cukup, daily loss/cooldown/circuit breaker tidak aktif |

### 7.2 Parameter awal yang harus dikalibrasi

```text
EMA_FAST                         = 20
EMA_SLOW                         = 50
RSI_PERIOD                       = 14
STOCHASTIC                       = 14,3,3
ATR_PERIOD                       = 14
MIN_HISTORY_CANDLES              = 100
MAX_WATCHLIST_PAIRS              = 10
MAX_OPEN_POSITIONS               = 1
MIN_VOLUME_RATIO_1M              = 1.20
MIN_CONFIDENCE_SCORE             = 8.00
MIN_NET_RISK_REWARD              = 2.00
WEBSOCKET_STALE_SECONDS          = 5
ORDER_FILL_TIMEOUT_SECONDS       = 15
COOLDOWN_AFTER_LOSS_SECONDS      = 600
```

Nilai tersebut adalah titik awal paper trading, bukan angka sakral. Perubahan parameter hanya boleh diterapkan setelah hasil out-of-sample dibandingkan dengan baseline.

### 7.3 Pseudocode keputusan

```python
def evaluate_entry(state):
    if state.is_stale or state.has_open_position or state.has_pending_order:
        return reject("market_or_account_not_ready")
    if state.daily_limit_hit or state.cooldown_active or state.circuit_breaker:
        return reject("risk_lock")
    if state.spread_pct > state.max_spread_pct:
        return reject("spread_too_wide")
    if not state.trend_15m.bullish or not state.structure_15m.higher_low:
        return reject("trend_15m_not_valid")
    if not state.momentum_5m.confirmed or state.volume_ratio_1m < 1.20:
        return reject("momentum_or_volume_not_valid")
    if state.trigger_1m not in {"ENGULFING", "RECLAIM", "RETEST"}:
        return reject("no_1m_trigger")
    if state.orderbook_imbalance < state.minimum_imbalance:
        return reject("orderbook_not_supportive")

    plan = make_trade_plan(state)
    if plan.net_rr < 2.0 or plan.net_expected_profit <= 0:
        return reject("net_reward_not_sufficient")
    if plan.confidence < 8.0:
        return reject("confidence_below_threshold")
    return approve(plan)
```

## 8. Rencana transaksi dan eksekusi

### 8.1 Pembentukan plan

```text
entry       = harga limit yang valid menurut increment pair
stop_loss   = swing low 1m - buffer ATR
R           = entry - stop_loss
TP1         = entry + 1R
TP2         = entry + 2R
risk_budget = equity × risk_per_trade_pct
quantity    = risk_budget / R
```

Plan ditolak bila quantity/nominal tidak memenuhi minimum pair atau exposure maksimum.

### 8.2 Urutan aman order

1. Kunci pair pada Redis agar tidak ada dua worker membuka order yang sama.
2. Simpan `order intent` dengan `client_ref` unik di MySQL.
3. Cek saldo terbaru melalui Private REST.
4. Kirim BUY sesuai API resmi.
5. Poll/rekonsiliasi status order dengan batas retry dan rate limiter.
6. Jika tidak terisi dalam batas waktu dan trigger sudah batal, cancel order.
7. Jika partial fill, bentuk posisi dari `filled_amount`, bukan jumlah yang diminta.
8. Saat posisi terbuka, position manager mulai mengawasi SL/TP dengan data WebSocket.

### 8.3 Position manager

- Jika harga menyentuh TP1 dan fill sukses: jual porsi pertama, lalu pindahkan stop ke break-even sesuai konfigurasi.
- Jika harga menyentuh TP2: jual sisa posisi dan tutup trade.
- Jika harga menyentuh SL atau struktur 5m invalid: kirim SELL protektif.
- Jika stream stale: blokir entry baru; untuk posisi aktif lakukan rekonsiliasi REST dan gunakan kebijakan exit konservatif.
- Jika aplikasi restart: muat `open orders` dan posisi dari Private REST, lalu rekonstruksi Redis state sebelum trading kembali.

## 9. Data model MySQL

| Tabel | Kunci utama | Retensi / pola tulis |
|---|---|---|
| `pairs` | `pair_id` | UPSERT saat bootstrap/refresh |
| `pair_rules` | `pair_id` | UPSERT saat bootstrap/refresh |
| `market_summary_current` | `pair_id` | UPSERT, satu baris pair terbaru |
| `candles` | `(pair_id,timeframe,open_time)` | Insert hanya candle final |
| `trade_minute_stats` | `(pair_id,minute_time)` | Insert/UPSERT satu kali per menit |
| `orderbook_metrics` | `id` + index pair/waktu | Ringkasan 5–10 detik atau event penting |
| `watchlist` | `(pair_id,active_from)` | Riwayat seleksi pair |
| `signals` | `id` | Hanya perubahan keputusan/entry candidate |
| `orders` | `id`, `client_ref` unik | Semua intent dan perubahan status |
| `positions` | `id` | Satu siklus posisi spot |
| `trade_results` | `id` | Trade selesai, P/L dan fee final |
| `risk_events` | `id` | Block/cooldown/circuit breaker/stale data |
| `bot_runs`, `bot_events` | `id` | Operasional dan troubleshooting |

Tidak dibuat tabel `raw_ticks` permanen, `raw_orderbook_levels` permanen, atau polling log tanpa batas. Data granular terlalu mahal untuk manfaat awal yang kecil.

## 10. Redis keys

```text
live:summary:{pair}
live:tradeflow:{pair}:{minute}
live:orderbook:{pair}
live:candle:1m:{pair}
live:indicator:{pair}:{timeframe}
state:watchlist
state:position:{pair}
state:order_lock:{pair}
state:cooldown:{pair}
state:risk:daily
```

Seluruh state sementara memiliki TTL yang sesuai. MySQL tetap menjadi audit permanen untuk data yang memang perlu disimpan.

## 11. Proteksi wajib

1. Default `DRY_RUN=true` dan `ENABLE_LIVE_TRADING=false`.
2. API key hanya izin view dan trade; tanpa withdraw.
3. Satu posisi aktif maksimum pada tahap awal.
4. Semua order harus melewati risk gate; dashboard/AI tidak bisa memanggil executor langsung.
5. Semua nominal menggunakan `DECIMAL`, bukan float.
6. Semua timestamp dinormalisasi UTC; notifikasi dapat menampilkan WIB.
7. Rate limiter global untuk REST; WebSocket reconnect memakai exponential backoff.
8. `PAUSE_ENTRY` saat state data tidak sehat.
9. Recovery restart wajib merekonsiliasi open order/saldo sebelum entry baru.
10. Setiap order memiliki audit trail dari sinyal sampai P/L final.

## 12. Tahapan pembangunan dan acceptance criteria

| Tahap | Hasil | Lulus bila |
|---|---|---|
| A. Foundation | Compose, MySQL, Redis, config fail-closed | service sehat; tidak ada live endpoint aktif |
| B. Market Gateway | Public REST + WebSocket collector | reconnect dan stale detection teruji |
| C. Storage | migrasi tabel dan writer batch | candle tidak duplikat; query pair/time cepat |
| D. Candle/Indicators | 1m/5m/15m dan indikator incremental | hasil sama dengan data fixture yang diketahui |
| E. Strategy | gate 15m/5m/1m + microstructure | semua reason PASS/FAIL dapat diuji |
| F. Paper Executor | saldo simulasi, order/fill/SL/TP | tidak ada duplicate order; P/L bersih benar |
| G. Dashboard | status data, sinyal, posisi, audit | dashboard tidak memanggil Indodax langsung |
| H. Backtest | evaluasi data histori dengan biaya | out-of-sample dan drawdown dilaporkan |
| I. Paper Trading | data live tanpa uang nyata | hasil stabil selama periode yang disepakati |
| J. Live Gate | izin live eksplisit terpisah | hanya setelah audit, backup, dan persetujuan Kiky |

## 13. Metrik evaluasi

Win rate tidak dipakai sebagai satu-satunya ukuran. Laporan harus selalu memuat:

- jumlah trade;
- win rate;
- profit factor;
- expectancy setelah fee/slippage;
- rata-rata kemenangan dan kerugian;
- maximum drawdown;
- fill rate dan slippage aktual;
- jumlah entry yang ditolak serta alasannya;
- performa per pair, jam, dan kondisi market.

Sebuah konfigurasi tidak boleh dinaikkan modalnya hanya karena win rate tinggi dengan jumlah sampel kecil.

## 14. Definition of Done

Program dianggap selesai untuk versi paper trading apabila:

1. Semua modul Tahap A–G teruji otomatis dan dapat direstart tanpa kehilangan status order/posisi.
2. Bot dapat mengumpulkan data, membentuk candle, memilih pair, dan menghasilkan `WAIT_AND_SEE` atau plan trading secara deterministik.
3. Paper executor dapat menjalankan lifecycle order → fill → TP/SL → P/L tanpa duplikasi.
4. Dashboard dan Telegram menampilkan status yang konsisten dengan MySQL/Redis.
5. Backtest dan paper-trading report menampilkan metrik evaluasi lengkap.
6. Live trading tetap `OFF` sampai persetujuan eksplisit, terpisah, dan berbatas scope.
