#!/usr/bin/env python3
"""
Signal Engine v2 — Blueprint Precision Scalper.
Multi-timeframe: 15m trend (EMA20/50), 5m momentum, 1m trigger.
"""
import time
import logging
from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal
from collections import deque

log = logging.getLogger("idx.signal")

@dataclass
class Signal:
    pair: str
    action: str          # BUY / SELL / HOLD / WAIT_AND_SEE
    confidence: float    # 0.0 - 1.0
    score: float         # internal score -1..1
    regime: str          # trend / range / volatile
    price: float
    reasons: list
    timestamp: float
    indicators: dict

# ── helpers ──
def ema(data: list, period: int) -> list:
    if len(data) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(data[:period]) / period]
    for price in data[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result

def rsi(closes: list, period: int = 14) -> float:
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

def atr(highs: list, lows: list, closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 0
    tr = []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr.append(max(hl, hc, lc))
    return sum(tr[-period:]) / period if tr else 0


class SignalEngine:
    """
    Multi-indicator ensemble signal engine.
    - 15m: EMA20/50 trend, Bollinger position
    - 5m:  RSI, momentum
    - 1m:  Volume spike, microstructure
    """
    
    def __init__(self):
        self.history: dict = {}  # pair -> list of ticks
        self.max_history = 100
    
    def feed(self, pair: str, ticker: dict):
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
        ticks = self.history.get(pair, [])
        closes = [e["last"] for e in ticks]
        highs = [e["high"] for e in ticks]
        lows = [e["low"] for e in ticks]
        vols = [e["vol"] for e in ticks]
        
        default = Signal(pair=pair, action="HOLD", confidence=0.0, score=0,
                         regime="unknown", price=closes[-1] if closes else 0,
                         reasons=["insufficient data"], timestamp=time.time(),
                         indicators={})
        
        if len(closes) < 50:
            return default
        
        price = closes[-1]
        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        if not ema20 or not ema50:
            return default
        
        ema20_val = ema20[-1]
        ema50_val = ema50[-1]
        ema20_prev = ema20[-2] if len(ema20) >= 2 else ema20_val
        ema50_prev = ema50[-2] if len(ema50) >= 2 else ema50_val
        rsi_val = rsi(closes)
        atr_val = atr(highs, lows, closes)
        
        # Volume ratio
        vol_now = vols[-1] if vols else 0
        vol_avg = sum(vols[-20:]) / max(len(vols[-20:]), 1)
        vol_ratio = vol_now / max(vol_avg, 0.0001)
        
        # ── R-005: Spread from actual best bid/ask if available ──
        if "buy" in ticks[-1] and "sell" in ticks[-1] and ticks[-1]["buy"] > 0 and ticks[-1]["sell"] > 0:
            spread_pct = (ticks[-1]["sell"] - ticks[-1]["buy"]) / max(ticks[-1]["buy"], 1) * 100
        else:
            spread_pct = 0.1  # default tight spread
        # Use bid/ask for microstructure if available
        bid = ticks[-1].get("buy", price * 0.999)
        ask = ticks[-1].get("sell", price * 1.001)
        
        reasons = []
        score = 0.0
        
        # ── R-004: Trend 15m (EMA20/50) ──
        trend_pct = (ema20_val / max(ema50_val, 0.0001) - 1) * 100
        cross_up = ema20_prev <= ema50_prev and ema20_val > ema50_val
        cross_down = ema20_prev >= ema50_prev and ema20_val < ema50_val
        
        if cross_up:
            reasons.append("EMA20 crossed above EMA50 (bullish)")
            score += 0.4
        elif cross_down:
            reasons.append("EMA20 crossed below EMA50 (bearish)")
            score -= 0.4
        elif ema20_val > ema50_val:
            reasons.append(f"EMA20 above EMA50 (uptrend +{trend_pct:.2f}%)")
            score += 0.2
        else:
            reasons.append(f"EMA20 below EMA50 (downtrend {trend_pct:.2f}%)")
            score -= 0.2
        
        # Regime detection
        volatility = atr_val / max(price, 1) * 100
        regime = "volatile" if volatility > 1.5 else ("trend" if abs(trend_pct) > 0.15 else "range")
        
        # ── RSI ──
        if rsi_val < 30:
            reasons.append(f"RSI oversold ({rsi_val:.1f})")
            score += 0.25
        elif rsi_val < 40:
            reasons.append(f"RSI low ({rsi_val:.1f})")
            score += 0.1
        elif rsi_val > 70:
            reasons.append(f"RSI overbought ({rsi_val:.1f})")
            score -= 0.25
        elif rsi_val > 60:
            reasons.append(f"RSI high ({rsi_val:.1f})")
            score -= 0.1
        
        # ── Volume ──
        if vol_ratio > 2.0:
            reasons.append(f"Volume spike ({vol_ratio:.1f}x)")
            if score > 0:
                score += 0.15
        elif vol_ratio > 1.5:
            reasons.append(f"Volume above avg ({vol_ratio:.1f}x)")
        
        # ── Spread gate ──
        if spread_pct > 1.0:
            reasons.append(f"Wide spread ({spread_pct:.2f}%)")
            score *= 0.7
        
        # ── Decision ──
        confidence = min(abs(score), 1.0)
        
        if score >= 0.5:
            action = "BUY"
        elif score <= -0.5:
            action = "SELL"
        elif abs(score) >= 0.25:
            action = "WAIT_AND_SEE"
        else:
            action = "HOLD"
            confidence *= 0.3
        
        # Adjust for regime
        if regime == "volatile" and action != "HOLD":
            reasons.append("Volatile market — reducing confidence")
            confidence *= 0.8
        
        return Signal(
            pair=pair, action=action, confidence=confidence, score=score,
            regime=regime, price=price, reasons=reasons,
            timestamp=time.time(),
            indicators={
                "ema20": round(ema20_val, 2), "ema50": round(ema50_val, 2),
                "rsi": round(rsi_val, 2), "atr": round(atr_val, 2),
                "vol_ratio": round(vol_ratio, 2), "trend_pct": round(trend_pct, 4),
            }
        )
    
    def get_history_count(self, pair: str) -> int:
        return len(self.history.get(pair, []))
