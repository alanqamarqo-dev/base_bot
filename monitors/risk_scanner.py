"""
Fast Risk Scanner - Phase 3
=============================
Runs the existing 4 analyzers (Security, Honeypot, Holders, Liquidity)
concurrently on each token that gets liquidity.

Uses asyncio.gather for parallel execution to minimize latency.
Reuses existing analyzer classes WITHOUT modification.
"""

import asyncio
import logging
import sys
import os
from typing import Optional
from dataclasses import dataclass, field

# Ensure parent directory is in path for existing analyzers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzers.security_score import SecurityScoreChecker, SecurityScoreResult
from analyzers.honeypot_checker import HoneypotChecker, HoneypotResult
from analyzers.holders_checker import HoldersChecker, HoldersResult
from analyzers.liquidity_checker import LiquidityChecker, LiquidityCheckResult

from config.settings import settings
from monitors.liquidity_monitor import LiquidityEvent

logger = logging.getLogger("RiskScanner")


@dataclass
class RiskScanResult:
    """Aggregated result from all 4 analyzers."""
    token_address: str
    token_symbol: str = ""
    token_name: str = ""

    # Security
    security_score: int = 0
    security_flags: list = field(default_factory=list)
    has_proxy: bool = False
    is_mintable: bool = False
    is_blacklisted: bool = False
    is_whitelisted: bool = False
    owner_renounced: bool = False
    can_take_back_ownership: bool = False
    transfer_pausable: bool = False
    is_open_source: bool = False

    # Honeypot
    is_honeypot: bool = True  # Assume honeypot until proven otherwise
    buy_success: bool = False
    sell_success: bool = False
    buy_tax: float = 0.0
    sell_tax: float = 0.0
    honeypot_flags: list = field(default_factory=list)

    # Holders
    total_holders: int = 0
    holders_concentration: str = "unknown"
    creator_percentage: float = 0.0
    top_10_percentage: float = 0.0

    # Liquidity
    total_liquidity_usd: float = 0.0
    locked_percentage: float = 0.0
    has_lock: bool = False

    # Meta
    success: bool = False
    error_message: str = ""
    scan_duration_ms: float = 0.0

    @property
    def overall_risk_score(self) -> int:
        """Quick combined risk score (0-100, higher = safer)."""
        score = self.security_score
        if self.is_honeypot:
            score = min(score, 20)
        if self.sell_tax > 50:
            score = min(score, 30)
        if self.holders_concentration == "extreme":
            score = min(score, 40)
        if self.holders_concentration == "high":
            score = min(score, 60)
        return score

    def to_dict(self) -> dict:
        return {
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "token_name": self.token_name,
            "security_score": self.security_score,
            "security_flags": self.security_flags,
            "has_proxy": self.has_proxy,
            "is_mintable": self.is_mintable,
            "is_blacklisted": self.is_blacklisted,
            "owner_renounced": self.owner_renounced,
            "is_honeypot": self.is_honeypot,
            "buy_tax": self.buy_tax,
            "sell_tax": self.sell_tax,
            "buy_success": self.buy_success,
            "sell_success": self.sell_success,
            "total_holders": self.total_holders,
            "holders_concentration": self.holders_concentration,
            "total_liquidity_usd": self.total_liquidity_usd,
            "locked_percentage": self.locked_percentage,
            "overall_risk_score": self.overall_risk_score,
            "success": self.success,
            "scan_duration_ms": self.scan_duration_ms,
        }


class RiskScanner:
    """
    Fast risk scan using existing analyzers.
    
    Runs Security, Honeypot, Holders, and Liquidity checks
    concurrently via asyncio.gather.
    """

    def __init__(self):
        self.security_checker = SecurityScoreChecker()
        self.honeypot_checker = HoneypotChecker()
        self.holders_checker = HoldersChecker(
            basescan_api_key=settings.analyzers.basescan_api_key
        )
        self.liquidity_checker = LiquidityChecker()
        self._scan_count: int = 0

    async def scan(
        self,
        event: LiquidityEvent,
        token_symbol: str = "",
        token_name: str = "",
    ) -> RiskScanResult:
        """
        Run all 4 analyzers on a token concurrently.
        
        Args:
            event: The liquidity event with token/pair info
            token_symbol: Token symbol (if known)
            token_name: Token name (if known)
        """
        import time
        start = time.time()

        token_address = event.token_address

        result = RiskScanResult(
            token_address=token_address,
            token_symbol=token_symbol,
            token_name=token_name,
            total_liquidity_usd=event.liquidity_usd,
        )

        # Run all 4 analyzers concurrently
        sec_task = self.security_checker.check(token_address, token_name, token_symbol)
        honey_task = self.honeypot_checker.check(token_address, token_name, token_symbol)
        holders_task = self.holders_checker.check(token_address, token_name, token_symbol)
        liq_task = self.liquidity_checker.check(
            token_address, token_name, token_symbol, event.liquidity_usd
        )

        security, honeypot, holders, liquidity = await asyncio.gather(
            sec_task, honey_task, holders_task, liq_task,
            return_exceptions=True,
        )

        # Parse security results
        if isinstance(security, SecurityScoreResult):
            result.security_score = security.score
            result.security_flags = security.risk_flags
            result.has_proxy = security.has_proxy
            result.is_mintable = security.is_mintable
            result.is_blacklisted = security.is_blacklisted
            result.is_whitelisted = security.is_whitelisted
            result.owner_renounced = not security.can_take_back_ownership
            result.can_take_back_ownership = security.can_take_back_ownership
            result.transfer_pausable = security.transfer_pausable
            result.is_open_source = security.is_open_source
        elif isinstance(security, Exception):
            logger.warning(f"Security check failed: {security}")

        # Parse honeypot results
        if isinstance(honeypot, HoneypotResult):
            result.is_honeypot = honeypot.is_honeypot
            result.buy_success = honeypot.buy_success
            result.sell_success = honeypot.sell_success
            result.buy_tax = honeypot.buy_tax
            result.sell_tax = honeypot.sell_tax
            result.honeypot_flags = honeypot.flags
        elif isinstance(honeypot, Exception):
            logger.warning(f"Honeypot check failed: {honeypot}")

        # Parse holders results
        if isinstance(holders, HoldersResult):
            result.total_holders = holders.total_holders
            result.holders_concentration = holders.concentration_level
            result.creator_percentage = holders.creator_percentage
            result.top_10_percentage = holders.top_10_percentage
        elif isinstance(holders, Exception):
            logger.warning(f"Holders check failed: {holders}")

        # Parse liquidity lock results
        if isinstance(liquidity, LiquidityCheckResult):
            result.locked_percentage = liquidity.locked_percentage
            result.has_lock = liquidity.has_lock
        elif isinstance(liquidity, Exception):
            logger.warning(f"Liquidity check failed: {liquidity}")

        # Mark success if at least one analyzer worked
        result.success = (
            isinstance(security, SecurityScoreResult)
            or isinstance(honeypot, HoneypotResult)
        )

        result.scan_duration_ms = (time.time() - start) * 1000
        self._scan_count += 1

        logger.info(
            f"🛡️ Risk scan for {token_symbol or token_address[:10]}: "
            f"Security:{result.security_score}/100 "
            f"Honeypot:{'YES' if result.is_honeypot else 'NO'} "
            f"Holders:{result.holders_concentration} "
            f"({result.scan_duration_ms:.0f}ms)"
        )

        return result

    async def close(self):
        """Clean up analyzer sessions."""
        await self.security_checker.close()
        await self.honeypot_checker.close()
        await self.holders_checker.close()
        await self.liquidity_checker.close()

    @property
    def scan_count(self) -> int:
        return self._scan_count
