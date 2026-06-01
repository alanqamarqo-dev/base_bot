"""
Database Module - SQLite Storage
================================
Stores token scan history, analysis results, and enables
tracking of tokens over time.
"""
import json
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens (
    address TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    chain TEXT DEFAULT 'base',
    description TEXT DEFAULT '',
    website TEXT DEFAULT '',
    twitter TEXT DEFAULT '',
    telegram TEXT DEFAULT '',
    discord TEXT DEFAULT '',
    github_url TEXT DEFAULT '',
    market_cap REAL DEFAULT 0.0,
    price_usd REAL DEFAULT 0.0,
    liquidity_usd REAL DEFAULT 0.0,
    volume_24h REAL DEFAULT 0.0,
    price_change_24h REAL DEFAULT 0.0,
    pair_address TEXT DEFAULT '',
    dex_url TEXT DEFAULT '',
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_positive INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    result_json TEXT NOT NULL,
    is_safe INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (token_address) REFERENCES tokens(address)
);

CREATE TABLE IF NOT EXISTS daily_scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date TEXT NOT NULL,
    tokens_found INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_tokens (
    scan_id INTEGER NOT NULL,
    token_address TEXT NOT NULL,
    is_positive INTEGER DEFAULT 0,
    overall_score INTEGER DEFAULT 0,
    PRIMARY KEY (scan_id, token_address),
    FOREIGN KEY (scan_id) REFERENCES daily_scans(id),
    FOREIGN KEY (token_address) REFERENCES tokens(address)
);

CREATE INDEX IF NOT EXISTS idx_analyses_token ON analyses(token_address);
CREATE INDEX IF NOT EXISTS idx_analyses_type ON analyses(analysis_type);
CREATE INDEX IF NOT EXISTS idx_tokens_name ON tokens(name);
CREATE INDEX IF NOT EXISTS idx_tokens_first_seen ON tokens(first_seen);
CREATE INDEX IF NOT EXISTS idx_daily_scans_date ON daily_scans(scan_date);
"""


class Database:
    """SQLite database for token tracking and analysis history."""

    def __init__(self, db_path: str = "base_bot.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_conn() as conn:
            conn.executescript(DB_SCHEMA)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ── Token Operations ──────────────────────────────────────────

    def upsert_token(self, token_data: Dict[str, Any]) -> bool:
        """Insert or update a token record."""
        with self._get_conn() as conn:
            try:
                conn.execute("""
                    INSERT INTO tokens (address, name, symbol, chain, description,
                        website, twitter, telegram, discord, github_url,
                        market_cap, price_usd, liquidity_usd, volume_24h,
                        price_change_24h, pair_address, dex_url,
                        first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(address) DO UPDATE SET
                        name=excluded.name, symbol=excluded.symbol,
                        market_cap=excluded.market_cap, price_usd=excluded.price_usd,
                        liquidity_usd=excluded.liquidity_usd, volume_24h=excluded.volume_24h,
                        price_change_24h=excluded.price_change_24h,
                        pair_address=excluded.pair_address,
                        dex_url=excluded.dex_url,
                        last_seen=CURRENT_TIMESTAMP
                """, (
                    token_data.get("address"),
                    token_data.get("name", "Unknown"),
                    token_data.get("symbol", "UNKNOWN"),
                    token_data.get("chain", "base"),
                    token_data.get("description", ""),
                    token_data.get("website", ""),
                    token_data.get("twitter", ""),
                    token_data.get("telegram", ""),
                    token_data.get("discord", ""),
                    token_data.get("github", ""),
                    float(token_data.get("market_cap", 0) or 0),
                    float(token_data.get("price_usd", 0) or 0),
                    float(token_data.get("liquidity_usd", 0) or 0),
                    float(token_data.get("volume_24h", 0) or 0),
                    float(token_data.get("price_change_24h", 0) or 0),
                    token_data.get("pair_address", ""),
                    token_data.get("dex_url", ""),
                    token_data.get("created_at", datetime.now().isoformat()),
                    datetime.now().isoformat(),
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error upserting token: {e}")
                return False

    def get_token(self, address: str) -> Optional[Dict]:
        """Get a token by address."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM tokens WHERE address = ?", (address,)
            ).fetchone()
            return dict(row) if row else None

    def get_tokens_by_date(self, date_str: str) -> List[Dict]:
        """Get tokens first seen on a specific date."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tokens WHERE DATE(first_seen) = ? ORDER BY first_seen DESC",
                (date_str,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_tokens(self, days: int = 1) -> List[Dict]:
        """Get tokens discovered in the last N days."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tokens WHERE first_seen >= DATE('now', ?) ORDER BY first_seen DESC",
                (f"-{days} days",)
            ).fetchall()
            return [dict(r) for r in rows]

    def was_token_seen_today(self, address: str) -> bool:
        """Check if a token was already reported today."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM tokens WHERE address = ? AND DATE(last_seen) = DATE('now')",
                (address,)
            ).fetchone()
            return row is not None

    # ── Analysis Operations ───────────────────────────────────────

    def save_analysis(self, token_address: str, analysis_type: str,
                      result_data: Dict, is_safe: bool = False, score: int = 0) -> bool:
        """Save an analysis result."""
        with self._get_conn() as conn:
            try:
                conn.execute("""
                    INSERT INTO analyses (token_address, analysis_type, result_json, is_safe, score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    token_address,
                    analysis_type,
                    json.dumps(result_data, default=str),
                    1 if is_safe else 0,
                    score,
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving analysis: {e}")
                return False

    def get_latest_analyses(self, token_address: str) -> Dict[str, Dict]:
        """Get the most recent analysis of each type for a token."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM analyses
                WHERE token_address = ?
                AND (analysis_type, created_at) IN (
                    SELECT analysis_type, MAX(created_at)
                    FROM analyses
                    WHERE token_address = ?
                    GROUP BY analysis_type
                )
            """, (token_address, token_address)).fetchall()

            result = {}
            for row in rows:
                r = dict(row)
                r["result_json"] = json.loads(r["result_json"])
                result[r["analysis_type"]] = r
            return result

    # ── Daily Scan Operations ─────────────────────────────────────

    def create_daily_scan(self, date_str: Optional[str] = None) -> int:
        """Create a new daily scan record, returns scan_id."""
        date_str = date_str or datetime.now().strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO daily_scans (scan_date, tokens_found, positive_count, negative_count, status) "
                "VALUES (?, 0, 0, 0, 'running')",
                (date_str,)
            )
            conn.commit()
            return cursor.lastrowid

    def add_scan_token(self, scan_id: int, token_address: str,
                       is_positive: bool = False, overall_score: int = 0):
        """Add a token to a daily scan."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scan_tokens (scan_id, token_address, is_positive, overall_score)
                VALUES (?, ?, ?, ?)
            """, (scan_id, token_address, 1 if is_positive else 0, overall_score))
            conn.commit()

    def complete_daily_scan(self, scan_id: int, positive: int, negative: int, total: int):
        """Mark a daily scan as completed."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE daily_scans
                SET tokens_found = ?, positive_count = ?, negative_count = ?, status = 'completed'
                WHERE id = ?
            """, (total, positive, negative, scan_id))
            conn.commit()

    def get_daily_scan_summary(self, date_str: Optional[str] = None) -> Optional[Dict]:
        """Get summary of a daily scan."""
        date_str = date_str or datetime.now().strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM daily_scans WHERE scan_date = ? ORDER BY id DESC LIMIT 1",
                (date_str,)
            ).fetchone()
            return dict(row) if row else None

    def get_scan_tokens(self, scan_id: int, positive_only: bool = False) -> List[Dict]:
        """Get tokens in a scan."""
        with self._get_conn() as conn:
            query = """SELECT t.*, st.is_positive AS scan_is_positive, st.overall_score
                       FROM scan_tokens st
                       JOIN tokens t ON st.token_address = t.address
                       WHERE st.scan_id = ?"""
            if positive_only:
                query += " AND st.is_positive = 1"
            rows = conn.execute(query, (scan_id,)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                # Rename the scan's is_positive column to not conflict with tokens.is_positive
                d["is_positive"] = d.pop("scan_is_positive", 0)
                results.append(d)
            return results

    # ── Utilities ─────────────────────────────────────────────────

    def get_statistics(self) -> Dict:
        """Get overall statistics."""
        with self._get_conn() as conn:
            total_tokens = conn.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
            total_analyses = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
            total_scans = conn.execute("SELECT COUNT(*) FROM daily_scans").fetchone()[0]

            pos = conn.execute(
                "SELECT COALESCE(SUM(positive_count), 0) FROM daily_scans"
            ).fetchone()[0]
            neg = conn.execute(
                "SELECT COALESCE(SUM(negative_count), 0) FROM daily_scans"
            ).fetchone()[0]

            return {
                "total_tokens": total_tokens,
                "total_analyses": total_analyses,
                "total_scans": total_scans,
                "total_positive": pos,
                "total_negative": neg,
            }

    def close(self):
        """No-op for SQLite; connections are managed per-operation."""
        pass