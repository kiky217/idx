#!/usr/bin/env python3
"""
Signal Engine — deteksi sinyal scalping dari data Indodax.
Strategi: EMA crossover (9/21) + RSI filter + volume spike.
"""
import time
import logging
from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal

log = logging.getLogger("idx.signal")


@dataclass
class Signal:
    pair: str
    action: str          # BUY / SELL / HOLD
    confidence: float    # 0.0 - 1.0
    price: float
    reasons: list        # list of strings
    timestamp: float
    indicators: dict     # ema9, ema21, rsi, vol_ratio


def ema(data: list, period: int) -> list:
    """Exponential Moving Average."""
    if len(data) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(data[:period]) / period]
    for price in data[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def rsi(closes: list, period: int = 14) -> float:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


class SignalEngine:
    """
    Generate trading signals from ticker history.
    Needs at least 30 data points per pair for reliable signals.
    """

    def __init__(self):
        # pair -> list of {"ts", "last", "high", "low", "vol", "buy", "sell"}
        self.history: dict = {}
        self.max_history = 100

    def feed(self, pair: str, ticker: dict):
        """Feed latest ticker data into history."""
        if pair not in self.history:
            self.history[pair] = []

        try:
            entry = {
                "ts": time.time(),
                "last": float(ticker.get("last", 0)),
                "high": float(ticker.get("high", 0)),
                "low": float(ticker.get("low", 0)),
                "vol": float(ticker.get(f"vol_{pair.split('_')[0]}", 0) or 0),
                "buy": float(ticker.get("buy", 0)),
                "sell": float(ticker.get("sell", 0)),
            }
        except (ValueError, TypeError):
            return

        if entry["last"] <= 0:
            return

        self.history[pair].append(entry)
        if len(self.history[pair]) > self.max_history:
            self.history[pair] = self.history[pair][-self.max_history:]

    def analyze(self, pair: str) -> Signal:
        """Analyze pair and return Signal."""
        closes = [e["last"] for e in self.history.get(pair, [])]
        vols = [e["vol"] for e in self.history.get(pair, [])]

        default = Signal(
            pair=pair, action="HOLD", confidence=0.0,
            price=closes[-1] if closes else 0,
            reasons=["insufficient data"],
            timestamp=time.time(),
            indicators={"ema9": 0, "ema21": 0, "rsi": 50, "vol_ratio": 1.0},
        )

        if len(closes) < 25:
            return default

        price = closes[-1]
        ema9_vals = ema(closes, 9)
        ema21_vals = ema(closes, 21)

        if not ema9_vals or not ema21_vals:
            return default

        ema9 = ema9_vals[-1]
        ema21 = ema21_vals[-1]
        ema9_prev = ema9_vals[-2] if len(ema9_vals) >= 2 else ema9
        ema21_prev = ema21_vals[-2] if len(ema21_vals) >= 2 else ema21
        rsi_val = rsi(closes)

        # volume ratio (current vs avg 20)
        vol_now = vols[-1] if vols else 0
        vol_avg = sum(vols[-20:]) / max(len(vols[-20:]), 1)
        vol_ratio = vol_now / max(vol_avg, 0.0001)

        reasons = []
        score = 0.0

        # --- EMA crossover ---
        cross_up = ema9_prev <= ema21_prev and ema9 > ema21
        cross_down = ema9_prev >= ema21_prev and ema9 < ema21
        above = ema9 > ema21

        if cross_up:
            reasons.append("EMA9 crossed above EMA21")
            score += 0.4
        elif cross_down:
            reasons.append("EMA9 crossed below EMA21")
            score -= 0.4
        elif above:
            reasons.append("EMA9 above EMA21 (trend up)")
            score += 0.15
        else:
            reasons.append("EMA9 below EMA21 (trend down)")
            score -= 0.15

        # --- RSI ---
        if rsi_val < 30:
            reasons.append(f"RSI oversold ({rsi_val:.1f})")
            score += 0.3
        elif rsi_val < 40:
            reasons.append(f"RSI low ({rsi_val:.1f})")
            score += 0.15
        elif rsi_val > 70:
            reasons.append(f"RSI overbought ({rsi_val:.1f})")
            score -= 0.3
        elif rsi_val > 60:
            reasons.append(f"RSI high ({rsi_val:.1f})")
            score -= 0.15

        # --- Volume ---
        if vol_ratio > 2.0:
            reasons.append(f"Volume spike ({vol_ratio:.1f}x avg)")
            score += 0.2 if score > 0 else 0.1  # boost buy, smaller boost sell
        elif vol_ratio > 1.5:
            reasons.append(f"Volume above avg ({vol_ratio:.1f}x)")

        # --- Spread ---
        buy = float(closes[-1] * 0.999)  # estimate from last if no buy
        sell = float(closes[-1] * 1.001)
        spread_pct = (sell - buy) / max(buy, 1) * 100
        if spread_pct > 1.0:
            reasons.append(f"Wide spread ({spread_pct:.2f}%)")
            score *= 0.7  # penalize

        # --- Decision ---
        confidence = min(abs(score), 1.0)

        if score >= 0.5:
            action = "BUY"
        elif score <= -0.5:
            action = "SELL"
        else:
            action = "HOLD"
            confidence *= 0.5  # lower confidence for HOLD

        return Signal(
            pair=pair, action=action, confidence=confidence,
            price=price, reasons=reasons, timestamp=time.time(),
            indicators={"ema9": round(ema9, 2), "ema21": round(ema21, 2),
                        "rsi": round(rsi_val, 2), "vol_ratio": round(vol_ratio, 2)},
        )

    def get_history_count(self, pair: str) -> int:
        return len(self.history.get(pair, []))
