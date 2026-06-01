"""
Tests for the Charts Module
===========================
Tests chart generation functions — verifying valid PNG output
for all chart types: gauge, honeypot, holders pie, liquidity, summary.
"""
import pytest
import io

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charts.chart_generator import ChartGenerator, ChartResult, create_chart_generator


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def chart_gen():
    """Create a chart generator instance for testing."""
    return ChartGenerator(style="dark", dpi=60)  # Lower DPI for faster tests


@pytest.fixture
def sample_holders_data():
    return [
        {"address": "0xDeve1oper0000000000000000000000000000001", "percentage": 15.0, "label": "Dev Wallet"},
        {"address": "0xLiquidity000000000000000000000000000000002", "percentage": 30.0, "label": "LP Pool"},
        {"address": "0xWhale10000000000000000000000000000000003", "percentage": 8.0, "label": "Whale"},
        {"address": "0xWhale20000000000000000000000000000000004", "percentage": 5.0, "label": "Whale"},
        {"address": "0xWhale30000000000000000000000000000000005", "percentage": 4.0, "label": "Whale"},
    ]


# ── Chart Generator Creation ─────────────────────────────────────

class TestChartGeneratorCreation:
    """Test chart generator initialization."""

    def test_create_default(self):
        gen = ChartGenerator()
        assert gen.style == "dark"
        assert gen.dpi == 120

    def test_create_light_style(self):
        gen = ChartGenerator(style="light", dpi=72)
        assert gen.style == "light"
        assert gen.dpi == 72

    def test_factory_function(self):
        gen = create_chart_generator("dark")
        assert isinstance(gen, ChartGenerator)
        assert gen.style == "dark"


# ── Security Gauge Tests ─────────────────────────────────────────

class TestSecurityGauge:
    """Test security score gauge generation."""

    def test_gauge_high_score(self, chart_gen):
        """Generate a gauge with high (safe) score."""
        result = chart_gen.generate_security_gauge(
            score=95,
            token_name="SafeToken",
            risk_flags=[],
        )
        assert isinstance(result, ChartResult)
        assert result.chart_type == "security_gauge"
        assert len(result.image_bytes) > 0
        assert result.image_bytes[:4] == b"\x89PNG"  # PNG magic bytes

    def test_gauge_low_score_with_flags(self, chart_gen):
        """Generate a gauge with low (danger) score and risk flags."""
        result = chart_gen.generate_security_gauge(
            score=15,
            token_name="ScamToken",
            risk_flags=["Honeypot detected", "Hidden owner", "Not open-source"],
        )
        assert len(result.image_bytes) > 0
        assert result.chart_type == "security_gauge"

    def test_gauge_medium_score(self, chart_gen):
        """Generate a gauge with medium (caution) score."""
        result = chart_gen.generate_security_gauge(
            score=55,
            token_name="MidToken",
            risk_flags=["High buy tax: 15%"],
        )
        assert len(result.image_bytes) > 1000  # Should be a decent size

    def test_gauge_no_token_name(self, chart_gen):
        """Generate a gauge without token name."""
        result = chart_gen.generate_security_gauge(score=80)
        assert len(result.image_bytes) > 0

    def test_gauge_zero_score(self, chart_gen):
        """Generate gauge with 0 score."""
        result = chart_gen.generate_security_gauge(
            score=0, risk_flags=["Honeypot", "Hidden owner", "No lock"]
        )
        assert len(result.image_bytes) > 0


# ── Honeypot Badge Tests ─────────────────────────────────────────

class TestHoneypotBadge:
    """Test honeypot badge generation."""

    def test_safe_badge(self, chart_gen):
        """Generate a green SAFE badge."""
        result = chart_gen.generate_honeypot_badge(
            is_honeypot=False,
            token_name="SafeToken",
            buy_tax=0.5,
            sell_tax=1.0,
            summary="Does not seem to be a honeypot.",
        )
        assert result.chart_type == "honeypot_badge"
        assert len(result.image_bytes) > 0

    def test_honeypot_badge(self, chart_gen):
        """Generate a red HONEYPOT badge."""
        result = chart_gen.generate_honeypot_badge(
            is_honeypot=True,
            token_name="ScamToken",
            buy_tax=0.0,
            sell_tax=100.0,
            summary="Honeypot detected! Cannot sell.",
        )
        assert len(result.image_bytes) > 0

    def test_badge_without_name(self, chart_gen):
        """Generate badge without token name."""
        result = chart_gen.generate_honeypot_badge(is_honeypot=False)
        assert len(result.image_bytes) > 0


# ── Holders Pie Chart Tests ──────────────────────────────────────

class TestHoldersPie:
    """Test holders pie chart generation."""

    def test_pie_with_data(self, chart_gen, sample_holders_data):
        """Generate pie chart with holder data."""
        result = chart_gen.generate_holders_pie(
            holders_data=sample_holders_data,
            token_name="MyToken",
            total_holders=5000,
            concentration_level="low",
            risk_warning="",
        )
        assert result.chart_type == "holders_pie"
        assert len(result.image_bytes) > 0

    def test_pie_high_concentration(self, chart_gen):
        """Pie chart with extreme concentration."""
        data = [{"address": "0xDev...", "percentage": 85.0, "label": "Dev"}]
        result = chart_gen.generate_holders_pie(
            holders_data=data,
            token_name="RiskyToken",
            total_holders=5,
            concentration_level="extreme",
            risk_warning="One wallet holds 85%!",
        )
        assert len(result.image_bytes) > 0

    def test_pie_empty_data(self, chart_gen):
        """Pie chart with no data (fallback)."""
        result = chart_gen.generate_holders_pie(holders_data=[], token_name="Unknown")
        assert len(result.image_bytes) > 0

    def test_pie_medium_concentration(self, chart_gen):
        """Pie with medium concentration."""
        data = [
            {"address": "0xDev...", "percentage": 30.0, "label": "Dev"},
            {"address": "0xWhale1...", "percentage": 20.0, "label": "Whale"},
            {"address": "0xWhale2...", "percentage": 15.0, "label": "Whale"},
        ]
        result = chart_gen.generate_holders_pie(
            holders_data=data,
            total_holders=100,
            concentration_level="medium",
            risk_warning="Monitor concentration",
        )
        assert len(result.image_bytes) > 0


# ── Liquidity Chart Tests ────────────────────────────────────────

class TestLiquidityChart:
    """Test liquidity lock chart generation."""

    def test_locked_chart(self, chart_gen):
        """Generate liquidity chart with locks."""
        locks = [
            {"locker": "UNCX", "days_remaining": 730, "amount_usd": 100000, "is_expired": False},
            {"locker": "TeamFinance", "days_remaining": 180, "amount_usd": 47000, "is_expired": False},
        ]
        result = chart_gen.generate_liquidity_chart(
            token_name="SafeToken",
            locked_percentage=98.0,
            total_liquidity_usd=150000,
            total_locked_usd=147000,
            locks=locks,
            risk_warning="",
        )
        assert result.chart_type == "liquidity_chart"
        assert len(result.image_bytes) > 0

    def test_no_lock_chart(self, chart_gen):
        """Generate liquidity chart with no locks."""
        result = chart_gen.generate_liquidity_chart(
            token_name="RiskyToken",
            locked_percentage=0.0,
            total_liquidity_usd=5000,
            total_locked_usd=0,
            locks=[],
            risk_warning="Liquidity is NOT locked!",
        )
        assert len(result.image_bytes) > 0

    def test_expired_lock(self, chart_gen):
        """Chart with an expired lock."""
        locks = [
            {"locker": "UNCX", "days_remaining": 0, "amount_usd": 10000, "is_expired": True},
        ]
        result = chart_gen.generate_liquidity_chart(
            token_name="ExpiredToken",
            locked_percentage=10.0,
            locks=locks,
        )
        assert len(result.image_bytes) > 0

    def test_partial_lock(self, chart_gen):
        """Chart with partial (50%) lock."""
        result = chart_gen.generate_liquidity_chart(
            token_name="PartialToken",
            locked_percentage=50.0,
            total_liquidity_usd=100000,
            total_locked_usd=50000,
            locks=[{"locker": "UNCX", "days_remaining": 365, "amount_usd": 50000}],
        )
        assert len(result.image_bytes) > 0


# ── Summary Card Tests ───────────────────────────────────────────

class TestSummaryCard:
    """Test the combined summary card."""

    def test_summary_card(self, chart_gen):
        """Generate a 2x2 summary card."""
        result = chart_gen.generate_summary_card(
            token_name="TestToken",
            token_symbol="TEST",
            security_score=85,
            is_honeypot=False,
            concentration_level="low",
            locked_percentage=98.0,
        )
        assert result.chart_type == "summary_card"
        assert len(result.image_bytes) > 0

    def test_summary_card_danger(self, chart_gen):
        """Summary with all bad metrics."""
        result = chart_gen.generate_summary_card(
            token_name="ScamToken",
            token_symbol="SCAM",
            security_score=10,
            is_honeypot=True,
            concentration_level="extreme",
            locked_percentage=0.0,
        )
        assert len(result.image_bytes) > 0


# ── ChartResult Tests ────────────────────────────────────────────

class TestChartResult:
    """Test ChartResult dataclass."""

    def test_save(self, tmp_path, chart_gen):
        """Test saving chart to file."""
        result = chart_gen.generate_security_gauge(score=80)
        path = tmp_path / "test_chart.png"
        result.save(str(path))
        assert path.exists()
        assert path.stat().st_size > 0

    def test_buffer(self, chart_gen):
        """Test buffer returns valid BytesIO."""
        result = chart_gen.generate_security_gauge(score=50)
        buf = result.buffer
        assert isinstance(buf, io.BytesIO)
        # Should be seekable and readable
        data = buf.read()
        assert len(data) == len(result.image_bytes)

    def test_format(self, chart_gen):
        """Test format attribute."""
        result = chart_gen.generate_security_gauge(score=80)
        assert result.format == "png"


# ── Edge Cases ───────────────────────────────────────────────────

class TestChartEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_score_100(self, chart_gen):
        """Perfect score gauge."""
        result = chart_gen.generate_security_gauge(score=100, risk_flags=[])
        assert len(result.image_bytes) > 0

    def test_empty_risk_flags_none(self, chart_gen):
        """None risk_flags should work."""
        result = chart_gen.generate_security_gauge(score=80, risk_flags=None)
        assert len(result.image_bytes) > 0

    def test_many_risk_flags(self, chart_gen):
        """Many risk flags should not crash."""
        flags = [f"Risk flag {i}" for i in range(20)]
        result = chart_gen.generate_security_gauge(score=30, risk_flags=flags)
        assert len(result.image_bytes) > 0

    def test_zero_liquidity(self, chart_gen):
        """Zero liquidity values."""
        result = chart_gen.generate_liquidity_chart(
            locked_percentage=0.0,
            total_liquidity_usd=0,
        )
        assert len(result.image_bytes) > 0

    def test_large_holders(self, chart_gen):
        """Large number of holders (should truncate in legend)."""
        data = [
            {"address": f"0xAddr{i:040d}"[:42], "percentage": 100.0 / 20, "label": f"H{i}"}
            for i in range(20)
        ]
        result = chart_gen.generate_holders_pie(holders_data=data)
        assert len(result.image_bytes) > 0