"""
Tests for the Analyzers Module
===============================
Tests all five analyzers using mock versions (no real API calls).
Also tests result dataclasses and scoring logic.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzers.security_score import (
    SecurityScoreChecker, SecurityScoreResult, MockSecurityScoreChecker,
)
from analyzers.honeypot_checker import (
    HoneypotChecker, HoneypotResult, MockHoneypotChecker,
)
from analyzers.holders_checker import (
    HoldersChecker, HoldersResult, HolderInfo, MockHoldersChecker,
)
from analyzers.liquidity_checker import (
    LiquidityChecker, LiquidityCheckResult, LiquidityLockInfo, MockLiquidityChecker,
)
from analyzers.github_checker import (
    GitHubChecker, GitHubResult, MockGitHubChecker,
)


# ── Security Score Tests ─────────────────────────────────────────

class TestSecurityScoreResult:
    """Test the SecurityScoreResult dataclass properties."""

    def test_safe_score(self):
        result = SecurityScoreResult(
            token_address="0x123",
            token_name="Safe",
            token_symbol="SAFE",
            score=95,
            is_safe=True,
        )
        assert result.score_color == "#22c55e"  # green
        assert result.score_label == "SAFE ✓"
        assert "No flags triggered" in result.summary

    def test_caution_score(self):
        result = SecurityScoreResult(
            token_address="0x123",
            score=60,
            risk_flags=["High buy tax"],
        )
        assert result.score_color == "#f59e0b"  # amber
        assert result.score_label == "CAUTION ⚠"
        assert "1 flag" in result.summary

    def test_danger_score(self):
        result = SecurityScoreResult(
            token_address="0x123",
            score=20,
            is_honeypot=True,
            risk_flags=["Honeypot detected", "Hidden owner"],
        )
        assert result.score_color == "#ef4444"  # red
        assert result.score_label == "DANGER ✗"
        assert "2 flag" in result.summary

    def test_to_dict(self):
        result = SecurityScoreResult(
            token_address="0x123",
            token_name="Test",
            token_symbol="TST",
            score=80,
            is_safe=True,
            success=True,
        )
        d = result.to_dict()
        assert d["token_address"] == "0x123"
        assert d["score"] == 80
        assert d["is_safe"] is True
        assert d["success"] is True


class TestMockSecurityScoreChecker:
    """Test the mock security checker."""

    @pytest.mark.asyncio
    async def test_mock_check_returns_safe(self):
        checker = MockSecurityScoreChecker()
        result = await checker.check("0xAnyToken", "TestToken", "TEST")

        assert result.success is True
        assert result.score == 95
        assert result.is_safe is True
        assert result.is_open_source is True
        assert result.is_honeypot is False
        assert len(result.risk_flags) == 0


class TestSecurityScoreChecker:
    """Test the real SecurityScoreChecker with mocked HTTP."""

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
    async def test_parse_safe_token(self):
        """Test parsing a safe token response from GoPlus."""
        from unittest.mock import Mock, AsyncMock, patch

        checker = SecurityScoreChecker()
        mock_resp = Mock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "result": {
                "0xSafeToken": {
                    "is_open_source": "1",
                    "is_proxy": "0",
                    "is_mintable": "0",
                    "is_honeypot": "0",
                    "can_take_back_ownership": "0",
                    "hidden_owner": "0",
                    "transfer_pausable": "0",
                    "is_blacklisted": "0",
                    "is_whitelisted": "0",
                    "is_anti_whale": "0",
                    "slippage_modifiable": "0",
                    "buy_tax": "0.5",
                    "sell_tax": "1.0",
                }
            }
        })

        with patch.object(checker, "_get_session") as mock_sess_fn:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_resp)
            mock_sess_fn.return_value = mock_sess

            result = await checker.check("0xSafeToken", "SafeToken", "SAFE")
            assert result.success is True
            assert result.score >= 80
            assert result.is_safe is True
            assert result.buy_tax == 0.5
            assert result.sell_tax == 1.0

    @pytest.mark.asyncio
    async def test_parse_honeypot_token(self):
        """Test parsing a honeypot token response."""
        from unittest.mock import Mock, AsyncMock, patch

        checker = SecurityScoreChecker()
        mock_resp = Mock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={
            "result": {
                "0xScamToken": {
                    "is_open_source": "0",
                    "is_honeypot": "1",
                    "hidden_owner": "1",
                    "sell_tax": "100",
                }
            }
        })

        with patch.object(checker, "_get_session") as mock_sess_fn:
            mock_sess = Mock()
            mock_sess.get.return_value = self._make_async_cm(mock_resp)
            mock_sess_fn.return_value = mock_sess

            result = await checker.check("0xScamToken", "ScamToken", "SCAM")
            assert result.is_honeypot is True
            assert result.score < 50
            assert result.is_safe is False
            assert "Honeypot detected" in result.risk_flags
            assert any("SELL TAX IS 100.0%" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_api_error_returns_failed_result(self):
        """Test that API errors produce a result with success=False."""
        from unittest.mock import Mock, AsyncMock, patch

        checker = SecurityScoreChecker()
        with patch.object(checker, "_get_session") as mock_sess_fn:
            mock_sess = Mock()
            mock_sess.get.side_effect = Exception("Connection refused")
            mock_sess_fn.return_value = mock_sess

            result = await checker.check("0xAny")
            assert result.success is False
            assert "Connection refused" in result.error_message


# ── Honeypot Checker Tests ───────────────────────────────────────

class TestHoneypotResult:
    """Test HoneypotResult properties."""

    def test_safe_result(self):
        result = HoneypotResult(
            token_address="0x123",
            token_name="Safe",
            token_symbol="SAFE",
            is_honeypot=False,
            sell_success=True,
            success=True,
        )
        assert result.is_safe is True
        assert "SAFE" in result.status_text
        assert result.status_color == "#22c55e"

    def test_honeypot_result(self):
        result = HoneypotResult(
            token_address="0x123",
            is_honeypot=True,
            sell_success=False,
            success=True,
            sell_tax=100.0,
        )
        assert result.is_safe is False
        assert "HONEYPOT" in result.status_text
        assert result.status_color == "#ef4444"

    def test_unknown_result(self):
        result = HoneypotResult(token_address="0x123", success=False)
        assert "Could not verify" in result.status_text
        assert result.status_color == "#9ca3af"


class TestMockHoneypotChecker:
    """Test the mock honeypot checker."""

    @pytest.mark.asyncio
    async def test_mock_returns_safe(self):
        checker = MockHoneypotChecker()
        result = await checker.check("0xAny")

        assert result.is_honeypot is False
        assert result.is_safe is True
        assert result.sell_success is True
        assert "Does not seem to be a honeypot" in result.summary


# ── Holders Checker Tests ────────────────────────────────────────

class TestHoldersResult:
    """Test HoldersResult properties."""

    def test_low_concentration(self):
        result = HoldersResult(
            token_address="0x123",
            total_holders=2500,
            creator_percentage=8.5,
            top_5_percentage=25.0,
            top_10_percentage=45.0,
            concentration_level="low",
            success=True,
        )
        assert result.is_safe is True
        assert "Well distributed" in result.status_text
        assert result.status_color == "#22c55e"

    def test_extreme_concentration(self):
        result = HoldersResult(
            token_address="0x123",
            creator_percentage=75.0,
            top_5_percentage=95.0,
            concentration_level="extreme",
            success=True,
            risk_warning="Extreme rug-pull risk",
        )
        assert result.is_safe is False
        assert "EXTREME" in result.status_text
        assert result.status_color == "#7f1d1d"

    def test_chart_data(self):
        result = HoldersResult(
            token_address="0x123",
            top_holders=[
                HolderInfo(address="0xDev", percentage=20.0),
                HolderInfo(address="0xLP", percentage=30.0),
            ],
        )
        data = result.chart_data
        assert len(data) == 3  # 2 holders + "Others"
        assert data[0]["percentage"] == 20.0
        assert data[2]["percentage"] == 50.0  # Others


class TestMockHoldersChecker:
    """Test the mock holders checker."""

    @pytest.mark.asyncio
    async def test_mock_returns_safe_distribution(self):
        checker = MockHoldersChecker()
        result = await checker.check("0xAny", "Test", "TST")

        assert result.success is True
        assert result.total_holders == 2500
        assert result.concentration_level == "low"
        assert result.is_safe is True
        assert result.creator_percentage == 8.5


# ── Liquidity Checker Tests ──────────────────────────────────────

class TestLiquidityCheckResult:
    """Test LiquidityCheckResult properties."""

    def test_fully_locked(self):
        result = LiquidityCheckResult(
            token_address="0x123",
            total_liquidity_usd=150000,
            total_locked_usd=147000,
            locked_percentage=98.0,
            has_lock=True,
            is_fully_locked=True,
            success=True,
        )
        assert result.is_safe is True
        assert "LOCKED 98%" in result.status_text
        assert result.status_color == "#22c55e"

    def test_no_lock(self):
        result = LiquidityCheckResult(
            token_address="0x123",
            has_lock=False,
            locked_percentage=0.0,
            success=True,
        )
        assert result.is_safe is False
        assert "NO LOCK" in result.status_text
        assert result.status_color == "#ef4444"

    def test_partial_lock(self):
        result = LiquidityCheckResult(
            token_address="0x123",
            locked_percentage=50.0,
            has_lock=True,
            success=True,
        )
        assert result.is_safe is True  # >40%, no expiry
        assert "LOCKED 50%" in result.status_text

    def test_lock_expiring_soon(self):
        result = LiquidityCheckResult(
            token_address="0x123",
            locked_percentage=90.0,
            has_lock=True,
            lock_expiry_soon=True,
            risk_warning="Lock expires in 7 days",
            success=True,
        )
        assert result.is_safe is False  # Expiring soon


class TestMockLiquidityChecker:
    """Test the mock liquidity checker."""

    @pytest.mark.asyncio
    async def test_mock_returns_locked(self):
        checker = MockLiquidityChecker()
        result = await checker.check("0xAny", "Test", "TST")

        assert result.success is True
        assert result.has_lock is True
        assert result.locked_percentage == 98.0
        assert result.is_safe is True
        assert len(result.locks) == 1
        assert result.locks[0].days_remaining == 730


# ── GitHub Checker Tests ─────────────────────────────────────────

class TestGitHubResult:
    """Test GitHubResult properties."""

    def test_active_repo(self):
        result = GitHubResult(
            token_address="0x123",
            repo_url="https://github.com/dev/repo",
            stars=100,
            forks=20,
            has_readme=True,
            has_license=True,
            days_since_last_update=3,
            is_active=True,
            found_repo=True,
            score=85,
            success=True,
        )
        assert result.status_color == "#22c55e"
        assert "Active" in result.status_text

    def test_no_repo(self):
        result = GitHubResult(
            token_address="0x123",
            found_repo=False,
            success=True,
        )
        assert "No GitHub" in result.status_text
        assert result.status_color == "#9ca3af"
        assert result.score == 0

    def test_archived_repo(self):
        result = GitHubResult(
            token_address="0x123",
            found_repo=True,
            is_archived=True,
            score=20,
            success=True,
        )
        assert "archived" in result.risk_warning.lower()


class TestMockGitHubChecker:
    """Test the mock GitHub checker."""

    @pytest.mark.asyncio
    async def test_mock_returns_legitimate(self):
        checker = MockGitHubChecker()
        result = await checker.check("0xAny", "Test", "TST", "https://github.com/test/tst")

        assert result.success is True
        assert result.found_repo is True
        assert result.score == 85
        assert result.is_legitimate is True
        assert result.stars == 42
        assert result.has_readme is True
        assert result.has_license is True

    @pytest.mark.asyncio
    async def test_mock_without_url(self):
        checker = MockGitHubChecker()
        result = await checker.check("0xAny", "TestToken", "TST")

        assert result.found_repo is True
        assert "github.com" in result.repo_url


# ── Integration: Multiple Analyzers ──────────────────────────────

class TestAnalyzerIntegration:
    """Test that all mock analyzers work together."""

    @pytest.mark.asyncio
    async def test_all_mocks_return_safe(self):
        """All mock analyzers should return safe/positive results."""
        token_addr = "0xTestToken001"

        security = await MockSecurityScoreChecker().check(token_addr)
        honeypot = await MockHoneypotChecker().check(token_addr)
        holders = await MockHoldersChecker().check(token_addr)
        liquidity = await MockLiquidityChecker().check(token_addr)
        github = await MockGitHubChecker().check(token_addr)

        assert security.is_safe is True
        assert honeypot.is_safe is True
        assert holders.is_safe is True
        assert liquidity.is_safe is True
        assert github.is_legitimate is True

    @pytest.mark.asyncio
    async def test_result_to_dict_serializable(self):
        """Ensure all result types produce serializable dicts."""
        import json

        results = [
            (await MockSecurityScoreChecker().check("0x1")).to_dict(),
            (await MockHoneypotChecker().check("0x1")).to_dict(),
            (await MockHoldersChecker().check("0x1")).to_dict(),
            (await MockLiquidityChecker().check("0x1")).to_dict(),
            (await MockGitHubChecker().check("0x1")).to_dict(),
        ]

        for r in results:
            # Should not raise
            json.dumps(r, default=str)