#!/usr/bin/env python3
"""
Risk Manager — batas aman untuk scalping.
"""
import time
import logging
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict
from pathlib import Path

log = logging.getLogger("idx.risk")


@dataclass
class RiskConfig:
    # --- per-trade limits ---
    max_order_idr: float = 50_000        # max IDR per order
    min_order_idr: float = 10_000        # min IDR per order
    # --- position limits ---
    max_position_pct: float = 0.30       # max 30% saldo per koin
    max_total_exposure_pct: float = 0.80 # max 80% saldo total
    # --- loss limits ---
    max_loss_per_trade_pct: float = 0.02 # stop-loss 2% dari entry
    max_daily_loss_idr: float = 200_000  # max rugi/hari
    max_daily_trades: int = 50           # max trade/hari
    # --- timing ---
    cooldown_seconds: int = 30           # jeda antar order per pair
    min_hold_seconds: int = 60           # minimal hold posisi
    # --- rate limit (indodax: 20 req/s per pair) ---
    rate_limit_rps: int = 5              # batas aman kita
    rate_limit_block_seconds: int = 5    # block jika kena rate limit


@dataclass
class TradeState:
    """State per pair untuk risk check."""
    last_trade_ts: Dict[str, float] = field(default_factory=dict)
    daily_trades: int = 0
    daily_loss_idr: float = 0.0
    daily_reset_ts: float = 0.0
    _reset_day: int = 0  # R-011: calendar day tracking


class RiskManager:
    def __init__(self, config: RiskConfig = None):
        self.cfg = config or RiskConfig()
        self.state = TradeState()
        self._persist_path = Path(os.environ.get("DATA_DIR", "/app/data")) / "risk_state.json"
        self._load_state()
    
    def _load_state(self):
        """R-007: Load risk state from disk."""
        try:
            if self._persist_path.exists():
                with open(self._persist_path) as f:
                    data = json.load(f)
                self.state.daily_trades = data.get("daily_trades", 0)
                self.state.daily_loss_idr = data.get("daily_loss_idr", 0.0)
                self.state.daily_reset_ts = data.get("daily_reset_ts", 0.0)
                self.state._reset_day = data.get("reset_day", 0)
        except Exception as e:
            log.warning(f"[risk] load state failed: {e}")
    
    def _save_state(self):
        """R-007: Persist risk state to disk."""
        try:
            data = {
                "daily_trades": self.state.daily_trades,
                "daily_loss_idr": self.state.daily_loss_idr,
                "daily_reset_ts": self.state.daily_reset_ts,
                "reset_day": self.state._reset_day,
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            log.warning(f"[risk] save state failed: {e}")

    def reset_daily_if_needed(self):
        # R-011: Calendar-based reset (UTC)
        today = time.gmtime().tm_yday  # day of year (1-366)
        if today != self.state._reset_day:
            self.state.daily_trades = 0
            self.state.daily_loss_idr = 0.0
            self.state.daily_reset_ts = time.time()
            self.state._reset_day = today
    
    def get_total_exposure(self, balance_idr: float, open_positions_value: float = 0) -> float:
        """R-012: Calculate total exposure ratio."""
        if balance_idr <= 0:
            return 0
        return (open_positions_value + self.state.daily_loss_idr) / balance_idr

    def can_trade(self, pair: str, order_idr: float, balance_idr: float) -> tuple:
        """Returns (ok: bool, reason: str)."""
        self.reset_daily_if_needed()

        # daily trade limit
        if self.state.daily_trades >= self.cfg.max_daily_trades:
            return False, f"daily_trade_limit ({self.cfg.max_daily_trades})"

        # daily loss limit
        if self.state.daily_loss_idr >= self.cfg.max_daily_loss_idr:
            return False, f"daily_loss_limit (Rp{self.state.daily_loss_idr:,.0f})"

        # order size limits
        if order_idr < self.cfg.min_order_idr:
            return False, f"below_min_order (Rp{order_idr:,.0f} < Rp{self.cfg.min_order_idr:,.0f})"
        if order_idr > self.cfg.max_order_idr:
            return False, f"above_max_order (Rp{order_idr:,.0f} > Rp{self.cfg.max_order_idr:,.0f})"

        # position exposure
        if balance_idr > 0:
            exposure_pct = order_idr / balance_idr
            if exposure_pct > self.cfg.max_position_pct:
                return False, f"position_too_large ({exposure_pct:.0%} > {self.cfg.max_position_pct:.0%})"

        # cooldown
        last = self.state.last_trade_ts.get(pair, 0)
        elapsed = time.time() - last
        if elapsed < self.cfg.cooldown_seconds:
            remain = self.cfg.cooldown_seconds - elapsed
            return False, f"cooldown ({remain:.0f}s remaining)"

        return True, "ok"

    def record_trade(self, pair: str, pnl_idr: float = 0):
        self.reset_daily_if_needed()
        self.state.last_trade_ts[pair] = time.time()
        self.state.daily_trades += 1
        if pnl_idr < 0:
            self.state.daily_loss_idr += abs(pnl_idr)
        self._save_state()  # R-007: persist after trade
        log.info(f"[risk] trade recorded: {pair} pnl={pnl_idr:+,.0f} daily_trades={self.state.daily_trades} daily_loss=Rp{self.state.daily_loss_idr:,.0f}")

    def get_status(self) -> dict:
        self.reset_daily_if_needed()
        return {
            "daily_trades": self.state.daily_trades,
            "daily_trades_limit": self.cfg.max_daily_trades,
            "daily_loss_idr": self.state.daily_loss_idr,
            "daily_loss_limit": self.cfg.max_daily_loss_idr,
            "cooldowns": {
                pair: max(0, self.cfg.cooldown_seconds - (time.time() - ts))
                for pair, ts in self.state.last_trade_ts.items()
                if time.time() - ts < self.cfg.cooldown_seconds
            },
            "max_order_idr": self.cfg.max_order_idr,
            "max_position_pct": self.cfg.max_position_pct,
        }
