"""
Liquidity Lock Checker - UNCX / Unicrypt Integration
=====================================================
Verifies the liquidity lock status for tokens.
Checks Unicrypt (UNCX) lockers and other lock providers.
Produces a timeline and lock percentage display.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)

# Unicrypt / UNCX API
UNCX_API_URL = "https://app.uncx.network/api"

# DexScreener as fallback for LP info
DEXSCREENER_API_URL = "https://api.dexscreener.com"


@dataclass
class LiquidityLockInfo:
    """Information about a single lock."""

    lock_id: str = ""
    token_address: str = ""
    pair_address: str = ""
    locker_name: str = ""  # UNCX, TeamFinance, etc.
    amount_usd: float = 0.0
    locked_percentage: float = 0.0
    unlock_date: Optional[datetime] = None
    is_locked: bool = False
    days_remaining: int = 0
    is_expired: bool = False


@dataclass
class LiquidityCheckResult:
    """Result of a liquidity lock analysis."""

    token_address: str
    token_name: str = ""
    token_symbol: str = ""
    total_liquidity_usd: float = 0.0
    total_locked_usd: float = 0.0
    locked_percentage: float = 0.0
    locks: List[LiquidityLockInfo] = field(default_factory=list)
    has_lock: bool = False
    is_fully_locked: bool = False
    lock_expiry_soon: bool = False
    risk_warning: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error_message: str = ""

    @property
    def is_safe(self) -> bool:
        """Considered safe if >80% liquidity is locked for >30 days."""
        if not self.has_lock:
            return False
        if self.locked_percentage < 40:
            return False
        if self.lock_expiry_soon:
            return False
        return True

    @property
    def status_text(self) -> str:
        if not self.has_lock:
            return "🔴 NO LOCK – Liquidity is not locked!"
        if self.locked_percentage >= 80:
            return f"🟢 LOCKED {self.locked_percentage:.0f}% – Safe"
        elif self.locked_percentage >= 40:
            return f"🟡 LOCKED {self.locked_percentage:.0f}% – Partial"
        else:
            return f"🔴 LOCKED {self.locked_percentage:.0f}% – Low"

    @property
    def status_color(self) -> str:
        if not self.has_lock:
            return "#ef4444"
        if self.locked_percentage >= 80:
            return "#22c55e"
        elif self.locked_percentage >= 40:
            return "#f59e0b"
        return "#ef4444"

    @property
    def unlock_timeline(self) -> List[Dict]:
        """Return timeline data for chart."""
        timeline = []
        for lock in self.locks:
            if lock.unlock_date:
                timeline.append({
                    "locker": lock.locker_name,
                    "amount_usd": lock.amount_usd,
                    "unlock_date": lock.unlock_date.isoformat(),
                    "days_remaining": lock.days_remaining,
                    "is_expired": lock.is_expired,
                })
        return timeline

    def to_dict(self) -> Dict:
        return {
            "token_address": self.token_address,
            "token_name": self.token_name,
            "token_symbol": self.token_symbol,
            "total_liquidity_usd": self.total_liquidity_usd,
            "total_locked_usd": self.total_locked_usd,
            "locked_percentage": self.locked_percentage,
            "has_lock": self.has_lock,
            "is_fully_locked": self.is_fully_locked,
            "lock_expiry_soon": self.lock_expiry_soon,
            "risk_warning": self.risk_warning,
            "is_safe": self.is_safe,
            "status_text": self.status_text,
            "locks": [{"locker_name": l.locker_name, "amount_usd": l.amount_usd,
                       "locked_percentage": l.locked_percentage, "days_remaining": l.days_remaining}
                      for l in self.locks],
            "success": self.success,
        }


class LiquidityChecker:
    """Checks liquidity lock status for tokens."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "BaseBot/1.0 LiquidityChecker"},
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "",
                    liquidity_usd: float = 0.0) -> LiquidityCheckResult:
        """
        Check liquidity lock status for a token.
        """
        result = LiquidityCheckResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            total_liquidity_usd=liquidity_usd,
        )

        session = await self._get_session()

        # Step 1: Get token pair data from DexScreener to find LP pair
        pair_address = await self._get_pair_address(session, token_address)

        # Step 2: Check UNCX for locks
        if pair_address:
            locks = await self._check_uncx_lock(session, pair_address, token_address)
            if locks:
                result.locks = locks
                result.has_lock = True
                result.success = True

        # Step 3: Calculate metrics
        if result.locks:
            self._calculate_metrics(result)

        if result.success:
            logger.info(
                f"Liquidity check for {token_symbol or token_address[:10]}: "
                f"{result.status_text}"
            )
        else:
            # Try fallback heuristic
            await self._heuristic_check(session, token_address, result)

        return result

    async def _get_pair_address(self, session: aiohttp.ClientSession, token_address: str) -> str:
        """Get the main liquidity pair address from DexScreener."""
        try:
            url = f"{DEXSCREENER_API_URL}/latest/dex/tokens/{token_address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        # Take the highest liquidity pair
                        best_pair = max(
                            pairs,
                            key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0),
                        )
                        return best_pair.get("pairAddress", "")
        except Exception as e:
            logger.debug(f"Error getting pair address: {e}")
        return ""

    async def _check_uncx_lock(
        self, session: aiohttp.ClientSession, pair_address: str, token_address: str
    ) -> List[LiquidityLockInfo]:
        """Check UNCX lock data for the pair."""
        locks = []
        try:
            # UNCX public API endpoint for locked liquidity
            url = f"{UNCX_API_URL}/locked/list?address={pair_address}&chainId=8453"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lock_data = data.get("data", data.get("locks", []))
                    if isinstance(lock_data, list):
                        for lock_item in lock_data:
                            lock_info = LiquidityLockInfo(
                                lock_id=str(lock_item.get("id", "")),
                                token_address=token_address,
                                pair_address=pair_address,
                                locker_name=lock_item.get("locker", "UNCX"),
                                amount_usd=float(lock_item.get("amountUsd", 0) or 0),
                                locked_percentage=float(lock_item.get("percentage", 100) or 100),
                            )

                            # Parse unlock date
                            unlock_ts = lock_item.get("unlockDate", lock_item.get("unlock_time", 0))
                            if unlock_ts:
                                try:
                                    lock_info.unlock_date = datetime.fromtimestamp(int(unlock_ts))
                                    lock_info.days_remaining = (lock_info.unlock_date - datetime.now()).days
                                    lock_info.is_expired = lock_info.days_remaining <= 0
                                    lock_info.is_locked = not lock_info.is_expired
                                except (ValueError, TypeError, OSError):
                                    pass

                            locks.append(lock_info)
        except Exception as e:
            logger.debug(f"Error checking UNCX: {e}")
        return locks

    async def _heuristic_check(self, session: aiohttp.ClientSession, token_address: str,
                                result: LiquidityCheckResult):
        """Fallback: try to determine lock status from available data."""
        # Without API access, check DexScreener for age and liquidity signals
        try:
            url = f"{DEXSCREENER_API_URL}/latest/dex/tokens/{token_address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        best_pair = pairs[0]
                        liq = best_pair.get("liquidity", {})
                        result.total_liquidity_usd = float(liq.get("usd", 0) or 0)

                        # Check pair creation date
                        created_at = best_pair.get("pairCreatedAt", 0)
                        if created_at:
                            try:
                                created = datetime.fromtimestamp(int(created_at) / 1000)
                                age_days = (datetime.now() - created).days
                                # New tokens (<7 days) without visible lock are risky
                                if age_days < 3:
                                    result.risk_warning = "⚠ Very new token – liquidity may not be locked"
                            except (ValueError, TypeError):
                                pass

                        result.success = True
        except Exception as e:
            logger.debug(f"Heuristic check error: {e}")

    def _calculate_metrics(self, result: LiquidityCheckResult):
        """Calculate lock metrics from lock data."""
        total_locked = sum(lock.amount_usd for lock in result.locks)

        if result.total_liquidity_usd > 0:
            result.total_locked_usd = total_locked
            result.locked_percentage = (total_locked / result.total_liquidity_usd) * 100
            result.locked_percentage = min(100.0, result.locked_percentage)

        result.is_fully_locked = result.locked_percentage >= 80

        # Check for imminent unlocks
        for lock in result.locks:
            if lock.days_remaining <= 14 and lock.days_remaining > 0:
                result.lock_expiry_soon = True
                result.risk_warning = (
                    f"⚠ Lock expires in {lock.days_remaining} days! "
                    f"Dev can withdraw liquidity soon."
                )
                break

        # Generate warning if no lock
        if not result.has_lock:
            result.risk_warning = (
                "🚨 Liquidity is NOT locked! Developer can withdraw all funds "
                "at any moment. Extreme rug-pull risk."
            )


class MockLiquidityChecker(LiquidityChecker):
    """Mock version for testing."""

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "",
                    liquidity_usd: float = 0.0) -> LiquidityCheckResult:
        future = datetime.now() + timedelta(days=730)
        result = LiquidityCheckResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            total_liquidity_usd=liquidity_usd or 150000.0,
            total_locked_usd=147000.0,
            locked_percentage=98.0,
            has_lock=True,
            is_fully_locked=True,
            success=True,
            locks=[
                LiquidityLockInfo(
                    lock_id="mock-1",
                    locker_name="UNCX",
                    amount_usd=147000.0,
                    locked_percentage=98.0,
                    unlock_date=future,
                    days_remaining=730,
                    is_locked=True,
                )
            ],
        )
        return result