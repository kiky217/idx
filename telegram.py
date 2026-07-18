#!/usr/bin/env python3
"""
Telegram Bot — notifikasi trading untuk INDODAX SCALPING MODE.
Menggunakan bot token dari env, kirim ke group LOGS.
"""
import os
import time
import logging
import requests
from typing import Optional

log = logging.getLogger("idx.telegram")


class TelegramBot:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "-1004349553559")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.enabled = bool(self.token)

    def send(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.enabled:
            log.debug("[telegram] disabled (no token)")
            return False
        try:
            r = requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
                timeout=10,
            )
            if r.ok:
                return True
            log.error(f"[telegram] send failed: {r.status_code} {r.text[:200]}")
        except Exception as e:
            log.error(f"[telegram] exception: {e}")
        return False

    def send_trade(self, pair: str, side: str, price: float,
                   amount_idr: float, pnl_idr: float = 0,
                   dry_run: bool = True, order_id: str = None) -> bool:
        """Format trade notification."""
        tag = "🧪 <b>DRY_RUN</b>" if dry_run else "💰 <b>LIVE</b>"
        side_emoji = "🟢" if "BUY" in side.upper() else "🔴"
        pnl_text = f"\nP&L: <b>{pnl_idr:+,.0f} IDR</b>" if pnl_idr != 0 else ""
        oid = f"\nOrder: <code>{order_id}</code>" if order_id else ""
        text = (
            f"{tag} {side_emoji} <b>{side.upper()}</b> {pair.replace('_','/').upper()}\n"
            f"Harga: <b>{price:,.0f} IDR</b>\n"
            f"Nominal: <b>{amount_idr:,.0f} IDR</b>{pnl_text}{oid}"
        )
        return self.send(text)

    def send_scalper_status(self, running: bool, mode: str) -> bool:
        status = "▶️ <b>STARTED</b>" if running else "⏹️ <b>STOPPED</b>"
        text = f"🤖 Scalper {status}\nMode: <b>{mode}</b>"
        return self.send(text)

    def send_error(self, context: str, error: str) -> bool:
        text = f"⚠️ <b>ERROR</b> [{context}]\n<code>{error}</code>"
        return self.send(text)

    def send_daily_summary(self, summary: dict) -> bool:
        """Kirim ringkasan P&L harian."""
        today = summary.get("today", {})
        text = (
            f"📊 <b>DAILY P&L</b> {today.get('date','')}\n"
            f"Trades: <b>{today.get('trades_count',0)}</b>\n"
            f"P&L: <b>{today.get('total_pnl',0):+,.0f} IDR</b>\n"
            f"Win: <b>{today.get('wins',0)}</b> | Loss: <b>{today.get('losses',0)}</b>\n"
            f"Volume: <b>{today.get('total_volume_idr',0):,.0f} IDR</b>"
        )
        return self.send(text)

    def test(self) -> bool:
        return self.send("✅ <b>Telegram Bot Test</b> — INDODAX SCALPING MODE connected")


# Singleton instance
_bot: Optional[TelegramBot] = None


def get_bot() -> TelegramBot:
    global _bot
    if _bot is None:
        _bot = TelegramBot()
    return _bot


def notify_trade(pair: str, side: str, price: float,
                 amount_idr: float, pnl_idr: float = 0,
                 dry_run: bool = True, order_id: str = None):
    """Helper cepat untuk notif trade."""
    get_bot().send_trade(pair, side, price, amount_idr, pnl_idr, dry_run, order_id)


def notify_scalper(running: bool, mode: str):
    get_bot().send_scalper_status(running, mode)


def notify_error(context: str, error: str):
    get_bot().send_error(context, error)


def notify_daily(summary: dict):
    get_bot().send_daily_summary(summary)


def test_bot() -> bool:
    return get_bot().test()