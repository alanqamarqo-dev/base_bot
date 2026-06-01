"""
Honeypot Checker - Honeypot.is Integration
==========================================
Checks whether a token is a honeypot (cannot sell after buying).
Uses the Honeypot.is API to produce a clear PASS/FAIL result.
"""
import asyncio
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

import aiohttp

logger = logging.getLogger(__name__)

# Honeypot.is API (public endpoint)
HONEYPOT_API_URL = "https://api.honeypot.is/v2"


@dataclass
class HoneypotResult:
    """Result of a honeypot check."""

    token_address: str
    token_name: str = ""
    token_symbol: str = ""
    is_honeypot: bool = True  # safer default: assume honeypot until proven otherwise
    simulation_success: bool = False
    buy_success: bool = False
    sell_success: bool = False
    buy_tax: float = 0.0
    sell_tax: float = 0.0
    max_buy_amount: float = 0.0
    max_sell_amount: float = 0.0
    summary: str = ""
    flags: list = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error_message: str = ""

    @property
    def is_safe(self) -> bool:
        return not self.is_honeypot and self.sell_success

    @property
    def status_text(self) -> str:
        if not self.success:
            return "⚠ Could not verify"
        if self.is_safe:
            return "✅ SAFE – Does not seem to be a honeypot"
        return "🚨 HONEYPOT DETECTED – Run away!"

    @property
    def status_color(self) -> str:
        if not self.success:
            return "#9ca3af"  # gray
        if self.is_safe:
            return "#22c55e"  # green
        return "#ef4444"  # red

    def to_dict(self) -> Dict:
        return {
            "token_address": self.token_address,
            "token_name": self.token_name,
            "token_symbol": self.token_symbol,
            "is_honeypot": self.is_honeypot,
            "is_safe": self.is_safe,
            "simulation_success": self.simulation_success,
            "buy_success": self.buy_success,
            "sell_success": self.sell_success,
            "buy_tax": self.buy_tax,
            "sell_tax": self.sell_tax,
            "summary": self.summary,
            "flags": self.flags,
            "status_text": self.status_text,
            "success": self.success,
        }


class HoneypotChecker:
    """Checks tokens for honeypot behavior using Honeypot.is API."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "User-Agent": "BaseBot/1.0 HoneypotChecker",
                    "Accept": "application/json",
                },
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "") -> HoneypotResult:
        """
        Check if a token is a honeypot.
        """
        result = HoneypotResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
        )

        session = await self._get_session()
        try:
            # Try the main API endpoint
            url = f"{HONEYPOT_API_URL}/check/8453/{token_address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result.raw_data = data
                    self._parse_result(result, data)
                    result.success = True
                elif resp.status == 404:
                    # Token not yet indexed; try simulation endpoint
                    result = await self._simulate_check(session, token_address, result)
                else:
                    result.error_message = f"API returned status {resp.status}"
                    logger.warning(result.error_message)
                    # Try fallback simulation
                    result = await self._simulate_check(session, token_address, result)
        except asyncio.TimeoutError:
            result.error_message = "Honeypot API timeout"
            logger.warning(result.error_message)
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Error checking honeypot for {token_address}: {e}")

        logger.info(
            f"Honeypot check for {token_symbol or token_address[:10]}: "
            f"{result.status_text}"
        )
        return result

    async def _simulate_check(
        self, session: aiohttp.ClientSession, token_address: str, result: HoneypotResult
    ) -> HoneypotResult:
        """Fallback: run a simulation-based check."""
        try:
            url = f"{HONEYPOT_API_URL}/simulate/8453/{token_address}"
            data = {
                "tokenAddress": token_address,
                "chainId": 8453,
                "buyAmount": "0.001",
            }
            async with session.post(url, json=data) as resp:
                if resp.status == 200:
                    sim_data = await resp.json()
                    result.raw_data = sim_data
                    self._parse_simulation(result, sim_data)
                    result.success = True
                else:
                    result.error_message = f"Simulation check failed: {resp.status}"
        except Exception as e:
            result.error_message = f"Simulation error: {e}"

        return result

    def _parse_result(self, result: HoneypotResult, data: Dict):
        """Parse the main API response."""
        # Honeypot.is typical response structure
        is_honeypot = data.get("isHoneypot", data.get("is_honeypot", True))
        result.is_honeypot = bool(is_honeypot)

        summary = data.get("summary", "")
        result.summary = str(summary) if summary else ""

        # Parse flags
        flags = data.get("flags", [])
        if isinstance(flags, list):
            result.flags = [str(f) for f in flags]

        # Parse taxes
        buy_tax = data.get("buyTax", data.get("buy_tax", 0))
        sell_tax = data.get("sellTax", data.get("sell_tax", 0))
        try:
            result.buy_tax = float(buy_tax)
        except (ValueError, TypeError):
            pass
        try:
            result.sell_tax = float(sell_tax)
        except (ValueError, TypeError):
            pass

        # Buy/sell simulation results
        buy_result = data.get("buyResult", data.get("buy_result", ""))
        sell_result = data.get("sellResult", data.get("sell_result", ""))
        result.buy_success = "success" in str(buy_result).lower()
        result.sell_success = "success" in str(sell_result).lower()

        # Override honeypot based on sell tax
        if result.sell_tax >= 80:
            result.is_honeypot = True
            if "Sell tax is extremely high" not in result.flags:
                result.flags.append("Sell tax is extremely high")

        # Generate summary
        if result.is_honeypot:
            result.summary = result.summary or "Honeypot detected! Cannot sell."
        else:
            result.summary = result.summary or "Does not seem to be a honeypot."

    def _parse_simulation(self, result: HoneypotResult, data: Dict):
        """Parse simulation response."""
        result.simulation_success = True

        # Check simulation results
        sim = data.get("simulation", data) if isinstance(data, dict) else {}

        result.buy_success = sim.get("buySuccess", sim.get("buyResult", True))
        result.sell_success = sim.get("sellSuccess", sim.get("sellResult", True))

        # Extract taxes
        buy_tax = sim.get("buyTax", 0)
        sell_tax = sim.get("sellTax", 0)
        try:
            result.buy_tax = float(buy_tax)
        except (ValueError, TypeError):
            pass
        try:
            result.sell_tax = float(sell_tax)
        except (ValueError, TypeError):
            pass

        # Determine honeypot status
        if not result.sell_success or result.sell_tax >= 80:
            result.is_honeypot = True
            result.summary = "Honeypot detected via simulation!"
        else:
            result.is_honeypot = False
            result.summary = "Does not appear to be a honeypot (simulated)."


class MockHoneypotChecker(HoneypotChecker):
    """Mock version for testing without real API calls."""

    async def check(self, token_address: str, token_name: str = "", token_symbol: str = "") -> HoneypotResult:
        result = HoneypotResult(
            token_address=token_address,
            token_name=token_name,
            token_symbol=token_symbol,
            is_honeypot=False,
            sell_success=True,
            buy_success=True,
            summary="Does not seem to be a honeypot.",
            success=True,
        )
        return result