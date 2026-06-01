"""
Chart Generator Module
======================
Generates visual charts for the Telegram bot:
- Security Score Gauge (donut/gauge chart)
- Honeypot Badge (green/red indicator)
- Top Holders Pie Chart
- Liquidity Lock Timeline
"""
import io
import math
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

logger = logging.getLogger(__name__)

# Color scheme
COLOR_GREEN = "#22c55e"
COLOR_RED = "#ef4444"
COLOR_AMBER = "#f59e0b"
COLOR_BLUE = "#3b82f6"
COLOR_PURPLE = "#8b5cf6"
COLOR_GRAY = "#9ca3af"
COLOR_DARK_BG = "#1a1a2e"
COLOR_CARD_BG = "#16213e"
COLOR_TEXT = "#e2e8f0"
COLOR_TEXT_SECONDARY = "#94a3b8"

# A dark, modern color palette for pie charts
PIE_COLORS = [
    "#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
    "#06b6d4", "#ec4899", "#f97316", "#14b8a6", "#6366f1",
    "#84cc16", "#d946ef", "#0ea5e9", "#e11d48", "#10b981",
]

STYLE_DARK = {
    "figure.facecolor": COLOR_DARK_BG,
    "axes.facecolor": COLOR_CARD_BG,
    "axes.edgecolor": COLOR_TEXT_SECONDARY,
    "axes.labelcolor": COLOR_TEXT,
    "text.color": COLOR_TEXT,
    "xtick.color": COLOR_TEXT_SECONDARY,
    "ytick.color": COLOR_TEXT_SECONDARY,
    "grid.color": "#2d2d4a",
    "grid.alpha": 0.3,
}


@dataclass
class ChartResult:
    """Holds the bytes of a generated chart image."""
    image_bytes: bytes
    chart_type: str
    title: str
    format: str = "png"

    def save(self, filepath: str) -> None:
        with open(filepath, "wb") as f:
            f.write(self.image_bytes)

    @property
    def buffer(self) -> io.BytesIO:
        buf = io.BytesIO(self.image_bytes)
        buf.seek(0)
        return buf


class ChartGenerator:
    """Main chart generator for the bot."""

    def __init__(self, style: str = "dark", dpi: int = 120):
        self.style = style
        self.dpi = dpi
        if style == "dark":
            plt.style.use(STYLE_DARK)
        else:
            plt.style.use("default")

    # ── Security Score Gauge ──────────────────────────────────────

    def generate_security_gauge(
        self, score: int, token_name: str = "", risk_flags: List[str] = None
    ) -> ChartResult:
        """
        Generate a gauge/donut chart showing the security score (0-100).
        Green = 80+, Amber = 50-79, Red = <50.
        """
        risk_flags = risk_flags or []
        fig, (ax_gauge, ax_flags) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [1, 1.5]})
        fig.patch.set_facecolor(COLOR_DARK_BG)

        # Determine color
        if score >= 80:
            color = COLOR_GREEN
            label = "SAFE"
        elif score >= 50:
            color = COLOR_AMBER
            label = "CAUTION"
        else:
            color = COLOR_RED
            label = "DANGER"

        # Gauge (donut chart)
        sizes = [score, max(0, 100 - score)]
        wedges, texts = ax_gauge.pie(
            sizes,
            colors=[color, "#2d2d4a"],
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.3, "edgecolor": "none"},
        )

        # Center text
        ax_gauge.text(
            0, 0, f"{score}/100",
            ha="center", va="center",
            fontsize=26, fontweight="bold",
            color=color,
        )
        ax_gauge.text(
            0, -0.3, label,
            ha="center", va="center",
            fontsize=13, fontweight="bold",
            color=color,
        )

        title = f"🔐 Security Score: {token_name}" if token_name else "🔐 Security Score"
        ax_gauge.set_title(title, fontsize=13, color=COLOR_TEXT, pad=15)

        # Flags panel
        ax_flags.set_xlim(0, 10)
        ax_flags.set_ylim(-1, max(1, len(risk_flags) + 1))
        ax_flags.axis("off")
        ax_flags.set_facecolor(COLOR_CARD_BG)

        if risk_flags:
            ax_flags.text(5, len(risk_flags) + 0.5, "Risk Flags:", fontsize=12,
                          ha="center", color=COLOR_RED, fontweight="bold")
            for i, flag in enumerate(risk_flags):
                y = len(risk_flags) - i
                ax_flags.text(0.3, y, f"⚠ {flag}", fontsize=10, color=COLOR_RED, va="center")
        else:
            ax_flags.text(5, 1, "✅ No flags triggered", fontsize=13,
                          ha="center", color=COLOR_GREEN, fontweight="bold")
            ax_flags.text(5, 0, "All security checks passed", fontsize=10,
                          ha="center", color=COLOR_TEXT_SECONDARY)

        plt.tight_layout(pad=2)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight",
                    facecolor=COLOR_DARK_BG, edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        return ChartResult(image_bytes=buf.read(), chart_type="security_gauge",
                           title=f"Security Score: {token_name}")

    # ── Honeypot Badge ────────────────────────────────────────────

    def generate_honeypot_badge(
        self, is_honeypot: bool, token_name: str = "", buy_tax: float = 0.0,
        sell_tax: float = 0.0, summary: str = ""
    ) -> ChartResult:
        """
        Generate a large badge/indicator showing honeypot result.
        Green box = SAFE, Red box = HONEYPOT.
        """
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor(COLOR_DARK_BG)
        ax.set_facecolor(COLOR_DARK_BG)

        if is_honeypot:
            box_color = COLOR_RED
            bg_color = "#3b0a0a"
            icon = "🚨"
            title_text = "HONEYPOT DETECTED!"
            subtitle = "Run away! This token cannot be sold."
        else:
            box_color = COLOR_GREEN
            bg_color = "#0a2e0a"
            icon = "✅"
            title_text = "SAFE"
            subtitle = "Does not seem to be a honeypot."

        # Background box
        rect = mpatches.FancyBboxPatch(
            (0.1, 0.2), 0.8, 0.6,
            boxstyle="round,pad=0.1",
            facecolor=bg_color,
            edgecolor=box_color,
            linewidth=3,
            transform=ax.transAxes,
        )
        ax.add_patch(rect)

        # Icon
        ax.text(0.5, 0.72, icon, fontsize=50, ha="center", va="center",
                transform=ax.transAxes)

        # Title
        ax.text(0.5, 0.55, title_text, fontsize=22, ha="center", va="center",
                fontweight="bold", color=box_color, transform=ax.transAxes)

        # Subtitle
        ax.text(0.5, 0.38, subtitle, fontsize=11, ha="center", va="center",
                color=COLOR_TEXT_SECONDARY, transform=ax.transAxes)

        # Tax info
        tax_text = f"Buy Tax: {buy_tax:.1f}%  |  Sell Tax: {sell_tax:.1f}%"
        ax.text(0.5, 0.25, tax_text, fontsize=9, ha="center", va="center",
                color=COLOR_TEXT_SECONDARY, transform=ax.transAxes)

        # Footer summary
        if summary:
            ax.text(0.5, 0.1, summary, fontsize=8, ha="center", va="center",
                    color=COLOR_TEXT_SECONDARY, style="italic", transform=ax.transAxes)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        chart_title = f"🍯 Honeypot Check: {token_name}" if token_name else "🍯 Honeypot Check"
        ax.set_title(chart_title, fontsize=14, color=COLOR_TEXT, pad=15, fontweight="bold")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight",
                    facecolor=COLOR_DARK_BG, edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        return ChartResult(image_bytes=buf.read(), chart_type="honeypot_badge",
                           title=f"Honeypot: {token_name}")

    # ── Top Holders Pie Chart ─────────────────────────────────────

    def generate_holders_pie(
        self, holders_data: List[Dict], token_name: str = "",
        total_holders: int = 0, concentration_level: str = "unknown",
        risk_warning: str = ""
    ) -> ChartResult:
        """
        Generate a pie chart showing token holder distribution.
        """
        if not holders_data:
            holders_data = [{"address": "No data", "percentage": 100, "label": "Unknown"}]

        fig, (ax_pie, ax_info) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1.2, 1]})
        fig.patch.set_facecolor(COLOR_DARK_BG)

        # Prepare data
        labels = [f"{h['address'][:12]}..." if len(h.get("address", "")) > 12 else h["address"]
                  for h in holders_data]
        sizes = [h["percentage"] for h in holders_data]
        colors = PIE_COLORS[: len(sizes)]

        # Pie chart
        wedges, texts, autotexts = ax_pie.pie(
            sizes,
            labels=None,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            pctdistance=0.78,
            wedgeprops={"edgecolor": COLOR_DARK_BG, "linewidth": 1.5},
        )

        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color("white")

        # Legend
        legend_labels = [
            f"{h.get('label', h['address'][:10])} ({h['percentage']:.1f}%)"
            for h in holders_data[:8]
        ]
        ax_pie.legend(
            wedges[:8], legend_labels,
            title="Top Holders",
            loc="lower center",
            bbox_to_anchor=(0.5, -0.25),
            ncol=2,
            fontsize=7,
            title_fontsize=8,
        )

        title = f"👥 Holders: {token_name}" if token_name else "👥 Token Holders"
        ax_pie.set_title(title, fontsize=13, color=COLOR_TEXT, pad=15)

        # Info panel
        ax_info.set_facecolor(COLOR_CARD_BG)
        ax_info.axis("off")

        # Concentration indicator
        level_colors = {
            "low": COLOR_GREEN, "medium": COLOR_AMBER,
            "high": COLOR_RED, "extreme": COLOR_RED, "unknown": COLOR_GRAY,
        }
        lc = level_colors.get(concentration_level, COLOR_GRAY)

        y = 4.5
        ax_info.text(0.5, y, f"Total Holders: {total_holders}", fontsize=12,
                     ha="center", color=COLOR_TEXT, fontweight="bold")

        y -= 0.8
        ax_info.text(0.5, y, "Distribution:", fontsize=10,
                     ha="center", color=COLOR_TEXT_SECONDARY)

        y -= 0.6
        level_text = concentration_level.upper() if concentration_level != "unknown" else "UNKNOWN"
        ax_info.text(0.5, y, level_text, fontsize=16, ha="center",
                     color=lc, fontweight="bold")

        if risk_warning:
            y -= 0.7
            ax_info.text(0.5, y, risk_warning, fontsize=8, ha="center",
                         color=COLOR_RED, style="italic",
                         bbox={"facecolor": "#3b0a0a", "alpha": 0.5, "pad": 5, "boxstyle": "round"})

        # Show top holders breakdown
        y -= 1.0
        for i, h in enumerate(holders_data[:5]):
            y -= 0.45
            addr = h.get("address", "?")[:14]
            ax_info.text(0.1, y, f"#{i+1}  {addr}", fontsize=8, color=COLOR_TEXT)
            ax_info.text(0.9, y, f"{h['percentage']:.1f}%", fontsize=8,
                         color=COLOR_TEXT, ha="right")

        ax_info.set_xlim(0, 1)
        ax_info.set_ylim(0, 5)

        plt.tight_layout(pad=2)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight",
                    facecolor=COLOR_DARK_BG, edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        return ChartResult(image_bytes=buf.read(), chart_type="holders_pie",
                           title=f"Holders: {token_name}")

    # ── Liquidity Lock Timeline ───────────────────────────────────

    def generate_liquidity_chart(
        self, token_name: str = "", locked_percentage: float = 0.0,
        total_liquidity_usd: float = 0.0, total_locked_usd: float = 0.0,
        locks: List[Dict] = None, risk_warning: str = ""
    ) -> ChartResult:
        """
        Generate a liquidity lock visualization:
        - Horizontal bar showing % locked
        - Timeline of lock expirations
        """
        locks = locks or []
        fig, (ax_bar, ax_timeline) = plt.subplots(2, 1, figsize=(9, 6),
                                                   gridspec_kw={"height_ratios": [1, 1.5]})
        fig.patch.set_facecolor(COLOR_DARK_BG)

        # ── Lock percentage bar ──
        locked_pct = min(100, max(0, locked_percentage))
        unlocked_pct = 100 - locked_pct

        if locked_pct >= 80:
            lock_color = COLOR_GREEN
        elif locked_pct >= 40:
            lock_color = COLOR_AMBER
        else:
            lock_color = COLOR_RED

        # Horizontal stacked bar
        ax_bar.barh(0, locked_pct, color=lock_color, height=0.5, label="Locked")
        ax_bar.barh(0, unlocked_pct, color="#2d2d4a", height=0.5, left=locked_pct, label="Unlocked")
        ax_bar.set_xlim(0, 100)
        ax_bar.set_ylim(-0.5, 0.8)
        ax_bar.axis("off")

        # Add lock icon and percentage
        emoji = "🔒" if locked_pct >= 40 else "🔓"
        ax_bar.text(locked_pct / 2, -0.1, f"{emoji} {locked_pct:.1f}% Locked",
                    fontsize=15, ha="center", va="center",
                    color="white", fontweight="bold")

        total_liq_str = f"${total_liquidity_usd:,.0f}" if total_liquidity_usd > 0 else "N/A"
        locked_str = f"${total_locked_usd:,.0f}" if total_locked_usd > 0 else "N/A"

        ax_bar.text(50, 0.5, f"Total: {total_liq_str}  |  Locked: {locked_str}",
                    fontsize=9, ha="center", color=COLOR_TEXT_SECONDARY)

        title = f"🔒 Liquidity Lock: {token_name}" if token_name else "🔒 Liquidity Lock"
        ax_bar.set_title(title, fontsize=13, color=COLOR_TEXT, pad=10)

        # ── Timeline ──
        ax_timeline.set_facecolor(COLOR_CARD_BG)

        if locks:
            locker_names = [l.get("locker", "Lock") for l in locks]
            days_remaining = [l.get("days_remaining", 0) for l in locks]
            amounts = [l.get("amount_usd", 0) for l in locks]
            is_expired = [l.get("is_expired", False) for l in locks]

            y_positions = list(range(len(locks)))
            bar_colors = [COLOR_RED if e else COLOR_GREEN for e in is_expired]

            bars = ax_timeline.barh(y_positions, days_remaining, color=bar_colors, height=0.5)
            ax_timeline.set_yticks(y_positions)
            ax_timeline.set_yticklabels(locker_names, fontsize=9)
            ax_timeline.set_xlabel("Days Remaining", color=COLOR_TEXT_SECONDARY, fontsize=9)
            ax_timeline.set_title("Lock Timeline", fontsize=11, color=COLOR_TEXT, pad=8)

            # Add day labels on bars
            for i, (bar, days, amt) in enumerate(zip(bars, days_remaining, amounts)):
                if days > 0:
                    amt_str = f"${amt:,.0f}" if amt > 0 else ""
                    ax_timeline.text(days + max(days_remaining) * 0.02, bar.get_y() + bar.get_height() / 2,
                                     f"{days}d  {amt_str}", fontsize=8, color=COLOR_TEXT, va="center")
        else:
            ax_timeline.text(0.5, 0.5, "No lock data available",
                             fontsize=12, ha="center", va="center",
                             color=COLOR_TEXT_SECONDARY, transform=ax_timeline.transAxes)
            ax_timeline.axis("off")

        # Risk warning
        if risk_warning:
            fig.text(0.5, 0.02, risk_warning, fontsize=8, ha="center",
                     color=COLOR_RED, style="italic")

        plt.tight_layout(pad=2)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight",
                    facecolor=COLOR_DARK_BG, edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        return ChartResult(image_bytes=buf.read(), chart_type="liquidity_chart",
                           title=f"Liquidity: {token_name}")

    # ── Combined Summary Card ─────────────────────────────────────

    def generate_summary_card(
        self, token_name: str, token_symbol: str,
        security_score: int = 0, is_honeypot: bool = False,
        concentration_level: str = "unknown", locked_percentage: float = 0.0,
    ) -> ChartResult:
        """
        Generate a single overview card with all 4 metrics in one compact image.
        """
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        fig.patch.set_facecolor(COLOR_DARK_BG)

        metrics = [
            ("🔐 Security Score", f"{security_score}/100",
             COLOR_GREEN if security_score >= 80 else COLOR_AMBER if security_score >= 50 else COLOR_RED),
            ("🍯 Honeypot", "SAFE ✅" if not is_honeypot else "DANGER 🚨",
             COLOR_GREEN if not is_honeypot else COLOR_RED),
            ("👥 Holders", concentration_level.upper(),
             {"low": COLOR_GREEN, "medium": COLOR_AMBER, "high": COLOR_RED, "extreme": COLOR_RED, "unknown": COLOR_GRAY}.get(concentration_level, COLOR_GRAY)),
            ("🔒 Liquidity", f"{locked_percentage:.0f}% Locked",
             COLOR_GREEN if locked_percentage >= 80 else COLOR_AMBER if locked_percentage >= 40 else COLOR_RED),
        ]

        for ax, (label, value, color) in zip(axes.flat, metrics):
            ax.set_facecolor(COLOR_CARD_BG)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            # Card border
            rect = mpatches.FancyBboxPatch(
                (0.05, 0.05), 0.9, 0.9,
                boxstyle="round,pad=0.05",
                facecolor=COLOR_CARD_BG,
                edgecolor=color,
                linewidth=2,
                transform=ax.transAxes,
            )
            ax.add_patch(rect)

            ax.text(0.5, 0.7, label, fontsize=12, ha="center", va="center",
                    color=COLOR_TEXT_SECONDARY, transform=ax.transAxes)
            ax.text(0.5, 0.35, value, fontsize=20, ha="center", va="center",
                    color=color, fontweight="bold", transform=ax.transAxes)

        fig.suptitle(f"{token_name} ({token_symbol})", fontsize=15,
                     color=COLOR_TEXT, fontweight="bold", y=0.98)

        plt.tight_layout(pad=2)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=self.dpi, bbox_inches="tight",
                    facecolor=COLOR_DARK_BG, edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        return ChartResult(image_bytes=buf.read(), chart_type="summary_card",
                           title=f"Summary: {token_name}")


# Factory function
def create_chart_generator(style: str = "dark") -> ChartGenerator:
    return ChartGenerator(style=style)