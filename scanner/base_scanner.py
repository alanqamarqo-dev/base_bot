"""
Scanner Module - Base Chain New Token Discovery
================================================
Uses DexScreener API to discover newly listed tokens on Base chain.
"""
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)

# DexScreener API endpoints
DEXSCREENER_BASE_URL = "https://api.dexscreener.com"
LATEST_PROFILES_URL = f"{DEXSCREENER_BASE_URL}/token-profiles/latest/v1"
SEARCH_URL = f"{DEXSCREENER_BASE_URL}/latest/dex/search"
TOKEN_INFO_URL = f"{DEXSCREENER_BASE_URL}/latest/dex/tokens"


class TokenData:
    """Data class representing a discovered token."""

    def __init__(
        self,
        address: str,
        name: str,
        symbol: str,
        chain: str = "base",
        description: str = "",
        website: str = "",
        twitter: str = "",
        telegram: str = "",
        discord: str = "",
        github: str = "",
        created_at: Optional[datetime] = None,
        market_cap: float = 0.0,
        price_usd: float = 0.0,
        liquidity_usd: float = 0.0,
        volume_24h: float = 0.0,
        price_change_24h: float = 0.0,
        pair_address: str = "",
        dex_url: str = "",
    ):
        self.address = address
        self.name = name
        self.symbol = symbol
        self.chain = chain
        self.description = description
        self.website = website
        self.twitter = twitter
        self.telegram = telegram
        self.discord = discord
        self.github = github
        self.created_at = created_at or datetime.now()
        self.market_cap = market_cap
        self.price_usd = price_usd
        self.liquidity_usd = liquidity_usd
        self.volume_24h = volume_24h
        self.price_change_24h = price_change_24h
        self.pair_address = pair_address
        self.dex_url = dex_url

    def to_dict(self) -> Dict:
        return {
            "address": self.address,
            "name": self.name,
            "symbol": self.symbol,
            "chain": self.chain,
            "description": self.description,
            "website": self.website,
            "twitter": self.twitter,
            "telegram": self.telegram,
            "discord": self.discord,
            "github": self.github,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "market_cap": self.market_cap,
            "price_usd": self.price_usd,
            "liquidity_usd": self.liquidity_usd,
            "volume_24h": self.volume_24h,
            "price_change_24h": self.price_change_24h,
            "pair_address": self.pair_address,
            "dex_url": self.dex_url,
        }

    def __repr__(self):
        return f"TokenData({self.symbol}: {self.address[:10]}...)"


class BaseScanner:
    """
    Scans DexScreener for newly listed tokens on Base chain.
    """

    def __init__(self, max_results: int = 50, min_liquidity_usd: float = 1000.0):
        self.max_results = max_results
        self.min_liquidity_usd = min_liquidity_usd
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "BaseBot/1.0 Token Scanner"},
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def fetch_latest_tokens(self) -> List[TokenData]:
        """
        Fetch the latest token profiles from DexScreener.
        Filters for Base chain tokens only.
        """
        session = await self._get_session()
        tokens = []

        try:
            async with session.get(LATEST_PROFILES_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tokens = self._parse_token_profiles(data)
                    logger.info(f"Fetched {len(tokens)} tokens from DexScreener profiles")
                else:
                    logger.error(f"DexScreener profiles returned status {resp.status}")
        except Exception as e:
            logger.error(f"Error fetching latest tokens: {e}")

        # Fallback: search for Base chain tokens directly
        if not tokens:
            tokens = await self._fetch_base_tokens_search(session)

        return tokens[: self.max_results]

    async def _fetch_base_tokens_search(self, session: aiohttp.ClientSession) -> List[TokenData]:
        """Fallback: search directly for Base chain tokens."""
        tokens = []
        try:
            params = {"q": "base"}
            async with session.get(SEARCH_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    tokens = self._parse_pairs(pairs)
                    logger.info(f"Fetched {len(tokens)} Base tokens via search fallback")
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
        return tokens

    async def get_token_info(self, address: str) -> Optional[TokenData]:
        """Get detailed token info for a specific address."""
        session = await self._get_session()
        try:
            url = f"{TOKEN_INFO_URL}/{address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
                    if pairs:
                        parsed = self._parse_pairs(pairs)
                        if parsed:
                            return parsed[0]
        except Exception as e:
            logger.error(f"Error fetching token info for {address}: {e}")
        return None

    async def fetch_pairs_by_address(self, address: str) -> List[Dict]:
        """Fetch all trading pairs for a token address."""
        session = await self._get_session()
        pairs = []
        try:
            url = f"{TOKEN_INFO_URL}/{address}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])
        except Exception as e:
            logger.error(f"Error fetching pairs: {e}")
        return pairs

    def _parse_token_profiles(self, data: List[Dict]) -> List[TokenData]:
        """Parse the token-profiles/latest/v1 API response."""
        tokens = []
        profile_map = {}

        # First pass: collect profiles
        for item in data:
            chain = item.get("chainId", "").lower()
            if chain != "base":
                continue
            token_address = item.get("tokenAddress", "").lower()
            if not token_address:
                continue
            profile_map[token_address] = item

        # Second pass: create TokenData objects
        for addr, profile in profile_map.items():
            links = profile.get("links", {}) or {}
            token = TokenData(
                address=addr,
                name=profile.get("name") or profile.get("baseToken", {}).get("name", "Unknown"),
                symbol=profile.get("symbol") or profile.get("baseToken", {}).get("symbol", "UNKNOWN"),
                chain="base",
                description=profile.get("description", ""),
                website=links.get("website", ""),
                twitter=links.get("twitter", ""),
                telegram=links.get("telegram", ""),
                discord=links.get("discord", ""),
                github=links.get("github", ""),
                created_at=datetime.now(),
                dex_url=profile.get("url", f"https://dexscreener.com/base/{addr}"),
            )
            tokens.append(token)

        return tokens

    def _parse_pairs(self, pairs: List[Dict]) -> List[TokenData]:
        """Parse DexScreener pairs search response."""
        tokens = []
        seen = set()

        for pair in pairs:
            chain = pair.get("chainId", "").lower()
            if chain != "base":
                continue

            base_token = pair.get("baseToken", {})
            address = base_token.get("address", "").lower()
            if not address or address in seen:
                continue
            seen.add(address)

            info = pair.get("info", {}) or {}
            socials = info.get("socials", []) or []

            # Extract links from socials
            website = ""
            twitter = ""
            telegram_link = ""
            discord = ""
            github = ""
            for s in socials:
                stype = s.get("type", "").lower()
                url = s.get("url", "")
                if stype == "website":
                    website = url
                elif stype == "twitter":
                    twitter = url
                elif stype == "telegram":
                    telegram_link = url
                elif stype == "discord":
                    discord = url
                elif stype == "github":
                    github = url

            token = TokenData(
                address=address,
                name=base_token.get("name", "Unknown"),
                symbol=base_token.get("symbol", "UNKNOWN"),
                chain="base",
                description="",
                website=website,
                twitter=twitter,
                telegram=telegram_link,
                discord=discord,
                github=github,
                created_at=datetime.now(),
                market_cap=float(pair.get("marketCap", 0) or 0),
                price_usd=float(pair.get("priceUsd", 0) or 0),
                liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                price_change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                pair_address=pair.get("pairAddress", ""),
                dex_url=pair.get("url", f"https://dexscreener.com/base/{address}"),
            )

            # Apply liquidity filter
            if token.liquidity_usd >= self.min_liquidity_usd:
                tokens.append(token)

        return tokens