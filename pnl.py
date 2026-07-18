#!/usr/bin/env python3
"""
P&L Persistence — SQLite storage untuk trade log dan P&L tracking.
"""
import os
import time
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

log = logging.getLogger("idx.pnl")

DB_PATH = os.environ.get("PNL_DB", "/app/data/trades.db")


class PnLStorage:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL DEFAULT 0,
                    amount_idr REAL NOT NULL DEFAULT 0,
                    amount_coin REAL NOT NULL DEFAULT 0,
                    fee REAL NOT NULL DEFAULT 0,
                    pnl_idr REAL DEFAULT 0,
                    order_id TEXT,
                    client_order_id TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    dry_run INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_pnl (
                    date TEXT PRIMARY KEY,
                    total_pnl REAL NOT NULL DEFAULT 0,
                    trades_count INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    total_volume_idr REAL NOT NULL DEFAULT 0
                )
            """)
            log.info(f"[pnl] DB initialized: {self.db_path}")

    def record_trade(self, pair: str, side: str, price: float,
                     amount_idr: float = 0, amount_coin: float = 0,
                     fee: float = 0, pnl_idr: float = 0,
                     order_id: str = None, client_order_id: str = None,
                     status: str = "filled", dry_run: bool = True) -> int:
        """Insert trade record, return trade id."""
        ts = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute("""
                INSERT INTO trades (ts, pair, side, price, amount_idr, amount_coin,
                                    fee, pnl_idr, order_id, client_order_id, status, dry_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ts, pair, side, price, amount_idr, amount_coin, fee, pnl_idr,
                  order_id, client_order_id, status, 1 if dry_run else 0))
            trade_id = cur.lastrowid

        # update daily summary
        self._update_daily(pair, side, pnl_idr, amount_idr)
        log.info(f"[pnl] trade #{trade_id} {side} {pair} pnl={pnl_idr:+,.0f} dry={dry_run}")
        return trade_id

    def _update_daily(self, pair, side, pnl_idr, amount_idr):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM daily_pnl WHERE date=?", (today,)).fetchone()
            if row:
                wins = row["wins"] + (1 if pnl_idr > 0 else 0)
                losses = row["losses"] + (1 if pnl_idr < 0 else 0)
                conn.execute("""
                    UPDATE daily_pnl SET total_pnl=total_pnl+?, trades_count=trades_count+1,
                           wins=?, losses=?, total_volume_idr=total_volume_idr+?
                    WHERE date=?
                """, (pnl_idr, wins, losses, amount_idr, today))
            else:
                wins = 1 if pnl_idr > 0 else 0
                losses = 1 if pnl_idr < 0 else 0
                conn.execute("""
                    INSERT INTO daily_pnl (date, total_pnl, trades_count, wins, losses, total_volume_idr)
                    VALUES (?, ?, 1, ?, ?, ?)
                """, (today, pnl_idr, wins, losses, amount_idr))

    def get_trades(self, limit: int = 50, pair: str = None) -> list:
        with self._conn() as conn:
            if pair:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE pair=? ORDER BY id DESC LIMIT ?",
                    (pair, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_daily_pnl(self, days: int = 30) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM daily_pnl ORDER BY date DESC LIMIT ?", (days,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_summary(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) as n FROM trades").fetchone()["n"]
            pnl = conn.execute("SELECT COALESCE(SUM(pnl_idr),0) as total FROM trades").fetchone()["total"]
            wins = conn.execute("SELECT COUNT(*) as n FROM trades WHERE pnl_idr > 0").fetchone()["n"]
            losses = conn.execute("SELECT COUNT(*) as n FROM trades WHERE pnl_idr < 0").fetchone()["n"]
            volume = conn.execute("SELECT COALESCE(SUM(amount_idr),0) as v FROM trades").fetchone()["v"]

            today = datetime.utcnow().strftime("%Y-%m-%d")
            daily = conn.execute("SELECT * FROM daily_pnl WHERE date=?", (today,)).fetchone()

            return {
                "total_trades": total,
                "total_pnl_idr": pnl,
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / max(total, 1) * 100, 1),
                "total_volume_idr": volume,
                "today": dict(daily) if daily else {"date": today, "trades_count": 0, "total_pnl": 0, "wins": 0, "losses": 0},
            }
