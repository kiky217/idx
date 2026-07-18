#!/usr/bin/env python3
"""
Risk Manager — batas aman untuk scalping.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Dict

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


class RiskManager:
    def __init__(self, config: RiskConfig = None):
        self.cfg = config or RiskConfig()
        self.state = TradeState()

    def reset_daily_if_needed(self):
        now = time.time()
        if now - self.state.daily_reset_ts > 86400:
            self.state.daily_trades = 0
            self.state.daily_loss_idr = 0.0
            self.state.daily_reset_ts = now

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
