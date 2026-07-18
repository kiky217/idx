#!/usr/bin/env python3
"""
Trade Executor — eksekusi order via Indodax TAPI.
Support: dry-run mode, order tracking, rate limit.
"""
import os
import time
import hmac
import hashlib
import logging
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

import requests

log = logging.getLogger("idx.executor")
try:
    from telegram import notify_trade
except ImportError:
    notify_trade = None

INDODAX_BASE = "https://indodax.com"


class TradeExecutor:
    """
    Execute trades via Indodax TAPI.
    dry_run=True (default) = log only, no actual orders.
    """

    def __init__(self, api_key: str = None, api_secret: str = None,
                 dry_run: bool = True):
        self.api_key = api_key or os.environ.get("INDODAX_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("INDODAX_API_SECRET", "")
        self.dry_run = dry_run
        self.trade_log = []  # in-memory trade log
        self.last_request_ts = 0
        self.min_interval = 0.5  # 500ms between requests (safe: 20/s limit)

    def _sign(self, body: str) -> str:
        return hmac.new(
            self.api_secret.encode(), body.encode(), hashlib.sha512
        ).hexdigest()

    def _request(self, method_name: str, extra_params: dict = None) -> Optional[dict]:
        """Signed TAPI request."""
        if not self.api_key or not self.api_secret:
            log.error("[executor] no credentials set")
            return None

        # rate limit
        elapsed = time.time() - self.last_request_ts
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        params = {"method": method_name}
        if extra_params:
            params.update(extra_params)

        body = "&".join(f"{k}={v}" for k, v in params.items())
        sign = self._sign(body)
        headers = {
            "Key": self.api_key,
            "Sign": sign,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        self.last_request_ts = time.time()

        try:
            r = requests.post(f"{INDODAX_BASE}/tapi", headers=headers,
                              data=body, timeout=10)
            data = r.json()
            if data.get("success") == 1:
                return data.get("return", {})
            else:
                err = data.get("error", "unknown")
                log.error(f"[executor] {method_name} failed: {err}")
                return {"error": err}
        except Exception as e:
            log.error(f"[executor] {method_name} exception: {e}")
            return None

    def get_balance(self) -> Optional[dict]:
        """Get full balance from getInfo."""
        return self._request("getInfo")

    def get_owned_coins(self) -> list:
        """Get list of coins with balance > 0."""
        info = self.get_balance()
        if not info or "error" in info:
            return []
        balance = info.get("balance", {})
        return [k for k, v in balance.items() if float(v) > 0]

    def get_idr_balance(self) -> float:
        """Get IDR balance only."""
        info = self.get_balance()
        if not info or "error" in info:
            return 0.0
        return float(info.get("balance", {}).get("idr", 0))

    def place_limit_buy(self, pair: str, price: float, amount_idr: float,
                        client_order_id: str = None) -> Optional[dict]:
        """Place limit buy order."""
        params = {
            "type": "buy",
            "pair": pair,
            "price": str(int(price)),
            "idr": str(int(amount_idr)),
            "order_type": "limit",
        }
        if client_order_id:
            params["client_order_id"] = client_order_id

        return self._execute("trade", params, pair, "BUY", price, amount_idr)

    def place_limit_sell(self, pair: str, price: float, amount_coin: float,
                         client_order_id: str = None) -> Optional[dict]:
        """Place limit sell order."""
        coin = pair.split("_")[0]
        params = {
            "type": "sell",
            "pair": pair,
            "price": str(int(price)),
            coin: str(amount_coin),
            "order_type": "limit",
        }
        if client_order_id:
            params["client_order_id"] = client_order_id

        return self._execute("trade", params, pair, "SELL", price, 0)

    def place_market_buy(self, pair: str, amount_idr: float,
                         client_order_id: str = None) -> Optional[dict]:
        """Place market buy order."""
        params = {
            "type": "buy",
            "pair": pair,
            "idr": str(int(amount_idr)),
            "order_type": "market",
        }
        if client_order_id:
            params["client_order_id"] = client_order_id

        return self._execute("trade", params, pair, "MARKET_BUY", 0, amount_idr)

    def place_market_sell(self, pair: str, amount_coin: float,
                          client_order_id: str = None) -> Optional[dict]:
        """Place market sell order."""
        coin = pair.split("_")[0]
        params = {
            "type": "sell",
            "pair": pair,
            coin: str(amount_coin),
            "order_type": "market",
        }
        if client_order_id:
            params["client_order_id"] = client_order_id

        return self._execute("trade", params, pair, "MARKET_SELL", 0, 0)

    def _execute(self, method: str, params: dict, pair: str,
                 side: str, price: float, amount_idr: float) -> dict:
        """Internal: execute or dry-run log."""
        client_id = f"idx-{int(time.time())}-{pair}"
        params["client_order_id"] = client_id

        entry = {
            "ts": datetime.now().isoformat(),
            "pair": pair,
            "side": side,
            "price": price,
            "amount_idr": amount_idr,
            "client_order_id": client_id,
            "dry_run": self.dry_run,
            "params": params,
        }

        if self.dry_run:
            entry["result"] = "DRY_RUN"
            entry["success"] = True
            self.trade_log.append(entry)
            log.info(f"[executor] DRY_RUN {side} {pair} price={price} idr={amount_idr} cid={client_id}")
            return entry

        # live execution
        result = self._request(method, params)
        entry["result"] = result
        entry["success"] = result and "error" not in result
        self.trade_log.append(entry)

        if entry["success"]:
            log.info(f"[executor] LIVE {side} {pair} OK order_id={result.get('order_id')} cid={client_id}")
        else:
            log.warning(f"[executor] LIVE {side} {pair} FAILED: {result}")

        return entry

    def get_trade_log(self, limit: int = 20) -> list:
        return self.trade_log[-limit:]

    def get_status(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "has_credentials": bool(self.api_key and self.api_secret),
            "total_trades": len(self.trade_log),
            "last_trade": self.trade_log[-1] if self.trade_log else None,
        }
