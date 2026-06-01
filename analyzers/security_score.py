"""
Security Score Analyzer - GoPlus Security API
==============================================
Fetches the safety score badge (0-100) for tokens using
the GoPlus Token Security API. Returns a gauge-style score
with detailed risk flags.
"""
import asyncio
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

import aiohttp

logger = logging.getLogger(__name__)

# GoPlus Security API
GOPLUS_API_URL = "https://api.gopluslabs.io/api/v1/token_security"
CHAIN_ID = "8453"  # Base chain ID for GoPlus


@dataclass
class SecurityScoreResult:
    """Result of a security score analysis."""

    token_address: str
    token_name: str = ""
    token_symbol: str = ""
    score: int = 0  # 0-100
    is_safe: bool = False
    risk_flags: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    buy_tax: float = 0.0
    sell_tax: float = 0.0
    is_honeypot: bool = False
    is_open_source: bool = False
    has_proxy: bool = False
    is_mintable: bool = False
    can_take_back_ownership: bool = False
    hidden_owner: bool = False
    transfer_pausable: bool = False
    is_blacklisted: bool = False
    is_whitelisted: bool = False
    is_anti_whale: bool = False
    slippage_modifiable: bool = False
    trading_cooldown: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error_message: str = ""

    def to_dict(self) -> Dict:
        return {
            "token_address": self.token_address,
            "token_name": self.token_name,
            "token_symbol": self.token_symbol,
            "score": self.score,
            "is_safe": self.is_safe,
            "risk_flags": self.risk_flags,
            "issues": self.issues,
            "buy_tax": self.buy_tax,
            "sell_tax": self.sell_tax,
            "is_honeypot": self.is_honeypot,
            "is_open_source": self.is_open_source,
            "has_proxy": self.has_proxy,
            "is_mintable": self.is_mintable,
            "can_take_back_ownership": self.can_take_back_ownership,
            "hidden_owner": self.hidden_owner,
            "transfer_pausable": self.transfer_pausable,
            "is_blacklisted": self.is_blacklisted,
            "is_whitelisted": self.is_whitelisted,
            "is_anti_whale": self.is_anti_whale,
            "slippage_modifiable": self.slippage_modifiable,
            "success": self.success,
        }

    @property
    def score_color(self) -> str:
        """Return hex color for the score."""
        if self.score >= 80:
            return "#22c55e"  # green
        elif self.score >= 50:
            return "#f59e0b"  # amber/yellow
        else:
            return "#ef4444"  # red

    @property
    def score_label(self) -> str:
        """Return a human-readable label for the score."""
        if self.score >= 80:
            return "SAFE ✓"
        elif self.score >= 50:
            return "CAUTION ⚠"
        else:
            return "DANGER ✗"

    @property
    def summary(self) -> str:
        """One-line summary."""
        flags = len(self.risk_flags)
        if flags == 0:
            return f"{self.score}/100 – No flags triggered"
        return f"{self.score}/100 – {flags} flag(s) triggered"


class SecurityScoreChecker:
    """Checks token security using GoPlus Security API."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "BaseBot/1.0 SecurityChecker"},
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "") -> SecurityScoreResult:
        """
        Run a full security check on a token address.
        Returns a SecurityScoreResult.
        """
        result = SecurityScoreResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
        )

        session = await self._get_session()
        try:
            params = {"contract_addresses": token_address, "chain_id": CHAIN_ID}
            async with session.get(GOPLUS_API_URL, params=params) as resp:
                if resp.status != 200:
                    result.error_message = f"GoPlus API returned {resp.status}"
                    logger.warning(result.error_message)
                    return result

                data = await resp.json()
                result.raw_data = data
                self._parse_result(result, data)
                result.success = True
                logger.info(
                    f"Security score for {token_symbol or token_address[:10]}: "
                    f"{result.score}/100 ({result.score_label})"
                )
        except asyncio.TimeoutError:
            result.error_message = "GoPlus API timeout"
            logger.warning(result.error_message)
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Error checking security for {token_address}: {e}")

        return result

    def _parse_result(self, result: SecurityScoreResult, data: Dict):
        """Parse the GoPlus API response and populate result."""
        # Handle the response format: keys are addresses
        result_data = data.get("result", {})
        if not result_data:
            return

        # Try to get data for our address (case-insensitive)
        addr_lower = result.token_address.lower()
        token_data = None
        for key, val in result_data.items():
            if key.lower() == addr_lower:
                token_data = val
                break

        if not token_data:
            # If no exact match, take the first result
            if isinstance(result_data, dict) and result_data:
                token_data = list(result_data.values())[0]

        if not token_data or not isinstance(token_data, dict):
            return

        # Extract fields
        result.is_open_source = self._parse_bool(token_data.get("is_open_source"))
        result.has_proxy = self._parse_bool(token_data.get("is_proxy"))
        result.is_mintable = self._parse_bool(token_data.get("is_mintable"))
        result.can_take_back_ownership = self._parse_bool(token_data.get("can_take_back_ownership"))
        result.hidden_owner = self._parse_bool(token_data.get("hidden_owner"))
        result.transfer_pausable = self._parse_bool(token_data.get("transfer_pausable"))
        result.is_blacklisted = self._parse_bool(token_data.get("is_blacklisted"))
        result.is_whitelisted = self._parse_bool(token_data.get("is_whitelisted"))
        result.is_anti_whale = self._parse_bool(token_data.get("is_anti_whale"))
        result.slippage_modifiable = self._parse_bool(token_data.get("slippage_modifiable"))
        result.trading_cooldown = self._parse_bool(token_data.get("trading_cooldown"))
        result.is_honeypot = self._parse_bool(token_data.get("is_honeypot"))

        # Parse buy/sell tax
        try:
            buy_tax_str = str(token_data.get("buy_tax", "0")).replace("%", "")
            result.buy_tax = float(buy_tax_str)
        except (ValueError, TypeError):
            result.buy_tax = 0.0
        try:
            sell_tax_str = str(token_data.get("sell_tax", "0")).replace("%", "")
            result.sell_tax = float(sell_tax_str)
        except (ValueError, TypeError):
            result.sell_tax = 0.0

        # Determine trust score
        trust_score = 100

        # Deduct for each risk
        if result.is_honeypot:
            trust_score -= 40
            result.risk_flags.append("Honeypot detected")
        if not result.is_open_source:
            trust_score -= 20
            result.risk_flags.append("Contract not open-source")
        if result.has_proxy:
            trust_score -= 25
            result.risk_flags.append("Proxy contract (upgradable)")
        if result.is_mintable:
            trust_score -= 15
            result.risk_flags.append("Mintable token")
        if result.can_take_back_ownership:
            trust_score -= 25
            result.risk_flags.append("Owner can reclaim ownership")
        if result.hidden_owner:
            trust_score -= 30
            result.risk_flags.append("Hidden owner detected")
        if result.transfer_pausable:
            trust_score -= 20
            result.risk_flags.append("Transfer can be paused")
        if result.is_blacklisted:
            trust_score -= 30
            result.risk_flags.append("Address has blacklist function")
        if result.slippage_modifiable:
            trust_score -= 20
            result.risk_flags.append("Slippage is modifiable")
        if result.trading_cooldown:
            trust_score -= 10
            result.risk_flags.append("Trading cooldown enabled")
        if result.buy_tax > 10:
            trust_score -= 15
            result.risk_flags.append(f"High buy tax: {result.buy_tax}%")
        if result.sell_tax > 10:
            trust_score -= 25
            result.risk_flags.append(f"High sell tax: {result.sell_tax}%")

        result.score = max(0, min(100, trust_score))
        result.is_safe = result.score >= 70 and len(result.risk_flags) == 0

        # Collect all issues
        if result.is_honeypot:
            result.issues.append("This token appears to be a honeypot!")
        if result.sell_tax >= 80:
            result.issues.append(f"SELL TAX IS {result.sell_tax}% – likely honeypot")
        if result.hidden_owner:
            result.issues.append("Developer identity is hidden")
        if not result.is_open_source:
            result.issues.append("Contract code is not verified/open-source")

    @staticmethod
    def _parse_bool(val) -> bool:
        """Parse various boolean representations."""
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return val != 0
        if isinstance(val, str):
            return val.lower() in ("1", "true", "yes")
        return False


class MockSecurityScoreChecker(SecurityScoreChecker):
    """Mock version for testing without real API calls."""

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "") -> SecurityScoreResult:
        result = SecurityScoreResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            score=95,
            is_safe=True,
            is_open_source=True,
            success=True,
        )
        return result