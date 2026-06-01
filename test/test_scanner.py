"""
Tests for the Scanner Module
=============================
Tests BaseScanner and DexScanner using mock DexScreener responses.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
import os

# Add project/sr to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.base_scanner import BaseScanner, TokenData
from scanner.dex_scanner import DexScanner


# ── Mock Data ────────────────────────────────────────────────────

MOCK_DEXSCREENER_PROFILES = [
    {
        "chainId": "base",
        "tokenAddress": "0xPositiveToken0000000000000000000000000000001",
        "name": "Positive Token",
        "symbol": "GOOD",
        "description": "A safe and legitimate token",
        "links": {
            "website": "https://goodtoken.example.com",
            "twitter": "https://twitter.com/goodtoken",
            "telegram": "https://t.me/goodtoken",
            "github": "https://github.com/goodtoken/token",
        },
        "url": "https://dexscreener.com/base/0xPositiveToken",
    },
    {
        "chainId": "base",
        "tokenAddress": "0xNegativeToken0000000000000000000000000000002",
        "name": "Suspicious Token",
        "symbol": "SCAM",
        "description": "",
        "links": {},
        "url": "https://dexscreener.com/base/0xNegativeToken",
    },
    {
        "chainId": "ethereum",  # Should be filtered out
        "tokenAddress": "0xEthereumToken0000000000000000000000000003",
        "name": "ETH Token",
        "symbol": "ETH",
        "description": "Not on Base chain",
        "links": {},
        "url": "https://dexscreener.com/ethereum/0xETH",
    },
]

MOCK_DEXSCREENER_PAIRS = [
    {
        "chainId": "base",
        "dexId": "uniswap",
        "url": "https://dexscreener.com/base/0xPair1",
        "pairAddress": "0xPairAddress1",
        "baseToken": {
            "address": "0xPositiveToken0000000000000000000000000000001",
            "name": "Positive Token",
            "symbol": "GOOD",
        },
        "priceUsd": "0.001",
        "priceChange": {"h24": 5.5},
        "liquidity": {"usd": 50000},
        "volume": {"h24": 25000},
        "marketCap": 100000,
        "info": {
            "socials": [
                {"type": "twitter", "url": "https://twitter.com/goodtoken"},
                {"type": "website", "url": "https://goodtoken.example.com"},
                {"type": "github", "url": "https://github.com/goodtoken/token"},
            ]
        },
    },
    {
        "chainId": "ethereum",  # Should be filtered
        "dexId": "uniswap",
        "url": "https://dexscreener.com/ethereum/0xPair2",
        "pairAddress": "0xPairAddress2",
        "baseToken": {
            "address": "0xEthereumToken0000000000000000000000000003",
            "name": "ETH Token",
            "symbol": "ETH",
        },
        "priceUsd": "100",
        "liquidity": {"usd": 1000000},
        "volume": {"h24": 500000},
        "marketCap": 10000000,
    },
]


# ── Tests: TokenData ─────────────────────────────────────────────

class TestTokenData:
    """Tests for the TokenData dataclass."""

    def test_create_token(self):
        token = TokenData(
            address="0xTest123",
            name="TestToken",
            symbol="TEST",
            chain="base",
            market_cap=50000,
            liquidity_usd=25000,
        )
        assert token.address == "0xTest123"
        assert token.name == "TestToken"
        assert token.symbol == "TEST"
        assert token.chain == "base"
        assert token.market_cap == 50000
        assert token.liquidity_usd == 25000

    def test_token_to_dict(self):
        token = TokenData(
            address="0xTest123",
            name="TestToken",
            symbol="TEST",
            market_cap=50000,
            price_usd=0.001,
        )
        d = token.to_dict()
        assert d["address"] == "0xTest123"
        assert d["name"] == "TestToken"
        assert d["symbol"] == "TEST"
        assert d["market_cap"] == 50000
        assert d["price_usd"] == 0.001
        assert d["chain"] == "base"

    def test_token_repr(self):
        token = TokenData(address="0xTest123TokenLong", name="Test", symbol="TEST")
        r = repr(token)
        assert "TEST" in r
        assert "0xTest123T" in r


# ── Tests: BaseScanner ───────────────────────────────────────────

class TestBaseScanner:
    """Tests for BaseScanner with mocked API responses."""

    @staticmethod
    def _make_async_cm(result):
        """Create an object that supports async with (async context manager)."""
        class AsyncCM:
            def __init__(self, value):
                self.value = value
            async def __aenter__(self):
                return self.value
            async def __aexit__(self, *args):
                pass
        return AsyncCM(result)

    @pytest.mark.asyncio
    async def test_fetch_latest_tokens_profiles(self):
        """Test parsing token profiles from DexScreener."""
        scanner = BaseScanner()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_DEXSCREENER_PROFILES)

        with patch.object(scanner, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_response)
            mock_session.return_value = mock_sess

            tokens = await scanner.fetch_latest_tokens()

            # Should get 2 Base tokens, 1 Ethereum filtered out
            assert len(tokens) == 2

            # Check first token
            assert tokens[0].address == "0xpositivetoken0000000000000000000000000000001"
            assert tokens[0].name == "Positive Token"
            assert tokens[0].symbol == "GOOD"
            assert tokens[0].chain == "base"
            assert tokens[0].github == "https://github.com/goodtoken/token"
            assert "twitter.com/goodtoken" in tokens[0].twitter

            # Check second
            assert tokens[1].symbol == "SCAM"

    @pytest.mark.asyncio
    async def test_fetch_latest_tokens_search_fallback(self):
        """Test fallback to search when profiles return empty."""
        scanner = BaseScanner()

        mock_empty = Mock()
        mock_empty.status = 200
        mock_empty.json = AsyncMock(return_value=[])

        mock_search = Mock()
        mock_search.status = 200
        mock_search.json = AsyncMock(return_value={"pairs": MOCK_DEXSCREENER_PAIRS})

        with patch.object(scanner, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.side_effect = [self._make_async_cm(mock_empty), self._make_async_cm(mock_search)]
            mock_session.return_value = mock_sess

            tokens = await scanner.fetch_latest_tokens()

            # Should fall back to search and get 1 Base token
            assert len(tokens) == 1
            assert tokens[0].symbol == "GOOD"
            assert tokens[0].liquidity_usd == 50000
            assert tokens[0].market_cap == 100000

    @pytest.mark.asyncio
    async def test_min_liquidity_filter(self):
        """Test that tokens below min_liquidity_usd are filtered out."""
        scanner = BaseScanner(min_liquidity_usd=100000)

        mock_search = Mock()
        mock_search.status = 200
        mock_search.json = AsyncMock(return_value={"pairs": MOCK_DEXSCREENER_PAIRS})

        with patch.object(scanner, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_search)
            mock_session.return_value = mock_sess

            tokens = await scanner._fetch_base_tokens_search(mock_sess)

            # GOOD has 50k liquidity < 100k min → filtered
            assert len(tokens) == 0

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test graceful handling of API errors."""
        scanner = BaseScanner()

        with patch.object(scanner, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.side_effect = Exception("Network error")
            mock_session.return_value = mock_sess

            tokens = await scanner.fetch_latest_tokens()
            assert tokens == []

    @pytest.mark.asyncio
    async def test_get_token_info(self):
        """Test fetching specific token info."""
        scanner = BaseScanner()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "pairs": [MOCK_DEXSCREENER_PAIRS[0]]
        })

        with patch.object(scanner, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_response)
            mock_session.return_value = mock_sess

            token = await scanner.get_token_info("0xPositiveToken...")
            assert token is not None
            assert token.symbol == "GOOD"

    @pytest.mark.asyncio
    async def test_max_results_limit(self):
        """Test that max_results limits output."""
        scanner = BaseScanner(max_results=1)

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_DEXSCREENER_PROFILES)

        with patch.object(scanner, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_response)
            mock_session.return_value = mock_sess

            tokens = await scanner.fetch_latest_tokens()
            assert len(tokens) <= 1


# ── Tests: DexScanner ────────────────────────────────────────────

class TestDexScanner:
    """Tests for the extended DexScanner."""

    @staticmethod
    def _make_async_cm(result):
        class AsyncCM:
            def __init__(self, value):
                self.value = value
            async def __aenter__(self):
                return self.value
            async def __aexit__(self, *args):
                pass
        return AsyncCM(result)

    @pytest.mark.asyncio
    async def test_get_pairs(self):
        dex = DexScanner()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "pairs": [MOCK_DEXSCREENER_PAIRS[0]]
        })

        with patch.object(dex, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_response)
            mock_session.return_value = mock_sess

            pair = await dex.get_pairs("base", "0xPairAddress1")
            assert pair is not None
            assert pair["baseToken"]["symbol"] == "GOOD"

    @pytest.mark.asyncio
    async def test_search_pairs(self):
        dex = DexScanner()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "pairs": MOCK_DEXSCREENER_PAIRS
        })

        with patch.object(dex, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_response)
            mock_session.return_value = mock_sess

            results = await dex.search_pairs("token")
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_token_pairs_bulk(self):
        dex = DexScanner()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "pairs": [MOCK_DEXSCREENER_PAIRS[0]]
        })

        with patch.object(dex, "_get_session") as mock_session:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_response)
            mock_session.return_value = mock_sess

            result = await dex.get_token_pairs_bulk([
                "0xPositiveToken0000000000000000000000000000001"
            ])
            assert "0xpositivetoken0000000000000000000000000000001" in result
            assert len(result["0xpositivetoken0000000000000000000000000000001"]) == 1

    @pytest.mark.asyncio
    async def test_close_session(self):
        dex = DexScanner()
        # Should not raise
        await dex.close()


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def sample_token_data():
    return TokenData(
        address="0xTest123",
        name="Test Token",
        symbol="TEST",
        chain="base",
        liquidity_usd=100000,
    )