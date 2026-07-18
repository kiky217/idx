#!/usr/bin/env python3
"""
Scalper Engine — otak utama INDODAX SCALPING MODE.
Menghubungkan: signal.py (sinyal) + executor.py (order) + risk.py (pengaman).
Loop: ambil data → generate sinyal → cek risk → eksekusi (dry-run/live).
"""
import os
import time
import json
import logging
from datetime import datetime
from threading import Thread, Lock

from indodax_signal import SignalEngine, Signal
from executor import TradeExecutor
from risk import RiskManager, RiskConfig

log = logging.getLogger("idx.scalper")


class ScalperEngine:
    def __init__(self):
        # --- config from env ---
        dry_run = os.environ.get("SCALPER_DRY_RUN", "true").lower() != "false"
        max_order = float(os.environ.get("SCALPER_MAX_ORDER_IDR", "50000"))
        max_daily_loss = float(os.environ.get("SCALPER_MAX_DAILY_LOSS", "200000"))

        # --- modules ---
        self.signal_engine = SignalEngine()
        self.executor = TradeExecutor(dry_run=dry_run)
        self.risk_manager = RiskManager(RiskConfig(
            max_order_idr=max_order,
            max_daily_loss_idr=max_daily_loss,
        ))

        # --- state ---
        self.running = False
        self.scan_interval = int(os.environ.get("SCALPER_SCAN_INTERVAL", "30"))
        self.min_confidence = float(os.environ.get("SCALPER_MIN_CONFIDENCE", "0.6"))
        self.mode = "DRY_RUN" if dry_run else "LIVE"
        self._lock = Lock()

        # --- results cache ---
        self.signals = {}           # pair -> last Signal
        self.trades_today = []      # today's trade log
        self.last_scan_ts = 0
        self.scan_count = 0
        self.error_count = 0
        self.start_ts = time.time()

    def start(self, ticker_fetcher):
        """
        Start scalping loop in background thread.
        ticker_fetcher: callable returning dict of {pair: ticker_data}
        """
        if self.running:
            log.warning("[scalper] already running")
            return

        self.running = True
        self._ticker_fetcher = ticker_fetcher
        Thread(target=self._loop, daemon=True, name="scalper").start()
        log.info(f"[scalper] STARTED mode={self.mode} interval={self.scan_interval}s min_conf={self.min_confidence}")

    def stop(self):
        self.running = False
        log.info("[scalper] STOPPED")

    def _loop(self):
        """Main scalping loop."""
        # warmup: collect data for 30 ticks before generating signals
        warmup_ticks = 30
        tick = 0

        while self.running:
            try:
                tickers = self._ticker_fetcher()
                if not tickers:
                    time.sleep(self.scan_interval)
                    continue

                # feed all pairs to signal engine
                for pair, data in tickers.items():
                    self.signal_engine.feed(pair, data)

                tick += 1

                if tick < warmup_ticks:
                    # still warming up
                    if tick % 10 == 0:
                        log.info(f"[scalper] warming up... tick {tick}/{warmup_ticks}")
                    time.sleep(self.scan_interval)
                    continue

                # --- analyze all owned pairs ---
                new_signals = {}
                for pair in self.signal_engine.history:
                    if self.signal_engine.get_history_count(pair) < 25:
                        continue
                    signal = self.signal_engine.analyze(pair)
                    new_signals[pair] = signal

                with self._lock:
                    self.signals = new_signals
                    self.last_scan_ts = time.time()
                    self.scan_count += 1

                # --- process signals ---
                self._process_signals(new_signals, tickers)

                log.info(f"[scalper] scan #{self.scan_count} — {len(new_signals)} pairs analyzed")

            except Exception as e:
                self.error_count += 1
                log.error(f"[scalper] error: {e}")

            time.sleep(self.scan_interval)

    def _process_signals(self, signals: dict, tickers: dict):
        """Check signals against risk rules and execute if allowed."""
        # get balance for risk check
        balance = self.executor.get_idr_balance()

        for pair, signal in signals.items():
            if signal.action == "HOLD":
                continue
            if signal.confidence < self.min_confidence:
                log.info(f"[scalper] {pair} signal={signal.action} conf={signal.confidence:.2f} < min={self.min_confidence} → SKIP")
                continue

            # calculate order size
            order_idr = min(self.risk_manager.cfg.max_order_idr,
                           balance * self.risk_manager.cfg.max_position_pct)

            if signal.action == "BUY":
                # risk check
                ok, reason = self.risk_manager.can_trade(pair, order_idr, balance)
                if not ok:
                    log.info(f"[scalper] {pair} BUY blocked: {reason}")
                    continue

                log.info(f"[scalper] {pair} BUY signal conf={signal.confidence:.2f} price={signal.price:,.0f} idr={order_idr:,.0f}")
                result = self.executor.place_limit_buy(pair, signal.price, order_idr)

            elif signal.action == "SELL":
                # sell: check if we have the coin
                coin = pair.split("_")[0]
                owned = self.executor.get_owned_coins()
                if coin not in owned:
                    log.info(f"[scalper] {pair} SELL signal but no {coin} balance → SKIP")
                    continue

                log.info(f"[scalper] {pair} SELL signal conf={signal.confidence:.2f} price={signal.price:,.0f}")
                result = self.executor.place_market_sell(pair, 0)  # amount=0 means sell all
            else:
                continue

            # record trade
            if result:
                self.risk_manager.record_trade(pair, 0)
                self.trades_today.append(result)
                # keep last 100 trades
                if len(self.trades_today) > 100:
                    self.trades_today = self.trades_today[-100:]

    def get_status(self) -> dict:
        with self._lock:
            uptime = int(time.time() - self.start_ts)
            return {
                "running": self.running,
                "mode": self.mode,
                "scan_count": self.scan_count,
                "error_count": self.error_count,
                "last_scan": datetime.fromtimestamp(self.last_scan_ts).isoformat() if self.last_scan_ts else "never",
                "uptime": f"{uptime//3600}h{(uptime%3600)//60}m{uptime%60}s",
                "scan_interval": self.scan_interval,
                "min_confidence": self.min_confidence,
                "signals": {
                    pair: {
                        "action": sig.action,
                        "confidence": round(sig.confidence, 3),
                        "price": sig.price,
                        "reasons": sig.reasons,
                        "indicators": sig.indicators,
                    }
                    for pair, sig in self.signals.items()
                    if sig.action != "HOLD"
                },
                "trade_count_today": len(self.trades_today),
                "risk": self.risk_manager.get_status(),
                "executor": self.executor.get_status(),
                "signal_history_count": {
                    pair: self.signal_engine.get_history_count(pair)
                    for pair in list(self.signal_engine.history.keys())[:10]
                },
            }
