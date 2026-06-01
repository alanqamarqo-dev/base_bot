"""
DexScanner - Extended DexScreener Integration
==============================================
Provides additional DexScreener functionality for pair data,
OHLCV charts, and deeper token analysis.
"""
import asyncio
import logging
from typing import List, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)

DEXSCREENER_BASE = "https://api.dexscreener.com"


class DexScanner:
    """Extended DexScreener API integration."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "BaseBot/1.0 DexScanner"},
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_pairs(self, chain_id: str, pair_address: str) -> Optional[Dict]:
        """Get detailed info about a specific trading pair."""
        session = await self._get_session()
        try:
            url = f"{DEXSCREENER_BASE}/latest/dex/pairs/{chain_id}/{pair_address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        return pairs[0]
        except Exception as e:
            logger.error(f"Error fetching pair {pair_address}: {e}")
        return None

    async def search_pairs(self, query: str) -> List[Dict]:
        """Search DexScreener for pairs."""
        session = await self._get_session()
        try:
            params = {"q": query}
            url = f"{DEXSCREENER_BASE}/latest/dex/search"
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("pairs", [])
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
        return []

    async def get_token_pairs_bulk(self, addresses: List[str]) -> Dict[str, List[Dict]]:
        """Bulk fetch pairs for multiple token addresses."""
        result = {}
        for i in range(0, len(addresses), 30):
            batch = addresses[i : i + 30]
            addr_str = ",".join(batch)
            session = await self._get_session()
            try:
                url = f"{DEXSCREENER_BASE}/latest/dex/tokens/{addr_str}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        pairs = data.get("pairs", [])
                        for pair in pairs:
                            base = pair.get("baseToken", {})
                            addr = base.get("address", "").lower()
                            if addr not in result:
                                result[addr] = []
                            result[addr].append(pair)
            except Exception as e:
                logger.error(f"Error fetching bulk pairs: {e}")
        logger.info(f"Fetched pairs bulk: {len(result)} tokens from {len(addresses)} addresses")
        return result