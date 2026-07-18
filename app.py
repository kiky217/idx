#!/usr/bin/env python3
"""
INDODAX SCALPING MODE v2 — Real-time Dashboard
Flask app: monitoring + scalper control + live data.
Integrates: indodax_signal.py, executor.py, risk.py, scalper.py
"""
import os
import time
import hmac
import hashlib
import logging
import json
import threading
import pymysql
import pymysql.cursors
from datetime import datetime, timezone, timedelta
from threading import Thread, Lock
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template_string, request

from indodax_signal import SignalEngine, Signal
from executor import TradeExecutor
from risk import RiskManager, RiskConfig
from scalper import ScalperEngine
from pnl import PnLStorage
from telegram import test_bot, notify_daily

# ── config ──
INDODAX_BASE = "https://indodax.com"
PORT = int(os.environ.get("PORT", 8925))
API_KEY = os.environ.get("INDODAX_API_KEY", "")
API_SECRET = os.environ.get("INDODAX_API_SECRET", "")
UPDATE_INTERVAL = 10

log = logging.getLogger("idx")

# ── cache ──
_cache = {}
_lock = Lock()

def _set(k, v, ttl=None):
    with _lock:
        _cache[k] = {"val": v, "ts": time.time(), "ttl": ttl}

def _get(k):
    with _lock:
        e = _cache.get(k)
        if not e:
            return None
        if e["ttl"] and time.time() - e["ts"] > e["ttl"]:
            del _cache[k]
            return None
        return e["val"]

# ── TAPI ──
def tapi_request(method_name):
    if not API_KEY or not API_SECRET:
        return None
    ts = int(time.time() * 1000)
    body = f"method={method_name}&timestamp={ts}"
    sign = hmac.new(API_SECRET.encode(), body.encode(), hashlib.sha512).hexdigest()
    headers = {"Key": API_KEY, "Sign": sign, "Content-Type": "application/x-www-form-urlencoded"}
    try:
        r = requests.post(f"{INDODAX_BASE}/tapi", headers=headers, data=body, timeout=10)
        data = r.json()
        if data.get("success") == 1:
            return data.get("return", {})
        log.error(f"[tapi] {method_name}: {data.get('error','unknown')}")
    except Exception as e:
        log.error(f"[tapi] error: {e}")
    return None

def _get_owned_coins():
    info = tapi_request("getInfo")
    if not info:
        return []
    balance = info.get("balance", {})
    owned = [k for k, v in balance.items() if float(v) > 0]
    log.info(f"[idx] owned: {owned}")
    return owned

# ── background fetcher ──
def _fetch_all():
    owned_coins = []
    fetch_count = 0
    while True:
        try:
            if fetch_count % 30 == 0:
                new_owned = _get_owned_coins()
                if new_owned:
                    owned_coins = new_owned
                    _set("owned_coins", owned_coins)

            r = requests.get(f"{INDODAX_BASE}/api/ticker_all", timeout=8)
            all_t = {}
            if r.ok:
                all_t = r.json().get("tickers", {})
                _set("ticker_all", all_t)

            tickers = {}
            # R-009: Rank pairs by volume IDR instead of slice
            idr_pairs = [(pk, float(all_t[pk].get("vol_idr", 0))) for pk in all_t if pk.endswith("_idr")]
            idr_pairs.sort(key=lambda x: -x[1])  # highest volume first
            top_pairs = [pk for pk, _ in idr_pairs[:100]]
            for pk in top_pairs:
                tickers[pk] = all_t[pk]

            if tickers:
                _set("tickers", tickers)
                _set("age_ts", time.time())
                # R-010: Fetch depth for top pairs by volume, not just owned BTC
                top3 = top_pairs[:3]
                for pk in top3:
                    try:
                        d = requests.get(f"{INDODAX_BASE}/api/depth/{pk}", timeout=5)
                        if d.ok:
                            _set(f"depth_{pk}", d.json())
                    except:
                        pass
                for pair, data in tickers.items():
                    last = float(data.get("last", 0))
                    if last > 0:
                        vol_key = next((k for k in data if k.startswith("vol_")), None)
                        vol = float(data.get(vol_key, 0)) if vol_key else 0
                        push_chart_data(pair, last, vol)

            if scalper and scalper.running:
                for pair, data in tickers.items():
                    scalper.signal_engine.feed(pair, data)

            if any(c.lower() == "btc" for c in owned_coins):
                r2 = requests.get(f"{INDODAX_BASE}/api/depth/btc_idr", timeout=5)
                if r2.ok:
                    _set("depth_btc", r2.json())

            r4 = requests.get(f"{INDODAX_BASE}/api/server_time", timeout=5)
            if r4.ok:
                st = r4.json()
                ts = int(st.get("server_time", 0)) // 1000
                _set("server_time", {"ts": ts})

            fetch_count += 1
            log.info(f"[idx] refreshed {len(tickers)} owned tickers (total: {len(all_t)})")
        except Exception as e:
            log.error(f"[idx] fetch error: {e}")
        time.sleep(UPDATE_INTERVAL)

scalper = ScalperEngine()
pnl_storage = PnLStorage()
Thread(target=_fetch_all, daemon=True).start()

def fmt_harga(v):
    if v is None:
        return "—"
    try:
        return f"Rp{int(float(v)):,}"
    except:
        return str(v)

def _fmt_num(v):
    try:
        return f"Rp{int(float(v)):,}"
    except:
        return str(v)

# ── HTML ──
_HTML = """<!DOCTYPE html>
<html lang="id" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDX — Ultimate Pro Scalping Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #050505; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
        .card { background: #121212; border: 1px solid #2d2d2d; border-radius: 8px; }
        .chart-container { position: relative; height: 350px; width: 100%; }
        .stat-card { text-align: center; padding: 15px; }
        .nav-tabs .nav-link.active { background: #121212; border-color: #2d2d2d; color: #00d4aa; }
        .nav-tabs .nav-link { color: #6c757d; border: none; }
        .badge-status { font-size: 12px; }
        .config-item label { font-size: 12px; color: #6c757d; margin-bottom: 2px; }
        .config-item input, .config-item select { background: #1a1a1a; border: 1px solid #2d2d2d; color: #e0e0e0; border-radius: 4px; padding: 6px 8px; font-size: 13px; width: 100%; }
        .toast-notif { position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 250px; }
        .pulse { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #00d4aa; margin-right: 6px; animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
        .pair-item { display:flex; justify-content:space-between; align-items:center; padding:6px 10px; cursor:pointer; border-bottom:1px solid #2d2d2d; border-radius:4px; }
        .pair-item:hover { background:#1a1a1a; }
    </style>
</head>
<body>

<div id="toast" class="toast-notif" style="display:none"></div>

<div class="container-fluid p-4">

    <!-- Header -->
    <div class="row mb-3">
        <div class="col-lg-12 d-flex align-items-center justify-content-between">
            <div>
                <h3 class="text-success mb-1">⚡ INDODAX SCALPING MODE</h3>
                <small class="text-muted" id="uptime">{{ uptime }}</small>
                <span class="ms-3"><span class="pulse"></span><strong id="live-clock" class="text-success">{{ live_time }}</strong></span>
                <span class="ms-3 text-muted" id="utc-clock" style="font-size:12px"></span>
                <span class="ms-3 text-muted">Server: <strong id="stime">{{ stime }}</strong></span>
                <span class="ms-3 text-muted">Update: <strong id="age">{{ age }}</strong></span>
            </div>
            <div>
                <span class="badge border border-secondary text-secondary me-2" id="badge">💰 {{ owned_count }} aset</span>
                <span class="badge border border-secondary text-secondary me-2">Scalper: <strong id="scalper-mode" class="{{ 'text-success' if scalper_status.mode == 'LIVE' else 'text-secondary' }}">{{ scalper_status.mode }}</strong></span>
                <button class="btn {{ 'btn-danger' if scalper_status.running else 'btn-success' }} btn-sm px-3" id="btn-scalper" onclick="toggleScalper()">{{ 'STOP' if scalper_status.running else 'START' }}</button>
                <button class="btn btn-outline-danger btn-sm px-3 ms-1" onclick="showToast('Emergency kill would stop all trading','err')">EMERGENCY KILL</button>
            </div>
        </div>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4">
        <li class="nav-item"><a class="nav-link active" href="#" onclick="switchTab('dashboard')" id="nav-dashboard">Dashboard</a></li>
        <li class="nav-item"><a class="nav-link" href="#" onclick="switchTab('portfolio')" id="nav-portfolio">Portfolio</a></li>
        <li class="nav-item"><a class="nav-link" href="#" onclick="switchTab('chart')" id="nav-chart">Chart</a></li>
        <li class="nav-item"><a class="nav-link" href="#" onclick="switchTab('settings')" id="nav-settings">Settings</a></li>
    </ul>

    <!-- TAB: DASHBOARD -->
    <div id="tab-dashboard" class="tab-content">

    <!-- Stats Row -->
    <div class="row mb-3">
        <div class="col-lg-2"><div class="card stat-card"><h6 class="text-muted">Win Rate</h6><h4 class="text-success" id="pnl-winrate">{{ pnl_summary.win_rate }}%</h4></div></div>
        <div class="col-lg-2"><div class="card stat-card"><h6 class="text-muted">Net P/L</h6><h4 id="pnl-total-pnl" class="{{ 'text-success' if pnl_summary.total_pnl_idr >= 0 else 'text-danger' }}">Rp{{ '{:,.0f}'.format(pnl_summary.total_pnl_idr) }}</h4></div></div>
        <div class="col-lg-2"><div class="card stat-card"><h6 class="text-muted">Today P/L</h6><h4 class="{{ 'text-success' if pnl_summary.today.total_pnl >= 0 else 'text-danger' }}" id="pnl-today">Rp{{ '{:,.0f}'.format(pnl_summary.today.total_pnl) }}</h4></div></div>
        <div class="col-lg-2"><div class="card stat-card"><h6 class="text-muted">Trades Today</h6><h4 id="sp-trades">{{ scalper_status.trade_count_today }}</h4></div></div>
        <div class="col-lg-2"><div class="card stat-card"><h6 class="text-muted">Scans</h6><h4 id="sp-scans">{{ scalper_status.scan_count }}</h4></div></div>
        <div class="col-lg-2"><div class="card stat-card"><h6 class="text-muted">Errors</h6><h4 class="text-warning" id="sp-errors">{{ scalper_status.error_count }}</h4></div></div>
    </div>

    <!-- Pair Selector + Selected Pair Data -->
    <div class="row g-4">
        <!-- Left: Pair Search -->
        <div class="col-lg-3">
            <div class="card p-3">
                <h5 class="mb-3">🔍 Pilih Pair</h5>
                <input type="text" id="pairSearch" class="form-control mb-2" placeholder="Cari pair..." style="background:#1a1a1a;border:1px solid #2d2d2d;color:#e0e0e0" oninput="searchPairs()">
                <div id="pairList" style="max-height:400px;overflow-y:auto">
                    <div class="text-muted small p-2" id="pairListDefault">Sedang memuat data...</div>
                </div>
                <div class="mt-2">
                    <small class="text-muted" id="selected-pair-label">Belum ada pair dipilih</small>
                </div>
            </div>
        </div>

        <!-- Center-Right: Selected Pair Data -->
        <div class="col-lg-9">
            <!-- Selected Pair Header -->
            <div class="card p-3 mb-3" id="selected-pair-card" style="display:none">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h3 class="mb-0" id="sel-pair-name">-</h3>
                        <h2 class="mb-0" id="sel-pair-price" style="font-size:32px">-</h2>
                    </div>
                    <div class="text-end">
                        <div><small class="text-muted">High</small> <strong id="sel-pair-high">-</strong></div>
                        <div><small class="text-muted">Low</small> <strong id="sel-pair-low">-</strong></div>
                        <div><small class="text-muted">Volume</small> <strong id="sel-pair-vol">-</strong></div>
                    </div>
                </div>
            </div>

            <!-- Price Chart -->
            <div class="card p-3 mb-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h5 class="mb-0">Price Chart</h5>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-outline-secondary" onclick="setChartDur('15m')" id="dur-15m">15m</button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="setChartDur('30m')" id="dur-30m">30m</button>
                        <button class="btn btn-sm btn-outline-secondary active" onclick="setChartDur('1h')" id="dur-1h" style="border-color:#00d4aa;color:#00d4aa">1h</button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="setChartDur('4h')" id="dur-4h">4h</button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="setChartDur('1d')" id="dur-1d">1d</button>
                    </div>
                </div>
                <div class="chart-container"><canvas id="tradingChart"></canvas></div>
            </div>

            <!-- Scalper + Risk + Signals row -->
            <div class="row g-3">
                <div class="col-lg-4">
                    <div class="card p-3">
                        <h5>🤖 Scalper Engine</h5>
                        <div class="mb-2">
                            <div class="d-flex justify-content-between"><small class="text-muted">Status</small><strong id="sp-status">{{ 'RUNNING' if scalper_status.running else 'STOPPED' }}</strong></div>
                            <div class="d-flex justify-content-between"><small class="text-muted">Mode</small><strong id="sp-mode">{{ scalper_status.mode }}</strong></div>
                            <div class="d-flex justify-content-between"><small class="text-muted">Scans</small><strong id="sp-scans">{{ scalper_status.scan_count }}</strong></div>
                        </div>
                        <button class="btn {{ 'btn-danger' if scalper_status.running else 'btn-success' }} btn-sm w-100" id="btn-scalper" onclick="toggleScalper()">{{ 'STOP' if scalper_status.running else 'START' }}</button>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="card p-3">
                        <h5>🛡️ Risk</h5>
                        <div class="d-flex justify-content-between"><small class="text-muted">Daily Trades</small><strong id="rk-trades">{{ scalper_status.risk.daily_trades }}/{{ scalper_status.risk.daily_trades_limit }}</strong></div>
                        <div class="d-flex justify-content-between"><small class="text-muted">Daily Loss</small><strong id="rk-loss" class="text-warning">Rp{{ '{:,.0f}'.format(scalper_status.risk.daily_loss_idr) }}</strong></div>
                        <div class="d-flex justify-content-between"><small class="text-muted">Max Order</small><strong>Rp{{ '{:,.0f}'.format(scalper_status.risk.max_order_idr) }}</strong></div>
                    </div>
                </div>
                <div class="col-lg-4">
                    <div class="card p-3">
                        <h5>📡 Signal</h5>
                        <div id="selected-signal">
                            <p class="text-muted small mb-0">Pilih pair untuk lihat sinyal</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    </div>

    <!-- TAB: PORTFOLIO -->
    <div id="tab-portfolio" class="tab-content" style="display:none">
        <div class="row mb-3">
            <div class="col-lg-3"><div class="card stat-card"><h6 class="text-muted">Total Portfolio</h6><h4 class="text-success" id="pf-total">-</h4></div></div>
            <div class="col-lg-3"><div class="card stat-card"><h6 class="text-muted">IDR Cash</h6><h4 id="pf-cash">-</h4></div></div>
            <div class="col-lg-3"><div class="card stat-card"><h6 class="text-muted">BTC Value</h6><h4 id="pf-btc">-</h4></div></div>
            <div class="col-lg-3"><div class="card stat-card"><h6 class="text-muted">Assets</h6><h4 id="pf-count">-</h4></div></div>
        </div>
        <div class="card p-3">
            <h5>My Assets</h5>
            <div id="portfolio-table">
                <p class="text-muted small">Loading...</p>
            </div>
        </div>
    </div>

    <!-- TAB: CHART -->
    <div id="tab-chart" class="tab-content" style="display:none">
        <div class="card p-4">
            <h5>Price Chart</h5>
            <div class="chart-container" style="height:500px"><canvas id="priceChart"></canvas></div>
        </div>
    </div>

    <!-- TAB: SETTINGS -->
    <div id="tab-settings" class="tab-content" style="display:none">
        <div class="card p-4">
            <h5>Scalper Configuration</h5>
            <div class="row g-3 mt-2">
                <div class="col-md-3 config-item">
                    <label>Scan Interval (s)</label>
                    <input type="number" id="cfg-scan_interval" min="5" max="300" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Min Confidence</label>
                    <input type="number" id="cfg-min_confidence" min="0" max="1" step="0.05" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Mode 🔒</label>
                    <select id="cfg-dry_run" class="form-select" disabled><option value="true">DRY RUN</option></select>
                </div>
                <div class="col-md-3 config-item">
                    <label>Max Order (IDR)</label>
                    <input type="number" id="cfg-max_order_idr" min="10000" step="10000" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Min Order (IDR)</label>
                    <input type="number" id="cfg-min_order_idr" min="5000" step="5000" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Max Position (%)</label>
                    <input type="number" id="cfg-max_position_pct" min="0.05" max="1" step="0.05" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Max Daily Loss (IDR)</label>
                    <input type="number" id="cfg-max_daily_loss_idr" min="10000" step="50000" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Max Daily Trades</label>
                    <input type="number" id="cfg-max_daily_trades" min="1" max="200" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Cooldown (s)</label>
                    <input type="number" id="cfg-cooldown_seconds" min="5" max="300" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Min Hold (s)</label>
                    <input type="number" id="cfg-min_hold_seconds" min="10" max="3600" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Refresh (s)</label>
                    <input type="number" id="cfg-refresh_interval" min="2" max="60" class="form-control">
                </div>
                <div class="col-md-3 config-item">
                    <label>Default Chart Pair</label>
                    <select id="cfg-default_chart_pair" class="form-select"></select>
                </div>
            </div>
            <button class="btn btn-success mt-3 px-4" onclick="saveConfig()">Save Configuration</button>
            <span id="config-status" class="text-muted ms-3 small"></span>
        </div>
    </div>

    <!-- Footer -->
    <div class="row mt-4">
        <div class="col text-center">
            <small class="text-muted">IDX Scalping Mode &middot; <span id="mode-banner">{{ 'LIVE TRADING' if scalper_status.mode=='LIVE' else 'DRY RUN' }}</span> &middot; <span id="footer-time">{{ now }}</span></small>
        </div>
    </div>

</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
const WIB = 7;
let chartInstance = null;
let currentDuration = '1h', currentPair = '';
let allPairs = [];
let selectedPair = '';

function showToast(msg, type){
    const el = document.getElementById('toast');
    el.textContent = msg; el.style.display = 'block';
    el.className = 'toast-notif alert alert-'+(type==='err'?'danger':'success');
    setTimeout(()=>{el.style.display='none'}, 3000);
}

function tickClock(){
    const now = new Date(), utc = now.getTime() + now.getTimezoneOffset()*60000;
    const wib = new Date(utc + WIB*3600000);
    const t = String(wib.getHours()).padStart(2,'0')+':'+String(wib.getMinutes()).padStart(2,'0')+':'+String(wib.getSeconds()).padStart(2,'0')+' WIB';
    const ut = String(now.getUTCHours()).padStart(2,'0')+':'+String(now.getUTCMinutes()).padStart(2,'0')+':'+String(now.getUTCSeconds()).padStart(2,'0')+' UTC';
    document.getElementById('live-clock').textContent = t;
    document.getElementById('utc-clock').textContent = ut;
    document.getElementById('footer-time').textContent = wib.getFullYear()+'-'+String(wib.getMonth()+1).padStart(2,'0')+'-'+String(wib.getDate()).padStart(2,'0')+' '+t;
}
setInterval(tickClock, 1000); tickClock();

function switchTab(name){
    document.querySelectorAll('.tab-content').forEach(e=>e.style.display='none');
    document.querySelectorAll('.nav-link').forEach(e=>e.classList.remove('active'));
    document.getElementById('nav-'+name).classList.add('active');
    document.getElementById('tab-'+name).style.display = 'block';
    if(name==='chart') setTimeout(loadChart, 100);
    if(name==='settings') loadConfigForm();
    if(name==='portfolio') loadPortfolio();
    // Auto-refresh chart every 10s while visible
    if(window._chartTimer) clearInterval(window._chartTimer);
    if(name==='chart') window._chartTimer = setInterval(loadChart, 10000);
}

function selectPair(pair){
    selectedPair = pair;
    currentPair = pair;
    document.getElementById('selected-pair-label').textContent = pair.replace('_','/').toUpperCase();
    document.getElementById('selected-pair-card').style.display = 'block';
    // Update header
    const t = tickerData[pair]||{};
    document.getElementById('sel-pair-name').textContent = pair.replace('_','/').toUpperCase();
    document.getElementById('sel-pair-price').textContent = fmtRp(t.last||0);
    document.getElementById('sel-pair-high').textContent = fmtRp(t.high||0);
    document.getElementById('sel-pair-low').textContent = fmtRp(t.low||0);
    document.getElementById('sel-pair-vol').textContent = fmtN(t.vol||0);
    // Load chart
    switchTab('chart');
    setTimeout(loadChart, 100);
}

function searchPairs(){
    const q = document.getElementById('pairSearch').value.toLowerCase();
    const list = document.getElementById('pairList');
    let filtered = allPairs.filter(p=>p.toLowerCase().includes(q));
    let html = '';
    filtered.slice(0, 30).forEach(p=>{
        const t = tickerData[p]||{};
        const last = t.last||0;
        const isOwned = ownedCoins.some(oc=>p.includes(oc));
        html += '<div class="pair-item" data-pair="'+p+'">'+
            '<span><strong>'+p.replace('_','/').toUpperCase()+'</strong>'+(isOwned?' ✅':'')+'</span>'+
            '<span class="text-end"><small>'+fmtRp(last)+'</small></span></div>';
    });
    if(!filtered.length) html = '<div class="text-muted small p-2">Tidak ditemukan</div>';
    list.innerHTML = html;
    // Attach click handlers
    list.querySelectorAll('.pair-item').forEach(el=>{
        el.addEventListener('click', function(){ selectPair(this.dataset.pair); });
    });
}

async function loadPairs(){
    try{
        const r = await fetch('/api/pairs'), d = await r.json();
        const sel = document.getElementById('chart-pair'), def = document.getElementById('cfg-default_chart_pair');
        sel.innerHTML = d.pairs.map(p=>'<option value="'+p+'">'+p.replace('_','/').toUpperCase()+'</option>').join('');
        def.innerHTML = sel.innerHTML;
        if(!currentPair && d.pairs.length) currentPair = d.pairs[0];
        sel.value = currentPair;
    }catch(e){}
}

async function loadChart(){
    const pair = document.getElementById('chart-pair').value;
    if(!pair) { 
        // fallback ke pair pertama
        const sel = document.getElementById('chart-pair');
        if(sel.options.length > 0) {
            sel.value = sel.options[0].value;
            currentPair = sel.options[0].value;
        } else { return; }
    }
    currentPair = pair;
    try{
        const r = await fetch('/api/chart/'+pair+'?duration='+currentDuration);
        const data = await r.json();
        // Use correct canvas based on active tab
        const canvasId = document.getElementById('priceChart') ? 'priceChart' : 'tradingChart';
        const ctx = document.getElementById(canvasId).getContext('2d');
        if(chartInstance) chartInstance.destroy();
        if(data.length === 0){
            chartInstance = null;
            return;
        }
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: data.map(p=>new Date(p.ts).toLocaleTimeString('id-ID')), datasets: [{ label: pair.replace('_','/').toUpperCase(), data: data.map(p=>p.price), borderColor: '#00d4aa', backgroundColor: 'rgba(0,212,170,0.1)', fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color:'#6c757d', maxTicksLimit: 10 }, grid: { color:'#2d2d2d' } }, y: { ticks: { color:'#6c757d', callback: v=>'Rp'+Number(v).toLocaleString('id-ID') }, grid: { color:'#2d2d2d' } } } }
        });
    }catch(e){}
}

function setChartDur(dur){
    currentDuration = dur;
    document.querySelectorAll('.mt-2.d-flex .btn').forEach(b=>b.classList.remove('active'));
    loadChart();
}

async function toggleScalper(){
    const btn = document.getElementById('btn-scalper');
    const running = btn.textContent.includes('STOP');
    try{
        const r = await fetch('/api/scalper/'+(running?'stop':'start'), {method:'POST'});
        const d = await r.json();
        if(d.ok) showToast(running?'Scalper stopped':'Scalper started','ok');
        else showToast(d.msg||'Failed','err');
    }catch(e){ showToast('Network error','err'); }
}

function updateHealthStatus(sp){
    const dataReady = sp && sp.scan_count !== undefined;
    const btn = document.getElementById('btn-scalper');
    if(btn && !dataReady) {
        btn.disabled = true;
        btn.textContent = 'WAIT...';
        btn.className = 'btn btn-secondary btn-sm w-100';
    } else if(btn && dataReady) {
        btn.disabled = false;
    }
}

async function loadConfigForm(){
    try{
        const r = await fetch('/api/config'), cfg = await r.json();
        setCfg('scan_interval', cfg.scalper.scan_interval);
        setCfg('min_confidence', cfg.scalper.min_confidence);
        document.getElementById('cfg-dry_run').value = cfg.scalper.dry_run ? 'true' : 'false';
        setCfg('max_order_idr', cfg.risk.max_order_idr);
        setCfg('min_order_idr', cfg.risk.min_order_idr);
        setCfg('max_position_pct', cfg.risk.max_position_pct);
        setCfg('max_daily_loss_idr', cfg.risk.max_daily_loss_idr);
        setCfg('max_daily_trades', cfg.risk.max_daily_trades);
        setCfg('cooldown_seconds', cfg.risk.cooldown_seconds);
        setCfg('min_hold_seconds', cfg.risk.min_hold_seconds);
        setCfg('refresh_interval', cfg.ui.refresh_interval);
        if(cfg.ui.default_chart_pair) document.getElementById('cfg-default_chart_pair').value = cfg.ui.default_chart_pair;
        if(window._refreshTimer) clearInterval(window._refreshTimer);
        window._refreshTimer = setInterval(refreshData, (cfg.ui.refresh_interval||5)*1000);
    }catch(e){}
}
function setCfg(id, val){ const el=document.getElementById('cfg-'+id); if(el) el.value=val; }

async function loadPortfolio(){
    try{
        const r = await fetch('/api/portfolio');
        const d = await r.json();
        if(d.error){ document.getElementById('portfolio-table').innerHTML = '<p class="text-danger">'+d.error+'</p>'; return; }
        document.getElementById('pf-total').textContent = fmtRp(d.total_idr);
        document.getElementById('pf-total').className = d.total_idr >= 0 ? 'text-success' : 'text-danger';
        const cash = d.assets.find(a=>a.coin==='IDR');
        document.getElementById('pf-cash').textContent = cash ? fmtRp(cash.value_idr) : 'Rp0';
        document.getElementById('pf-btc').textContent = d.total_btc ? d.total_btc.toFixed(8)+' BTC' : '-';
        document.getElementById('pf-count').textContent = d.assets.length+(d.open_orders_count?' ('+d.open_orders_count+' orders)':'');
        // Compact list view — click to expand
        let html = '<div class="list-group list-group-flush" style="background:transparent">';
        d.assets.forEach(a=>{
            if(a.coin==='IDR' && a.amount <= 50000) return; // hide small IDR
            const locked = a.locked||0;
            const isLocked = locked > 0;
            const totalVal = a.value_idr;
            const pairName = a.coin.toLowerCase()+'_idr';
            const lockIcon = isLocked ? ' 🔒' : '';
            const pct = d.total_idr > 0 ? (totalVal/d.total_idr*100) : 0;
            html += '<div class="list-group-item d-flex justify-content-between align-items-center py-2 px-3" data-pair="'+pairName+'" style="background:#121212;border-color:#2d2d2d;cursor:pointer">'+
                '<div><strong>'+a.coin+'</strong>'+lockIcon+' <small class="text-muted">'+a.amount.toFixed(2)+'</small></div>'+
                '<div class="text-end"><span>'+fmtRp(totalVal)+'</span> <small class="text-muted ms-2">'+pct.toFixed(1)+'%</small></div></div>';
        });
        html += '</div>';
        if(d.assets.filter(a=>a.coin!=='IDR').length === 0) html = '<p class="text-muted p-3">Tidak ada aset</p>';
        document.getElementById('portfolio-table').innerHTML = html;
    }catch(e){ document.getElementById('portfolio-table').innerHTML = '<p class="text-danger">Load failed</p>'; }
}

async function saveConfig(){
    const data = {
        scalper: { scan_interval: +document.getElementById('cfg-scan_interval').value||30, min_confidence: +document.getElementById('cfg-min_confidence').value||0.6, dry_run: document.getElementById('cfg-dry_run').value === 'true' },
        risk: { max_order_idr: +document.getElementById('cfg-max_order_idr').value||50000, min_order_idr: +document.getElementById('cfg-min_order_idr').value||10000, max_position_pct: +document.getElementById('cfg-max_position_pct').value||0.3, max_daily_loss_idr: +document.getElementById('cfg-max_daily_loss_idr').value||200000, max_daily_trades: +document.getElementById('cfg-max_daily_trades').value||50, cooldown_seconds: +document.getElementById('cfg-cooldown_seconds').value||30, min_hold_seconds: +document.getElementById('cfg-min_hold_seconds').value||60 },
        ui: { refresh_interval: +document.getElementById('cfg-refresh_interval').value||5, default_chart_pair: document.getElementById('cfg-default_chart_pair').value||'btc_idr' }
    };
    try{
        const r = await fetch('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
        if(await r.json()) showToast('Configuration saved!','ok');
        document.getElementById('config-status').textContent = 'Saved at '+new Date().toLocaleTimeString();
    }catch(e){ showToast('Save failed','err'); }
}

const prevPrices = {};
let lastAge = '';
let allCoins = [];
let ownedCoins = [];
let viewMode = 'card';

function setView(mode){
    viewMode = mode;
    document.getElementById('view-card').className = 'btn btn-sm btn-outline-secondary'+(mode==='card'?' active':'');
    document.getElementById('view-list').className = 'btn btn-sm btn-outline-secondary'+(mode==='list'?' active':'');
    renderPairs();
}

function filterPairs(){ renderPairs(); }

function renderPairs(){
    const q = document.getElementById('pairSearch').value.toLowerCase();
    const f = document.getElementById('pairFilter').value;
    const sort = document.getElementById('pairSort').value;
    const grid = document.getElementById('tickers');
    // Filter
    let filtered = allCoins.filter(pair => {
        const p = pair.toLowerCase();
        if(!p.includes(q)) return false;
        if(f==='owned' && !ownedCoins.some(oc=>p.includes(oc))) return false;
        return true;
    });
    // Sort
    if(sort==='volume') filtered.sort((a,b)=> (tickerData[b]?.vol||0) - (tickerData[a]?.vol||0));
    else if(sort==='price') filtered.sort((a,b)=> (tickerData[b]?.last||0) - (tickerData[a]?.last||0));
    else filtered.sort();

    document.getElementById('pair-count').textContent = filtered.length+' pairs';

    if(viewMode==='list'){
        let html = '<div class="col-12"><div class="card p-2"><table class="table table-dark table-sm mb-0"><thead><tr><th>Pair</th><th style=\"text-align:right\">Price</th><th style=\"text-align:right\">Change</th><th style=\"text-align:right\">High</th><th style=\"text-align:right\">Low</th><th style=\"text-align:right\">Volume</th></tr></thead><tbody>';
        filtered.forEach(pair=>{
            const t = tickerData[pair]||{};
            const last = t.last||0, high = t.high||0, low = t.low||0, vol = t.vol||0;
            const chg = low>0 ? ((last-low)/low*100) : 0;
            const isOwned = ownedCoins.some(oc=>pair.includes(oc));
            html += '<tr style="cursor:pointer" onclick="selectPair(\\''+pair+'\\')" class="'+(isOwned?'':'')+'">'+
                '<td><strong>'+pair.replace('_','/').toUpperCase()+'</strong>'+(isOwned?' <span class=\"badge bg-success ms-1\">✓</span>':'')+'</td>'+
                '<td style=\"text-align:right\">'+fmtRp(last)+'</td>'+
                '<td style=\"text-align:right;color:'+(chg>=0?'var(--bs-success)':'var(--bs-danger)')+'">'+(chg>=0?'+':'')+chg.toFixed(2)+'%</td>'+
                '<td style=\"text-align:right\">'+fmtRp(high)+'</td>'+
                '<td style=\"text-align:right\">'+fmtRp(low)+'</td>'+
                '<td style=\"text-align:right\">'+fmtN(vol)+'</td></tr>';
        });
        html += '</tbody></table></div></div>';
        grid.innerHTML = html;
    } else {
        let html = '';
        filtered.forEach(pair=>{
            const t = tickerData[pair]||{};
            const last = parseFloat(t.last)||0, high = parseFloat(t.high)||0, low = parseFloat(t.low)||0;
            const pct = high>low ? Math.round((last-low)/(high-low)*100) : 50;
            const cls = pct>60?'text-success':pct<40?'text-danger':'';
            const vol = t.vol_btc||t.vol_ten||t.vol_eth||t.vol_usdt||'0';
            html += '<div class=\"col-lg-3 col-md-4 col-sm-6\"><div class=\"card p-3\" style=\"cursor:pointer\" onclick=\"selectPair(\\''+pair+'\\')\">'+
                '<div class=\"d-flex justify-content-between\"><span class=\"text-muted small\">'+pair.replace('_','/').toUpperCase()+'</span></div>'+
                '<h4 class=\"mb-0 '+cls+'\">'+fmtRp(last)+'</h4>'+
                '<small class=\"text-muted\">H: '+fmtRp(high)+' L: '+fmtRp(low)+'</small></div></div>';
        });
        grid.innerHTML = html;
    }
}

let tickerData = {};

async function refreshData(){
    try{
        const res = await fetch('/api/live'), d = await res.json();
        if(d.age !== lastAge){ document.getElementById('age').textContent = d.age; lastAge = d.age; }
        document.getElementById('stime').textContent = d.stime;
        document.getElementById('uptime').textContent = d.uptime;

        const grid = document.getElementById('tickers'), coins = Object.keys(d.tickers||{});
        ownedCoins = d.owned_coins || [];
        allCoins = coins.filter(p=>p.endsWith('_idr'));
        allPairs = allCoins;
        // Build tickerData
        tickerData = {};
        coins.forEach(pair=>{
            const t = d.tickers[pair];
            tickerData[pair] = {
                last: parseFloat(t.last)||0,
                high: parseFloat(t.high)||0,
                low: parseFloat(t.low)||0,
                vol: parseFloat(t.vol_btc||t.vol_ten||t.vol_eth||t.vol_usdt||0),
            };
        });
        let html = '';
        coins.forEach(pair=>{
            const coin = pair.split('_')[0], t = d.tickers[pair];
            const last = parseFloat(t.last)||0, high = parseFloat(t.high)||0, low = parseFloat(t.low)||0;
            const pct = high>low ? Math.round((last-low)/(high-low)*100) : 50;
            const cls = pct>60?'text-success':pct<40?'text-danger':'';
            prevPrices[coin] = last;
        });
        renderPairs();
        
        // Update selected pair data if any
        if(selectedPair && tickerData[selectedPair]){
            const t = tickerData[selectedPair];
            document.getElementById('sel-pair-price').textContent = fmtRp(t.last||0);
            document.getElementById('sel-pair-high').textContent = fmtRp(t.high||0);
            document.getElementById('sel-pair-low').textContent = fmtRp(t.low||0);
            document.getElementById('sel-pair-vol').textContent = fmtN(t.vol||0);
        }

        const sp = d.scalper_status||{};
        updateHealthStatus(sp);
        document.getElementById('sp-status').textContent = sp.running?'RUNNING':'STOPPED';
        document.getElementById('sp-status').className = sp.running?'text-success':'text-danger';
        setText('sp-mode', sp.mode||'?'); setText('sp-scans', sp.scan_count||0);
        setText('sp-errors', sp.error_count||0); setText('sp-minconf', sp.min_confidence||0.6);
        setText('sp-trades', sp.trade_count_today||0);
        const sBtn = document.getElementById('btn-scalper');
        if(sBtn){ sBtn.textContent = sp.running?'STOP':'START'; sBtn.className = 'btn btn-sm px-3 '+(sp.running?'btn-danger':'btn-success'); }
        setText('rk-trades', (sp.risk?.daily_trades||0)+'/'+(sp.risk?.daily_trades_limit||50));
        setText('rk-loss', 'Rp'+fmtN(sp.risk?.daily_loss_idr||0));
        document.getElementById('mode-banner').textContent = sp.mode==='LIVE'?'LIVE TRADING':'DRY RUN';
    }catch(e){}
}

function fmtRp(v){ return 'Rp'+Number(v).toLocaleString('id-ID',{maximumFractionDigits:0}) }
function fmtN(v){ return Number(v).toLocaleString('id-ID',{maximumFractionDigits:0}) }
function setText(id,v){ const e=document.getElementById(id); if(e) e.textContent=v }

loadPairs(); refreshData();
setInterval(refreshData, 5000);
// Populate allPairs from /api/pairs on load
fetch('/api/pairs').then(r=>r.json()).then(d=>{ allPairs = d.pairs.filter(p=>p.endsWith('_idr')); }).catch(()=>{});
</script>
</body></html>"""


# ── Flask ──
app = Flask(__name__)
_start = time.time()
WIB = timezone(timedelta(hours=7))

# ── config persistence ──
CONFIG_PATH = Path(os.environ.get("DATA_DIR", "/app/data")) / "config.json"

DEFAULT_CONFIG = {
    "scalper": {"scan_interval": 30, "min_confidence": 0.6, "dry_run": True, "mode": "DRY_RUN"},
    "risk": {
        "max_order_idr": 50000, "min_order_idr": 10000, "max_position_pct": 0.30,
        "max_total_exposure_pct": 0.80, "max_loss_per_trade_pct": 0.02,
        "max_daily_loss_idr": 200000, "max_daily_trades": 50,
        "cooldown_seconds": 30, "min_hold_seconds": 60,
        "rate_limit_rps": 5, "rate_limit_block_seconds": 5,
    },
    "ui": {"refresh_interval": 5, "default_chart_pair": "btc_idr", "chart_duration": "1h"},
}

_config_lock = threading.Lock()

def load_config():
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            # S-01: Always force dry_run unless ENABLE_LIVE_TRADING=true
            if os.environ.get("ENABLE_LIVE_TRADING", "").lower() != "true":
                cfg.setdefault("scalper", {})["dry_run"] = True
                cfg.setdefault("scalper", {})["mode"] = "DRY_RUN"
            return cfg
    except Exception as e:
        log.warning(f"[config] load failed: {e}")
    cfg = dict(DEFAULT_CONFIG)
    return cfg

def save_config(cfg):
    with _config_lock:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        return cfg

APP_CONFIG = load_config()

# ── MySQL ──
DB_CONFIG = {
    "host": os.environ.get("IDX_DB_HOST"),
    "port": int(os.environ.get("IDX_DB_PORT", 3306)),
    "user": os.environ.get("IDX_DB_USER"),
    "password": os.environ.get("IDX_DB_PASSWORD"),
    "database": os.environ.get("IDX_DB_NAME"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

def get_db():
    # S-16: Fail-closed — no default credentials
    if not DB_CONFIG["host"] or not DB_CONFIG["user"] or not DB_CONFIG["password"] or not DB_CONFIG["database"]:
        raise RuntimeError("MySQL not configured. Set IDX_DB_HOST, IDX_DB_USER, IDX_DB_PASSWORD, IDX_DB_NAME env vars.")
    return pymysql.connect(**DB_CONFIG)

def db_exec(sql, params=None):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            return cur
    finally:
        conn.close()

def db_insert(table, data):
    cols = ", ".join(data.keys())
    vals = ", ".join(["%s"] * len(data))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
    return db_exec(sql, list(data.values()))

def db_query(sql, params=None, one=False):
    cur = db_exec(sql, params)
    return cur.fetchone() if one else cur.fetchall()

# ── chart data ring buffer ──
CHART_DATA = {}
CHART_LOCK = threading.Lock()
MAX_CHART_POINTS = 500

def push_chart_data(pair, price, volume=0):
    with CHART_LOCK:
        if pair not in CHART_DATA:
            CHART_DATA[pair] = []
        CHART_DATA[pair].append({"ts": int(time.time()*1000), "price": price, "volume": volume})
        if len(CHART_DATA[pair]) > MAX_CHART_POINTS:
            CHART_DATA[pair] = CHART_DATA[pair][-MAX_CHART_POINTS:]

def get_chart_data(pair, duration_min=60):
    with CHART_LOCK:
        if pair not in CHART_DATA: return []
        cutoff = int(time.time()*1000) - duration_min*60*1000
        return [p for p in CHART_DATA[pair] if p["ts"] >= cutoff]

# ── API Key Auth (S-02/R-003) ──
AUTH_ENABLED = os.environ.get("DASHBOARD_API_KEY", "")

def require_api_key():
    if not AUTH_ENABLED:
        return jsonify({"error": "Authentication not configured. Set DASHBOARD_API_KEY in environment."}), 503
    key = request.headers.get("X-API-Key", "")
    if key != AUTH_ENABLED:
        return jsonify({"error": "Unauthorized. Invalid or missing X-API-Key header."}), 401
    return None

# ── Health check (S-03) ──
def system_healthy():
    issues = []
    # Market data
    tickers = _get("tickers")
    if not tickers or len(tickers) == 0:
        issues.append("market_data: no tickers")
    # Server time freshness
    age_ts = _get("age_ts")
    if age_ts and time.time() - age_ts > 30:
        issues.append(f"market_data: stale ({int(time.time()-age_ts)}s)")
    # MySQL
    try:
        db_exec("SELECT 1")
    except RuntimeError as e:
        issues.append(f"mysql: {e}")
    except Exception:
        issues.append("mysql: unreachable")
    else:
        # Pair rules — only check if MySQL is reachable
        try:
            cur = db_exec("SELECT COUNT(*) as c FROM pairs")
            row = cur.fetchone()
            if row and row.get("c", 0) == 0:
                issues.append("pair_rules: empty")
        except Exception as e:
            issues.append(f"pair_rules: error ({e})")
    return issues

@app.route("/")
def landing():
    tickers = _get("tickers") or {}
    depth = _get("depth_btc")
    st = _get("server_time") or {}
    stime = datetime.fromtimestamp(st.get("ts", 0), tz=WIB).strftime("%H:%M:%S WIB") if st else "—"
    us = int(time.time() - _start)
    uptime = f"{us//3600}h{(us%3600)//60}m"
    age_val = _get("age_ts")
    age = f"{int(time.time()-age_val)}s lalu" if age_val else "baru"
    scalper_status = scalper.get_status()
    live_time = datetime.now(tz=WIB).strftime("%H:%M:%S WIB")

    return render_template_string(
        _HTML, tickers=tickers, depth=depth, stime=stime,
        uptime=uptime, age=age, live_time=live_time,
        now=datetime.now(tz=WIB).strftime("%Y-%m-%d %H:%M:%S"),
        fmt=fmt_harga, owned_count=len(tickers),
        scalper_status=scalper_status,
        signals=scalper_status.get("signals", {}),
        trade_log=scalper.executor.get_trade_log(10),
        pnl_summary=pnl_storage.get_summary(),
    )

@app.route("/api/live")
def api_live():
    """Lightweight JSON for JS auto-refresh — all data in one call."""
    tickers = _get("tickers") or {}
    st = _get("server_time") or {}
    stime = datetime.fromtimestamp(st.get("ts", 0), tz=WIB).strftime("%H:%M:%S WIB") if st else "—"
    us = int(time.time() - _start)
    uptime = f"{us//3600}h{(us%3600)//60}m"
    age_val = _get("age_ts")
    age = f"{int(time.time()-age_val)}s lalu" if age_val else "baru"

    return jsonify({
        "tickers": {k: {"last": v.get("last"), "high": v.get("high"), "low": v.get("low"),
                        "buy": v.get("buy"), "sell": v.get("sell"),
                        **{kk: vv for kk, vv in v.items() if kk.startswith("vol_")}}
                    for k, v in tickers.items()},
        "owned_coins": _get("owned_coins") or [],
        "scalper_status": scalper.get_status(),
        "stime": stime,
        "uptime": uptime,
        "age": age,
    })

@app.route("/health")
def health():
    issues = system_healthy()
    sp = scalper.get_status()
    return jsonify({
        "status": "ok" if len(issues) == 0 else "degraded",
        "issues": issues,
        "uptime": int(time.time() - _start),
        "cached_pairs": len(_get("tickers") or {}),
        "scalper_running": sp.get("running"),
        "mode": sp.get("mode"),
    })

@app.route("/api/scalper/status")
def scalper_status_api():
    return jsonify(scalper.get_status())

@app.route("/api/scalper/start", methods=["POST"])
def scalper_start():
    auth = require_api_key()
    if auth: return auth
    # S-03: Full health gate
    issues = system_healthy()
    if issues:
        return jsonify({"ok": False, "msg": "System not healthy", "issues": issues}), 503
    if scalper.running:
        return jsonify({"ok": False, "msg": "already running"})
    tickers_fn = lambda: _get("tickers") or {}
    scalper.start(tickers_fn)
    return jsonify({"ok": True, "mode": scalper.mode})

@app.route("/api/scalper/stop", methods=["POST"])
def scalper_stop():
    auth = require_api_key()
    if auth: return auth
    scalper.stop()
    return jsonify({"ok": True})

@app.route("/api/scalper/trades")
def scalper_trades():
    return jsonify(scalper.executor.get_trade_log(50))

@app.route("/api/tickers")
def api_tickers():
    at = _get("ticker_all") or {}
    return jsonify({"count": len(at), "tickers": at, "source": "cache"})

@app.route("/ticker/<pair>")
def ticker(pair):
    at = _get("ticker_all") or {}
    if pair in at:
        return jsonify({"ticker": at[pair], "source": "cache"})
    try:
        r = requests.get(f"{INDODAX_BASE}/api/ticker/{pair}", timeout=5)
        return (r.content, r.status_code, {"Content-Type": "application/json"})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ── Portfolio API ──

@app.route("/api/portfolio")
def api_portfolio():
    auth = require_api_key()
    if auth: return auth
    info = tapi_request("getInfo")
    if not info:
        return jsonify({"error": "TAPI failed"}), 502
    balance = info.get("balance", {})
    balance_idr = info.get("balance_idr", {})

    # Fetch open orders untuk locked assets
    open_orders_raw = tapi_request("openOrders")
    locked_coins = {}
    if open_orders_raw and isinstance(open_orders_raw, dict):
        orders_dict = open_orders_raw.get("orders", {})
        for pair, ords in orders_dict.items():
            coin = pair.split("_")[0]
            if isinstance(ords, list):
                for o in ords:
                    amt = float(o.get("order_btc", o.get("order_" + coin, o.get("amount", 0))))
                    locked_coins[coin] = locked_coins.get(coin, 0) + amt

    # Get tickers for price conversion
    all_t = _get("ticker_all") or {}
    assets = []
    total_idr = float(balance.get("idr", 0))

    # Process available balance
    for coin, amount in balance.items():
        amt = float(amount)
        if amt <= 0:
            continue
        pair = f"{coin}_idr"
        ticker = all_t.get(pair, {})
        last_price = float(ticker.get("last", 0))
        value_idr = amt * last_price if last_price > 0 else 0
        if coin == "idr":
            value_idr = amt
        assets.append({
            "coin": coin.upper(),
            "amount": round(amt, 8),
            "price_idr": last_price,
            "value_idr": round(value_idr, 2),
            "locked": 0,
            "status": "available",
        })
        if coin != "idr":
            total_idr += value_idr

    # Process locked assets from open orders
    for coin, amt in locked_coins.items():
        if amt <= 0:
            continue
        pair = f"{coin}_idr"
        ticker = all_t.get(pair, {})
        last_price = float(ticker.get("last", 0))
        value_idr = amt * last_price if last_price > 0 else 0
        # Check if already in assets list
        existing = [a for a in assets if a["coin"] == coin.upper()]
        if existing:
            existing[0]["locked"] = round(amt, 8)
            existing[0]["amount"] = round(existing[0]["amount"] + amt, 8)
            existing[0]["value_idr"] = round(
                (float(balance.get(coin, 0)) + amt) * last_price if last_price > 0 else 0, 2
            )
        else:
            assets.append({
                "coin": coin.upper(),
                "amount": round(amt, 8),
                "price_idr": last_price,
                "value_idr": round(value_idr, 2),
                "locked": round(amt, 8),
                "status": "locked",
            })
        if coin.lower() != "idr":
            total_idr += value_idr

    assets.sort(key=lambda x: -x["value_idr"])
    return jsonify({
        "assets": assets,
        "total_idr": round(total_idr, 2),
        "total_btc": float(balance_idr.get("btc", 0)) if balance_idr else 0,
        "open_orders_count": sum(len(v) if isinstance(v, list) else 0 for v in (open_orders_raw or {}).get("orders", {}).values()),
    })


@app.route("/api/pnl/summary")
def pnl_summary():
    auth = require_api_key()
    if auth: return auth
    return jsonify(pnl_storage.get_summary())

@app.route("/api/pnl/trades")
def pnl_trades():
    auth = require_api_key()
    if auth: return auth
    pair = request.args.get("pair")
    limit = int(request.args.get("limit", 50))
    return jsonify(pnl_storage.get_trades(limit=limit, pair=pair))

@app.route("/api/pnl/daily")
def pnl_daily():
    auth = require_api_key()
    if auth: return auth
    days = int(request.args.get("days", 30))
    return jsonify(pnl_storage.get_daily_pnl(days=days))


@app.route("/api/telegram/test", methods=["POST"])
def telegram_test():
    auth = require_api_key()
    if auth: return auth
    ok = test_bot()
    return jsonify({"ok": ok})

@app.route("/api/telegram/daily", methods=["POST"])
def telegram_daily_route():
    ok = notify_daily(pnl_storage.get_summary())
    return jsonify({"ok": ok})


# ── Config API ──

@app.route("/api/config", methods=["GET"])
def api_config_get():
    return jsonify(APP_CONFIG)

@app.route("/api/config", methods=["POST"])
def api_config_set():
    auth = require_api_key()
    if auth: return auth
    global APP_CONFIG, scalper
    data = request.get_json(force=True) or {}
    
    # S-01: Check dry_run BEFORE saving anything
    scalper_cfg = data.get("scalper", {})
    if scalper_cfg.get("dry_run") is not None and not scalper_cfg["dry_run"]:
        # Check if ENABLE_LIVE_TRADING env allows it
        if os.environ.get("ENABLE_LIVE_TRADING", "").lower() != "true":
            return jsonify({"error": "LIVE mode is disabled. Set ENABLE_LIVE_TRADING=true in environment to enable."}), 403
    
    # deep merge
    merged = dict(DEFAULT_CONFIG)
    for section in ("scalper", "risk", "ui"):
        if section in APP_CONFIG:
            merged[section] = {**merged[section], **APP_CONFIG[section]}
        if section in data:
            merged[section] = {**merged[section], **data[section]}
    
    # S-01: Force DRY_RUN in merged config (env var can override)
    if os.environ.get("ENABLE_LIVE_TRADING", "").lower() != "true":
        merged["scalper"]["dry_run"] = True
        merged["scalper"]["mode"] = "DRY_RUN"
    
    APP_CONFIG = save_config(merged)
    
    # apply to running scalper (safely)
    sc = APP_CONFIG.get("scalper", {})
    rk = APP_CONFIG.get("risk", {})
    scalper.scan_interval = int(sc.get("scan_interval", scalper.scan_interval))
    scalper.min_confidence = float(sc.get("min_confidence", scalper.min_confidence))
    # Always enforce DRY_RUN mode
    scalper.mode = "DRY_RUN"
    scalper.executor.dry_run = True
    # update risk config
    if hasattr(scalper.risk_manager, "cfg"):
        cfg = scalper.risk_manager.cfg
        for k, v in rk.items():
            if hasattr(cfg, k):
                setattr(cfg, k, type(getattr(cfg, k))(v))
    return jsonify(APP_CONFIG)


# ── Chart API ──

@app.route("/api/chart/<pair>")
def api_chart(pair):
    duration = request.args.get("duration", "1h")
    dur_map = {"15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
    minutes = dur_map.get(duration, 60)
    return jsonify(get_chart_data(pair, minutes))


@app.route("/api/pairs")
def api_pairs():
    tickers = _get("tickers") or {}
    return jsonify({"pairs": list(tickers.keys())})

@app.route("/api/<path:path>")
def proxy(path):
    try:
        r = requests.get(f"{INDODAX_BASE}/api/{path}", timeout=8, params=request.args)
        return (r.content, r.status_code, {"Content-Type": "application/json"})
    except Exception as e:
        return jsonify({"error": str(e)}), 502

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    log.info(f"🔥 IDX scalping mode v2 starting on port {PORT} (mode={scalper.mode})")
    app.run(host="0.0.0.0", port=PORT, debug=False)
