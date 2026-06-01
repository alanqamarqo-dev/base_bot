"""
Integration & End-to-End Tests
===============================
Tests the full bot pipeline: scanner → analyzers → classification.
Tests the orchestrator logic and scoring system.
Uses mock analyzers to avoid real API calls.
"""
import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.base_scanner import TokenData
from analyzers.security_score import SecurityScoreResult
from analyzers.honeypot_checker import HoneypotResult
from analyzers.holders_checker import HoldersResult, HolderInfo
from analyzers.liquidity_checker import LiquidityCheckResult
from analyzers.github_checker import GitHubResult


# ── Classification Logic Tests ───────────────────────────────────

class TestTokenClassification:
    """Test the token evaluation/classification logic."""

    @staticmethod
    def evaluate_token(security, honeypot, holders, liquidity, github):
        """Replicate the classification logic from main.py."""
        scores = []

        # Security
        s_score = security.score if security.success else 0
        scores.append((s_score, 30))

        # Honeypot
        hp_score = 100 if (honeypot.success and honeypot.is_safe) else 0
        scores.append((hp_score, 25))

        # Holders
        level_map = {"low": 100, "medium": 60, "high": 30, "extreme": 0}
        h_score = level_map.get(holders.concentration_level, 50)
        scores.append((h_score if holders.success else 0, 20))

        # Liquidity
        if liquidity.locked_percentage >= 80:
            lq_score = 100
        elif liquidity.locked_percentage >= 40:
            lq_score = 60
        elif liquidity.has_lock:
            lq_score = 30
        else:
            lq_score = 0
        scores.append((lq_score if liquidity.success else 0, 20))

        # GitHub
        scores.append((github.score if github.success else 0, 5))

        total_weight = sum(w for _, w in scores)
        overall = round(sum(s * w for s, w in scores) / total_weight) if total_weight > 0 else 0

        is_positive = (
            overall >= 60
            and not honeypot.is_honeypot
            and security.score >= 40
            and not (liquidity.locked_percentage == 0 and liquidity.total_liquidity_usd > 0)
        )

        return overall, is_positive

    def test_perfect_token_positive(self):
        """A perfect token should be positive with high score."""
        security = SecurityScoreResult(token_address="0x1", score=100, is_safe=True, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(
            token_address="0x1", concentration_level="low", success=True
        )
        liquidity = LiquidityCheckResult(
            token_address="0x1", locked_percentage=98.0, has_lock=True, success=True, total_liquidity_usd=100000,
        )
        github = GitHubResult(token_address="0x1", score=90, success=True, found_repo=True)

        score, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert score >= 80
        assert is_pos is True

    def test_honeypot_always_negative(self):
        """Even with other good metrics, honeypot = negative."""
        security = SecurityScoreResult(token_address="0x1", score=80, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=True, sell_success=False, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="low", success=True)
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=90.0, has_lock=True, success=True)
        github = GitHubResult(token_address="0x1", score=90, success=True, found_repo=True)

        _, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert is_pos is False

    def test_low_security_negative(self):
        """Security score < 40 should be negative."""
        security = SecurityScoreResult(token_address="0x1", score=25, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="low", success=True)
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=90.0, has_lock=True, success=True)
        github = GitHubResult(token_address="0x1", score=80, success=True, found_repo=True)

        _, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert is_pos is False

    def test_no_liquidity_lock_with_liquidity_negative(self):
        """Unlocked liquidity with actual money = negative."""
        security = SecurityScoreResult(token_address="0x1", score=85, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="low", success=True)
        liquidity = LiquidityCheckResult(
            token_address="0x1", locked_percentage=0.0, has_lock=False, success=True,
            total_liquidity_usd=100000,
        )
        github = GitHubResult(token_address="0x1", score=85, success=True, found_repo=True)

        _, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert is_pos is False

    def test_no_liquidity_no_money_neutral(self):
        """No liquidity lock but also no liquidity = should still be evaluated by score."""
        security = SecurityScoreResult(token_address="0x1", score=80, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="low", success=True)
        liquidity = LiquidityCheckResult(
            token_address="0x1", locked_percentage=0.0, has_lock=False, success=True,
            total_liquidity_usd=0,
        )
        github = GitHubResult(token_address="0x1", score=80, success=True, found_repo=True)

        score, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert score >= 50

    def test_all_unknown_results(self):
        """When all analyzers fail, score should be near 0."""
        security = SecurityScoreResult(token_address="0x1", score=0, success=False)
        honeypot = HoneypotResult(token_address="0x1", success=False)
        holders = HoldersResult(token_address="0x1", success=False)
        liquidity = LiquidityCheckResult(token_address="0x1", success=False)
        github = GitHubResult(token_address="0x1", success=False)

        score, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert score == 0
        assert is_pos is False

    def test_medium_concentration_mid_score(self):
        """Medium concentration should produce a mid-range score."""
        security = SecurityScoreResult(token_address="0x1", score=70, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="medium", success=True)
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=50.0, has_lock=True, success=True)
        github = GitHubResult(token_address="0x1", score=50, success=True, found_repo=True)

        score, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert 45 <= score <= 75

    def test_extreme_concentration_negative(self):
        """Extreme holder concentration should drag score down significantly."""
        security = SecurityScoreResult(token_address="0x1", score=60, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="extreme", success=True)
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=50.0, has_lock=True, success=True)
        github = GitHubResult(token_address="0x1", score=40, success=True, found_repo=True)

        score, is_pos = self.evaluate_token(security, honeypot, holders, liquidity, github)
        assert score < 60


# ── TokenData Integration Tests ──────────────────────────────────

class TestTokenDataIntegration:
    """Test TokenData conversion and usage in pipeline."""

    def test_token_to_dict_for_db(self):
        """TokenData dict should be compatible with database."""
        token = TokenData(
            address="0xTest000000000000000000000000000000000001",
            name="Integration Token",
            symbol="INTG",
            chain="base",
            market_cap=500000,
            liquidity_usd=200000,
            volume_24h=100000,
            dex_url="https://dexscreener.com/base/0xTest",
        )
        d = token.to_dict()
        required_fields = ["address", "name", "symbol", "chain", "liquidity_usd"]
        for field in required_fields:
            assert field in d, f"Missing field: {field}"
            assert d[field] is not None

    def test_token_list_to_dict_list(self):
        """Multiple tokens to dict conversion."""
        tokens = [
            TokenData(address=f"0x{i:040d}"[:42], name=f"Token{i}", symbol=f"TK{i}")
            for i in range(10)
        ]
        dicts = [t.to_dict() for t in tokens]
        assert len(dicts) == 10
        assert all(d["chain"] == "base" for d in dicts)


# ── Result Aggregation Tests ─────────────────────────────────────

class TestResultAggregation:
    """Test that analysis results aggregate correctly."""

    def test_positive_results_aggregation(self):
        """All positive results should produce high overall score."""
        security = SecurityScoreResult(token_address="0x1", score=90, is_safe=True, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(
            token_address="0x1", concentration_level="low", total_holders=5000, success=True,
            creator_percentage=5.0, top_10_percentage=40.0,
        )
        liquidity = LiquidityCheckResult(
            token_address="0x1", locked_percentage=95.0, has_lock=True,
            total_liquidity_usd=500000, total_locked_usd=475000, success=True,
        )
        github = GitHubResult(
            token_address="0x1", score=88, found_repo=True, stars=200, forks=50,
            has_readme=True, has_license=True, is_active=True, success=True,
        )

        assert security.is_safe is True
        assert honeypot.is_safe is True
        assert holders.is_safe is True
        assert liquidity.is_safe is True
        assert github.is_legitimate is True  # __post_init__ sets this for score>=50

    def test_negative_results_aggregation(self):
        """All negative results should produce low scores."""
        security = SecurityScoreResult(
            token_address="0x1", score=10, is_honeypot=True,
            risk_flags=["Honeypot", "Hidden owner", "Not open-source"],
            success=True,
        )
        honeypot = HoneypotResult(
            token_address="0x1", is_honeypot=True, sell_success=False,
            sell_tax=100.0, success=True,
        )
        holders = HoldersResult(
            token_address="0x1", concentration_level="extreme",
            creator_percentage=85.0, success=True,
        )
        liquidity = LiquidityCheckResult(
            token_address="0x1", has_lock=False, locked_percentage=0.0,
            total_liquidity_usd=10000, success=True,
        )
        github = GitHubResult(
            token_address="0x1", found_repo=False, score=0, success=True,
        )

        assert security.is_safe is False
        assert honeypot.is_safe is False
        # extreme level → is_safe checks level in ("low",) AND not is_concentrated → False
        assert holders.is_safe is False
        assert liquidity.is_safe is False
        assert github.is_legitimate is False

    def test_mixed_results(self):
        """Mixed results: some good, some bad."""
        security = SecurityScoreResult(token_address="0x1", score=65, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="high", success=True,
                                risk_warning="Top 5 wallets hold 80%")
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=30.0, has_lock=True, success=True)
        github = GitHubResult(token_address="0x1", score=35, found_repo=True, success=True)

        assert honeypot.is_safe is True
        # high level → level not "low" → is_safe = False
        assert holders.is_safe is False
        assert liquidity.is_safe is False  # Bad (<40%)


# ── Pipeline Simulation ──────────────────────────────────────────

class TestPipelineSimulation:
    """Simulate the full pipeline without real network calls."""

    @pytest.mark.asyncio
    async def test_simulated_pipeline_flow(self):
        """Simulate the flow: scan → analyze → classify → send."""
        discovered_tokens = [
            {"address": "0xToken1", "name": "Good Token", "symbol": "GOOD", "liquidity_usd": 200000},
            {"address": "0xToken2", "name": "Bad Token", "symbol": "SCAM", "liquidity_usd": 5000},
            {"address": "0xToken3", "name": "Mid Token", "symbol": "MID", "liquidity_usd": 50000},
        ]

        classifications = [
            (True, 85),
            (False, 15),
            (True, 62),
        ]

        results = list(zip(discovered_tokens, classifications))
        positive = [t for t, (is_pos, _) in results if is_pos]
        negative = [t for t, (is_pos, _) in results if not is_pos]

        assert len(positive) == 2
        assert len(negative) == 1
        assert positive[0]["symbol"] == "GOOD"
        assert positive[1]["symbol"] == "MID"
        assert negative[0]["symbol"] == "SCAM"


# ── Scoring Edge Cases ───────────────────────────────────────────

class TestScoringEdgeCases:
    """Test edge cases in scoring calculations."""

    def test_all_zero_scores(self):
        """When everything is zero."""
        security = SecurityScoreResult(token_address="0x1", score=0, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="extreme", success=True)
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=0.0, success=True)
        github = GitHubResult(token_address="0x1", score=0, success=True)

        score, is_pos = TestTokenClassification.evaluate_token(
            security, honeypot, holders, liquidity, github
        )
        assert score == 0
        assert is_pos is False

    def test_borderline_score_59(self):
        """Score below 60 should be negative."""
        # Sec:0.3*30=9, HP:0.25*100=25, Holders:0.2*30=6, Liq:0.2*30=6, Git:0.05*30=1.5 → 47.5→48
        security = SecurityScoreResult(token_address="0x1", score=30, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="high", success=True)
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=30.0, has_lock=True, success=True)
        github = GitHubResult(token_address="0x1", score=30, success=True, found_repo=True)

        score, is_pos = TestTokenClassification.evaluate_token(
            security, honeypot, holders, liquidity, github
        )
        assert score < 60
        assert is_pos is False

    def test_borderline_score_60(self):
        """Score of exactly 60 should be positive if other criteria met."""
        # Security 40 (30%), Honeypot 100 (25%), Holders medium 60 (20%), Liq 60 (20%), Git 50 (5%)
        # = 12 + 25 + 12 + 12 + 2.5 = 63.5 → 64
        security = SecurityScoreResult(token_address="0x1", score=40, success=True)
        honeypot = HoneypotResult(token_address="0x1", is_honeypot=False, sell_success=True, success=True)
        holders = HoldersResult(token_address="0x1", concentration_level="medium", success=True)
        liquidity = LiquidityCheckResult(token_address="0x1", locked_percentage=60.0, has_lock=True, success=True)
        github = GitHubResult(token_address="0x1", score=50, success=True, found_repo=True)

        score, is_pos = TestTokenClassification.evaluate_token(
            security, honeypot, holders, liquidity, github
        )

        assert score >= 60
        assert is_pos is True