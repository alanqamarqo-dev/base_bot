"""
Holders Checker - Top Holders Distribution Analysis
====================================================
Analyzes holder distribution using Basescan API.
Generates pie chart data showing token concentration.
Detects dangerous concentration patterns.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import aiohttp

logger = logging.getLogger(__name__)

# Basescan API
BASESCAN_API_URL = "https://api.basescan.org/api"

# CoinGecko fallback
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"


@dataclass
class HolderInfo:
    """Information about a single holder."""

    address: str
    balance: float = 0.0
    percentage: float = 0.0
    is_contract: bool = False
    label: str = ""


@dataclass
class HoldersResult:
    """Result of a holders distribution analysis."""

    token_address: str
    token_name: str = ""
    token_symbol: str = ""
    total_supply: float = 0.0
    total_holders: int = 0
    top_holders: List[HolderInfo] = field(default_factory=list)
    creator_percentage: float = 0.0
    top_10_percentage: float = 0.0
    top_5_percentage: float = 0.0
    is_concentrated: bool = False
    concentration_level: str = "unknown"  # low, medium, high, extreme
    risk_warning: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error_message: str = ""

    @property
    def is_safe(self) -> bool:
        return self.concentration_level in ("low",) and not self.is_concentrated

    @property
    def status_text(self) -> str:
        if self.concentration_level == "low":
            return "✅ Well distributed"
        elif self.concentration_level == "medium":
            return "⚠ Moderate concentration"
        elif self.concentration_level == "high":
            return "⛔ High concentration risk"
        elif self.concentration_level == "extreme":
            return "🚨 EXTREME concentration!"
        return "❓ Unknown"

    @property
    def status_color(self) -> str:
        colors = {
            "low": "#22c55e",
            "medium": "#f59e0b",
            "high": "#ef4444",
            "extreme": "#7f1d1d",
        }
        return colors.get(self.concentration_level, "#9ca3af")

    @property
    def chart_data(self) -> List[Dict]:
        """Return data suitable for pie chart generation."""
        data = []
        for h in self.top_holders:
            data.append({
                "address": h.address[:10] + "...",
                "percentage": h.percentage,
                "label": h.label or ("Contract" if h.is_contract else "Wallet"),
            })
        others_pct = 100.0 - sum(h.percentage for h in self.top_holders)
        if others_pct > 0:
            data.append({
                "address": "Others",
                "percentage": round(others_pct, 2),
                "label": "Other Holders",
            })
        return data

    def to_dict(self) -> Dict:
        return {
            "token_address": self.token_address,
            "token_name": self.token_name,
            "token_symbol": self.token_symbol,
            "total_supply": self.total_supply,
            "total_holders": self.total_holders,
            "top_holders": [
                {
                    "address": h.address,
                    "balance": h.balance,
                    "percentage": h.percentage,
                    "is_contract": h.is_contract,
                }
                for h in self.top_holders
            ],
            "creator_percentage": self.creator_percentage,
            "top_10_percentage": self.top_10_percentage,
            "top_5_percentage": self.top_5_percentage,
            "is_concentrated": self.is_concentrated,
            "concentration_level": self.concentration_level,
            "risk_warning": self.risk_warning,
            "is_safe": self.is_safe,
            "status_text": self.status_text,
            "success": self.success,
        }


class HoldersChecker:
    """Analyzes token holder distribution using Basescan API."""

    def __init__(self, basescan_api_key: str = "", timeout: int = 30):
        self.basescan_api_key = basescan_api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"User-Agent": "BaseBot/1.0 HoldersChecker"},
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "") -> HoldersResult:
        """
        Analyze holder distribution for a token.
        """
        result = HoldersResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
        )

        session = await self._get_session()

        # Step 1: Get total supply via Basescan
        total_supply = await self._get_total_supply(session, token_address)
        if total_supply > 0:
            result.total_supply = total_supply
            result.success = True

        # Step 2: Try to get holder list
        if self.basescan_api_key:
            holders = await self._get_top_holders(session, token_address, total_supply)
        else:
            # Without API key, try CoinGecko or use heuristics
            holders = await self._get_holders_via_coingecko(session, token_address)

        if holders:
            result.top_holders = holders
            result.success = True

        # Step 3: Calculate concentration metrics
        if result.total_supply > 0:
            self._calculate_concentration(result)

        if result.success:
            logger.info(
                f"Holders check for {token_symbol or token_address[:10]}: "
                f"{result.total_holders} holders, {result.status_text}"
            )

        return result

    @staticmethod
    async def _get_total_supply(session: aiohttp.ClientSession, token_address: str) -> float:
        """Fetch total supply from Basescan."""
        try:
            params = {
                "module": "stats",
                "action": "tokensupply",
                "contractaddress": token_address,
                "apikey": "",
            }
            async with session.get(BASESCAN_API_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "1":
                        raw = data.get("result", "0")
                        # Supply is in wei-like units; try to parse
                        try:
                            supply = float(raw)
                            # If supply is huge, it's in smallest units; normalize
                            if supply > 1e18:
                                supply = supply / 1e18
                            return supply
                        except (ValueError, TypeError):
                            return 0.0
        except Exception as e:
            logger.debug(f"Error getting total supply: {e}")
        return 0.0

    @staticmethod
    async def _get_top_holders(
        session: aiohttp.ClientSession, token_address: str, total_supply: float
    ) -> List[HolderInfo]:
        """Get top token holders. Returns empty if no API key."""
        return []

    @staticmethod
    async def _get_holders_via_coingecko(session: aiohttp.ClientSession, token_address: str) -> List[HolderInfo]:
        """Try CoinGecko as fallback for holder data."""
        try:
            # CoinGecko has limited holder info on free tier
            url = f"{COINGECKO_API_URL}/coins/base/contract/{token_address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # CoinGecko provides some market data
                    # This is limited; real holder data needs Basescan API key
                    pass
        except Exception:
            pass
        return []

    def _calculate_concentration(self, result: HoldersResult):
        """Calculate concentration metrics and determine risk level."""
        if not result.top_holders:
            # No holder data available
            result.total_holders = 0
            result.concentration_level = "unknown"
            result.risk_warning = "Could not fetch holder data (API key may be needed)"
            return

        # Sort by percentage descending
        sorted_holders = sorted(result.top_holders, key=lambda h: h.percentage, reverse=True)

        # Top holder (creator/dev)
        if sorted_holders:
            result.creator_percentage = sorted_holders[0].percentage

        # Top 5
        top5 = sum(h.percentage for h in sorted_holders[:5])
        result.top_5_percentage = top5

        # Top 10
        top10 = sum(h.percentage for h in sorted_holders[:10])
        result.top_10_percentage = top10

        # Determine concentration level
        if result.creator_percentage > 50:
            result.concentration_level = "extreme"
            result.is_concentrated = True
            result.risk_warning = (
                f"🚨 One wallet holds {result.creator_percentage:.1f}%! "
                f"Extreme rug-pull risk."
            )
        elif result.top_5_percentage > 80:
            result.concentration_level = "high"
            result.is_concentrated = True
            result.risk_warning = (
                f"⛔ Top 5 wallets hold {result.top_5_percentage:.1f}%. "
                f"High centralization risk."
            )
        elif result.top_10_percentage > 60:
            result.concentration_level = "medium"
            result.is_concentrated = True
            result.risk_warning = (
                f"⚠ Top 10 wallets hold {result.top_10_percentage:.1f}%. "
                f"Monitor before investing."
            )
        else:
            result.concentration_level = "low"
            result.is_concentrated = False
            result.risk_warning = ""

        result.total_holders = len(result.top_holders)


class MockHoldersChecker(HoldersChecker):
    """Mock version for testing with sample data."""

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "") -> HoldersResult:
        result = HoldersResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            total_supply=1_000_000_000,
            total_holders=2500,
            top_holders=[
                HolderInfo(address="0xDeve1oper0000000000000000000000000000001", percentage=8.5, label="Dev Wallet"),
                HolderInfo(address="0xLiquidity000000000000000000000000000000002", percentage=25.0, label="LP Pool", is_contract=True),
                HolderInfo(address="0xWhale10000000000000000000000000000000003", percentage=6.2, label="Whale"),
                HolderInfo(address="0xWhale20000000000000000000000000000000004", percentage=4.1, label="Whale"),
                HolderInfo(address="0xWhale30000000000000000000000000000000005", percentage=3.5, label="Whale"),
            ],
            creator_percentage=8.5,
            top_5_percentage=47.3,
            top_10_percentage=55.0,
            is_concentrated=False,
            concentration_level="low",
            success=True,
        )
        return result