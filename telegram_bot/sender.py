"""
Telegram Bot Sender Module
===========================
Formats and sends token analysis results via Telegram.
Handles message composition, chart attachments, and
positive/negative token sorting.
"""
import asyncio
import io
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from telegram import Bot, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.error import TelegramError

from charts.chart_generator import ChartGenerator, ChartResult
from analyzers.security_score import SecurityScoreResult
from analyzers.honeypot_checker import HoneypotResult
from analyzers.holders_checker import HoldersResult
from analyzers.liquidity_checker import LiquidityCheckResult
from analyzers.github_checker import GitHubResult

logger = logging.getLogger(__name__)

# Emoji constants
EMOJI = {
    "green_circle": "🟢",
    "red_circle": "🔴",
    "yellow_circle": "🟡",
    "shield": "🛡️",
    "honey": "🍯",
    "people": "👥",
    "lock": "🔒",
    "github": "💻",
    "chart": "📊",
    "money": "💰",
    "warning": "⚠️",
    "check": "✅",
    "cross": "❌",
    "skull": "💀",
    "rocket": "🚀",
    "link": "🔗",
    "star": "⭐",
    "new": "🆕",
    "fire": "🔥",
}


class TelegramSender:
    """Sends formatted token analysis results via Telegram."""

    def __init__(self, bot_token: str, channel_id: str, chart_generator: Optional[ChartGenerator] = None):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.bot = Bot(token=bot_token)
        self.chart_gen = chart_generator or ChartGenerator(style="dark")

    async def send_positive_token(
        self,
        token_data: Dict,
        security_result: SecurityScoreResult,
        honeypot_result: HoneypotResult,
        holders_result: HoldersResult,
        liquidity_result: LiquidityCheckResult,
        github_result: GitHubResult,
        overall_score: int = 0,
    ) -> bool:
        """
        Send a comprehensive positive token report with all 4 chart images.
        """
        try:
            token_name = token_data.get("name", "Unknown")
            token_symbol = token_data.get("symbol", "UNKNOWN")
            token_address = token_data.get("address", "")
            dex_url = token_data.get("dex_url", f"https://dexscreener.com/base/{token_address}")
            liquidity_usd = token_data.get("liquidity_usd", 0)
            market_cap = token_data.get("market_cap", 0)

            # ── Generate all 4 charts ──
            charts: List[ChartResult] = []

            # 1. Security Score Gauge
            charts.append(self.chart_gen.generate_security_gauge(
                score=security_result.score,
                token_name=token_name,
                risk_flags=security_result.risk_flags,
            ))

            # 2. Honeypot Badge
            charts.append(self.chart_gen.generate_honeypot_badge(
                is_honeypot=honeypot_result.is_honeypot,
                token_name=token_name,
                buy_tax=honeypot_result.buy_tax,
                sell_tax=honeypot_result.sell_tax,
                summary=honeypot_result.summary,
            ))

            # 3. Holders Pie Chart
            charts.append(self.chart_gen.generate_holders_pie(
                holders_data=holders_result.chart_data,
                token_name=token_name,
                total_holders=holders_result.total_holders,
                concentration_level=holders_result.concentration_level,
                risk_warning=holders_result.risk_warning,
            ))

            # 4. Liquidity Lock Chart
            charts.append(self.chart_gen.generate_liquidity_chart(
                token_name=token_name,
                locked_percentage=liquidity_result.locked_percentage,
                total_liquidity_usd=liquidity_result.total_liquidity_usd,
                total_locked_usd=liquidity_result.total_locked_usd,
                locks=liquidity_result.unlock_timeline,
                risk_warning=liquidity_result.risk_warning,
            ))

            # ── Build message text ──
            message = self._build_positive_message(
                token_name=token_name,
                token_symbol=token_symbol,
                token_address=token_address,
                dex_url=dex_url,
                liquidity_usd=liquidity_usd,
                market_cap=market_cap,
                security_result=security_result,
                honeypot_result=honeypot_result,
                holders_result=holders_result,
                liquidity_result=liquidity_result,
                github_result=github_result,
                overall_score=overall_score,
            )

            # ── Send as media group (up to 4 images) with caption ──
            media_group = []
            for i, chart in enumerate(charts):
                buf = chart.buffer
                if i == 0:
                    # First image gets the caption
                    media_group.append(InputMediaPhoto(
                        media=buf,
                        caption=message,
                        parse_mode=ParseMode.HTML,
                    ))
                else:
                    media_group.append(InputMediaPhoto(media=buf))

            # Send in batches of 2 (Telegram limit for media group with caption considerations)
            await self.bot.send_media_group(
                chat_id=self.channel_id,
                media=media_group[:4],
            )

            logger.info(f"✅ Sent positive report for {token_symbol} to Telegram")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending positive report for {token_data.get('symbol')}: {e}")
            # Fallback: send text-only
            return await self._send_text_fallback(token_data, security_result, honeypot_result,
                                                   holders_result, liquidity_result, github_result)
        except Exception as e:
            logger.error(f"Error sending positive report: {e}")
            return False

    async def send_negative_token(
        self,
        token_data: Dict,
        security_result: SecurityScoreResult,
        honeypot_result: HoneypotResult,
        holders_result: HoldersResult,
        liquidity_result: LiquidityCheckResult,
        github_result: GitHubResult,
    ) -> bool:
        """
        Send a brief warning for a negative/suspicious token (text only, no charts).
        """
        try:
            token_name = token_data.get("name", "Unknown")
            token_symbol = token_data.get("symbol", "UNKNOWN")
            token_address = token_data.get("address", "")

            message = self._build_negative_message(
                token_name=token_name,
                token_symbol=token_symbol,
                token_address=token_address,
                security_result=security_result,
                honeypot_result=honeypot_result,
                holders_result=holders_result,
                liquidity_result=liquidity_result,
                github_result=github_result,
            )

            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

            logger.info(f"⚠ Sent negative report for {token_symbol} to Telegram")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending negative report: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending negative report: {e}")
            return False

    async def send_daily_summary(
        self, date_str: str, total_tokens: int, positive_count: int,
        negative_count: int, positive_tokens: List[Dict] = None,
    ) -> bool:
        """
        Send a daily summary message.
        """
        try:
            positive_tokens = positive_tokens or []
            message_parts = [
                f"{EMOJI['fire']} <b>Daily Base Chain Scan Summary</b> {EMOJI['fire']}",
                f"📅 <b>Date:</b> {date_str}",
                "",
                f"📊 <b>Total tokens scanned:</b> {total_tokens}",
                f"{EMOJI['green_circle']} <b>Positive (Safe):</b> {positive_count}",
                f"{EMOJI['red_circle']} <b>Negative (Scam/Risky):</b> {negative_count}",
                "",
            ]

            if positive_tokens:
                message_parts.append(f"{EMOJI['star']} <b>Today's Safe Tokens:</b>")
                for t in positive_tokens[:10]:
                    name = t.get("name", "Unknown")
                    symbol = t.get("symbol", "???")
                    address = t.get("address", "")
                    short_addr = f"{address[:6]}...{address[-4:]}" if len(address) > 12 else address
                    score = t.get("overall_score", "?")
                    message_parts.append(
                        f"  {EMOJI['check']} <b>{name}</b> (${symbol}) — "
                        f"Score: {score}/100 | <code>{short_addr}</code>"
                    )

                if len(positive_tokens) > 10:
                    message_parts.append(f"  ... and {len(positive_tokens) - 10} more")

                message_parts.append("")

            message_parts.append(f"🤖 <i>Base Bot v1.0 — Automated scans run daily</i>")

            message = "\n".join(message_parts)

            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

            logger.info(f"Sent daily summary for {date_str}")
            return True

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False

    async def send_text(self, text: str, parse_mode: str = ParseMode.HTML) -> bool:
        """Send a plain text message."""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending text: {e}")
            return False

    async def send_photo(self, photo_bytes: bytes, caption: str = "",
                         parse_mode: str = ParseMode.HTML) -> bool:
        """Send a single photo."""
        try:
            buf = io.BytesIO(photo_bytes)
            buf.seek(0)
            await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=buf,
                caption=caption,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False

    # ── Message Builders ──────────────────────────────────────────

    def _build_positive_message(
        self, token_name: str, token_symbol: str, token_address: str,
        dex_url: str, liquidity_usd: float, market_cap: float,
        security_result: SecurityScoreResult,
        honeypot_result: HoneypotResult,
        holders_result: HoldersResult,
        liquidity_result: LiquidityCheckResult,
        github_result: GitHubResult,
        overall_score: int,
    ) -> str:
        """Build formatted HTML message for a positive token."""

        liq_str = f"${liquidity_usd:,.0f}" if liquidity_usd > 0 else "N/A"
        mcap_str = f"${market_cap:,.0f}" if market_cap > 0 else "N/A"

        parts = [
            f"{EMOJI['rocket']} <b>{token_name} (${token_symbol})</b> {EMOJI['rocket']}",
            f"{EMOJI['green_circle']} <b>OVERALL SCORE: {overall_score}/100 — SAFE</b>",
            "",
            f"<code>{token_address}</code>",
            "",
            f"{EMOJI['money']} <b>Market Data:</b>",
            f"  💰 Liquidity: {liq_str}",
            f"  📈 Market Cap: {mcap_str}",
            "",
            f"{EMOJI['shield']} <b>1. Security Score:</b> {security_result.score}/100",
            f"  {EMOJI['check'] if security_result.is_safe else EMOJI['warning']} {security_result.summary}",
            f"  • Buy Tax: {security_result.buy_tax:.1f}% | Sell Tax: {security_result.sell_tax:.1f}%",
        ]

        if security_result.risk_flags:
            parts.append(f"  {EMOJI['warning']} Flags: {', '.join(security_result.risk_flags[:3])}")

        parts.extend([
            "",
            f"{EMOJI['honey']} <b>2. Honeypot Check:</b>",
            f"  {honeypot_result.status_text}",
            f"  • Buy Tax: {honeypot_result.buy_tax:.1f}% | Sell Tax: {honeypot_result.sell_tax:.1f}%",
            "",
            f"{EMOJI['people']} <b>3. Holder Distribution:</b>",
            f"  {holders_result.status_text}",
            f"  • Total Holders: {holders_result.total_holders}",
            f"  • Top Holder: {holders_result.creator_percentage:.1f}%",
            f"  • Top 10: {holders_result.top_10_percentage:.1f}%",
            "",
            f"{EMOJI['lock']} <b>4. Liquidity Lock:</b>",
            f"  {liquidity_result.status_text}",
            f"  • Total Liquidity: ${liquidity_result.total_liquidity_usd:,.0f}",
            f"  • Locked: {liquidity_result.locked_percentage:.1f}% (${liquidity_result.total_locked_usd:,.0f})",
        ])

        if liquidity_result.unlock_timeline:
            for lock_info in liquidity_result.unlock_timeline[:2]:
                parts.append(f"  • {lock_info['locker']}: {lock_info['days_remaining']}d remaining")

        parts.extend([
            "",
            f"{EMOJI['github']} <b>5. GitHub Repository:</b>",
            f"  {github_result.status_text}",
            f"  • Stars: {github_result.stars} | Forks: {github_result.forks}",
            f"  • Score: {github_result.score}/100",
        ])

        if github_result.found_repo and github_result.repo_url:
            parts.append(f"  • <a href='{github_result.repo_url}'>View Repository</a>")

        parts.extend([
            "",
            f"{EMOJI['link']} <a href='{dex_url}'>View on DexScreener</a>",
            "",
            f"🕐 <i>Analyzed: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</i>",
        ])

        return "\n".join(parts)

    def _build_negative_message(
        self, token_name: str, token_symbol: str, token_address: str,
        security_result: SecurityScoreResult,
        honeypot_result: HoneypotResult,
        holders_result: HoldersResult,
        liquidity_result: LiquidityCheckResult,
        github_result: GitHubResult,
    ) -> str:
        """Build a concise warning message for negative tokens."""

        parts = [
            f"{EMOJI['skull']} <b>{token_name} (${token_symbol})</b> {EMOJI['skull']}",
            f"{EMOJI['red_circle']} <b>WARNING: Suspicious Token Detected</b>",
            "",
            f"<code>{token_address}</code>",
            "",
            f"{EMOJI['warning']} <b>Risk Summary:</b>",
        ]

        # Collect all risk issues
        issues = []

        if security_result.score < 50:
            issues.append(f"🔴 Security Score: {security_result.score}/100")
        if security_result.risk_flags:
            for flag in security_result.risk_flags[:3]:
                issues.append(f"  ⚠ {flag}")

        if honeypot_result.is_honeypot:
            issues.append(f"🔴 HONEYPOT DETECTED: {honeypot_result.summary}")
        elif not honeypot_result.success:
            issues.append("🟡 Honeypot check: Could not verify")

        if holders_result.is_concentrated and holders_result.concentration_level != "unknown":
            issues.append(f"🔴 Holder Concentration: {holders_result.concentration_level.upper()}")

        if not liquidity_result.has_lock or liquidity_result.locked_percentage < 40:
            issues.append(f"🔴 Liquidity: NOT SAFELY LOCKED ({liquidity_result.locked_percentage:.0f}%)")

        if not github_result.found_repo:
            issues.append("🔴 No GitHub repository found")
        elif github_result.score < 30:
            issues.append(f"🔴 GitHub Score: {github_result.score}/100 (suspicious)")

        if not issues:
            issues.append("🟡 Some checks returned uncertain results")

        parts.extend(issues)
        parts.extend([
            "",
            f"{EMOJI['cross']} <b>Verdict: HIGH RISK — Avoid this token</b>",
            "",
            f"🕐 <i>Analyzed: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</i>",
        ])

        return "\n".join(parts)

    async def _send_text_fallback(
        self, token_data: Dict,
        security_result: SecurityScoreResult,
        honeypot_result: HoneypotResult,
        holders_result: HoldersResult,
        liquidity_result: LiquidityCheckResult,
        github_result: GitHubResult,
    ) -> bool:
        """Fallback: send text-only if media group fails."""
        token_name = token_data.get("name", "Unknown")
        token_symbol = token_data.get("symbol", "UNKNOWN")
        token_address = token_data.get("address", "")

        score = security_result.score
        message = self._build_positive_message(
            token_name=token_name,
            token_symbol=token_symbol,
            token_address=token_address,
            dex_url=token_data.get("dex_url", ""),
            liquidity_usd=token_data.get("liquidity_usd", 0),
            market_cap=token_data.get("market_cap", 0),
            security_result=security_result,
            honeypot_result=honeypot_result,
            holders_result=holders_result,
            liquidity_result=liquidity_result,
            github_result=github_result,
            overall_score=score,
        )

        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return True
        except Exception as e:
            logger.error(f"Text fallback also failed: {e}")
            return False

    async def close(self):
        """Close the bot session."""
        if self.bot:
            await self.bot.close()