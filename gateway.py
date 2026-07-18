#!/usr/bin/env python3
"""
Market Gateway — WebSocket + REST collector untuk Indodax.
Blueprint Section B: Market Gateway + D: Candle Engine

Mengumpulkan data dari WebSocket Indodax, membentuk candle 1m/5m/15m,
dan menyediakan state untuk strategy engine.
"""
import os, time, json, threading, logging, asyncio
from datetime import datetime, timezone
from typing import Optional
from collections import deque

try:
    import websockets
except ImportError:
    websockets = None

log = logging.getLogger("idx.gateway")

# ── Constants ──
WS_MARKET_URL = "wss://ws3.indodax.com/ws/"
WS_PING_INTERVAL = 25
MAX_PAIRS = 10
CANDLE_PERIODS = {"1m": 60, "5m": 300, "15m": 900}

# ── Static token from Indodax docs (public) ──
# ── Static token from env (R-015) ──
WS_STATIC_TOKEN = os.environ.get(
    "INDODAX_WS_TOKEN",
    "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwdWJsaWN3cyIsInNjb3BlIjoicHVibGljIiwiaWF0IjoxNjk4NzE2ODAwfQ.JtDgT5aP-Z1qJzT5zS5zS5zS5zS5zS5zS5zS5zS5zS5zS5zS5zS5zA"
)


class Candle:
    """OHLC candle dengan incremental update."""
    __slots__ = ('pair', 'timeframe', 'open_time', 'open', 'high', 'low', 'close', 'volume', 'trade_count', 'is_final')
    
    def __init__(self, pair: str, timeframe: str, open_time: float, price: float, volume: float = 0):
        self.pair = pair
        self.timeframe = timeframe
        self.open_time = open_time
        self.open = price
        self.high = price
        self.low = price
        self.close = price
        self.volume = volume
        self.trade_count = 1
        self.is_final = False
    
    def update(self, price: float, volume: float = 0):
        if price > self.high: self.high = price
        if price < self.low: self.low = price
        self.close = price
        self.volume += volume
        self.trade_count += 1
    
    def finalize(self) -> dict:
        self.is_final = True
        return {
            "pair": self.pair,
            "timeframe": self.timeframe,
            "open_time": datetime.fromtimestamp(self.open_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "open": round(self.open, 2),
            "high": round(self.high, 2),
            "low": round(self.low, 2),
            "close": round(self.close, 2),
            "volume": round(self.volume, 8),
            "trade_count": self.trade_count,
        }


class CandleEngine:
    """Membentuk candle 1m/5m/15m dari trade flow."""
    
    def __init__(self):
        self._candles = {}  # (pair, tf) -> Candle
        self._lock = threading.Lock()
        self._callbacks = []  # listeners for finalized candles
    
    def on_finalized(self, callback):
        self._callbacks.append(callback)
    
    def _round_time(self, timestamp: float, period: int) -> float:
        return (timestamp // period) * period
    
    def feed_trade(self, pair: str, price: float, volume: float, timestamp: float):
        """Feed a single trade event."""
        with self._lock:
            for tf_name, period in CANDLE_PERIODS.items():
                key = (pair, tf_name)
                open_time = self._round_time(timestamp, period)
                
                if key not in self._candles:
                    self._candles[key] = Candle(pair, tf_name, open_time, price, volume)
                elif self._candles[key].open_time != open_time:
                    # Finalize old candle
                    old = self._candles[key].finalize()
                    for cb in self._callbacks:
                        cb(old)
                    # Start new candle
                    self._candles[key] = Candle(pair, tf_name, open_time, price, volume)
                else:
                    self._candles[key].update(price, volume)
    
    def get_candle(self, pair: str, timeframe: str = "1m") -> Optional[dict]:
        key = (pair, timeframe)
        with self._lock:
            c = self._candles.get(key)
            if c:
                return {"pair": c.pair, "timeframe": c.timeframe,
                        "open": c.open, "high": c.high, "low": c.low,
                        "close": c.close, "volume": c.volume,
                        "trade_count": c.trade_count, "is_final": c.is_final}
        return None


class LiveState:
    """In-memory state store (pengganti Redis untuk sekarang)."""
    
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()
    
    def set(self, key: str, value, ttl: int = 0):
        with self._lock:
            self._data[key] = {"val": value, "exp": time.time() + ttl if ttl else 0}
    
    def get(self, key: str):
        with self._lock:
            d = self._data.get(key)
            if not d: return None
            if d["exp"] and time.time() > d["exp"]:
                del self._data[key]
                return None
            return d["val"]
    
    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)
    
    def get_all(self, prefix: str = "") -> dict:
        with self._lock:
            return {k: v["val"] for k, v in self._data.items() if k.startswith(prefix)}


class MarketGateway:
    """Market Data Gateway — WebSocket + REST collector."""
    
    def __init__(self, candle_engine: CandleEngine):
        self.candle_engine = candle_engine
        self.state = LiveState()
        self.running = False
        self._thread = None
        self._watchlist = []
        self._lock = threading.Lock()
    
    def set_watchlist(self, pairs: list):
        with self._lock:
            self._watchlist = list(pairs)[:MAX_PAIRS]
    
    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="gateway")
        self._thread.start()
        log.info("[gateway] started")
    
    def stop(self):
        self.running = False
        log.info("[gateway] stopped")
    
    def _run_loop(self):
        """Run asyncio event loop in thread."""
        asyncio.run(self._ws_loop())
    
    async def _ws_loop(self):
        """WebSocket main loop with auto-reconnect."""
        while self.running:
            try:
                async with websockets.connect(WS_MARKET_URL, ping_interval=WS_PING_INTERVAL) as ws:
                    log.info("[gateway] WebSocket connected")
                    
                    # Auth
                    auth_msg = json.dumps({"params": {"token": WS_STATIC_TOKEN}, "id": 1})
                    await ws.send(auth_msg)
                    resp = await ws.recv()
                    auth_data = json.loads(resp)
                    log.info(f"[gateway] auth OK: {auth_data.get('result', {}).get('client', '?')[:20]}...")
                    
                    # Subscribe to watchlist pairs
                    while self.running:
                        with self._lock:
                            pairs = list(self._watchlist)
                        
                        for pair in pairs:
                            # Subscribe to trade activity
                            sub = json.dumps({"method": 1, "params": {"channel": f"trade:{pair}.activity"}, "id": hash(pair) & 0xFFFF})
                            await ws.send(sub)
                        
                        # Read messages
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            self._process_message(msg)
                        except asyncio.TimeoutError:
                            continue
                            
            except Exception as e:
                log.warning(f"[gateway] WS error: {e}, reconnecting in 5s...")
                if self.running:
                    await asyncio.sleep(5)
    
    def _process_message(self, raw: str):
        """Process incoming WebSocket message."""
        try:
            data = json.loads(raw)
            if data.get("method") == 1:  # subscription data
                channel = data.get("params", {}).get("channel", "")
                result = data.get("result", {})
                
                if "trade" in channel and ".activity" in channel:
                    pair = channel.split(":")[1].split(".")[0] if ":" in channel else ""
                    trades = result if isinstance(result, list) else [result]
                    for t in trades:
                        price = float(t.get("price", 0))
                        vol = float(t.get("amount", 0))
                        ts = float(t.get("timestamp", time.time()))
                        if price > 0:
                            self.candle_engine.feed_trade(pair, price, vol, ts)
        except json.JSONDecodeError:
            pass


# ── Global instances ──
candle_engine = CandleEngine()
market_gateway = MarketGateway(candle_engine)
live_state = market_gateway.state
