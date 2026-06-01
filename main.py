"""
Main Orchestrator - Base Chain Token Scanner Bot
=================================================
Daily pipeline:
1. Scan DexScreener for new Base chain tokens
2. Run 5 analyzers on each token (Security, Honeypot, Holders, Liquidity, GitHub)
3. Generate charts for positive tokens
4. Send results to Telegram channel
5. Store everything in the database
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner.base_scanner import BaseScanner, TokenData
from scanner.dex_scanner import DexScanner
from analyzers.security_score import SecurityScoreChecker, SecurityScoreResult
from analyzers.honeypot_checker import HoneypotChecker, HoneypotResult
from analyzers.holders_checker import HoldersChecker, HoldersResult
from analyzers.liquidity_checker import LiquidityChecker, LiquidityCheckResult
from analyzers.github_checker import GitHubChecker, GitHubResult
from charts.chart_generator import ChartGenerator
from database.storage import Database
from telegram_bot.sender import TelegramSender

# ── Configuration ────────────────────────────────────────────────

# Load from environment or use defaults
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
BASESCAN_API_KEY = os.getenv("BASESCAN_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "base_bot.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SCAN_INTERVAL_HOURS = int(os.getenv("SCAN_INTERVAL_HOURS", "24"))
MAX_TOKENS_PER_SCAN = int(os.getenv("MAX_TOKENS_PER_SCAN", "30"))
MIN_LIQUIDITY_USD = float(os.getenv("MIN_LIQUIDITY_USD", "1000"))
ENABLE_CHARTS = os.getenv("ENABLE_CHARTS", "true").lower() == "true"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("base_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("BaseBot")


@dataclass
class TokenAnalysisResult:
    """Aggregates all analysis results for a single token."""
    token_data: Dict
    security: SecurityScoreResult
    honeypot: HoneypotResult
    holders: HoldersResult
    liquidity: LiquidityCheckResult
    github: GitHubResult
    overall_score: int = 0
    is_positive: bool = False

    @property
    def token_name(self) -> str:
        return self.token_data.get("name", "Unknown")

    @property
    def token_symbol(self) -> str:
        return self.token_data.get("symbol", "UNKNOWN")


class BaseBotOrchestrator:
    """
    Main orchestrator that runs the daily scan pipeline:
    Scan → Analyze → Classify → Chart → Send → Store
    """

    def __init__(self):
        self.scanner = BaseScanner(
            max_results=MAX_TOKENS_PER_SCAN,
            min_liquidity_usd=MIN_LIQUIDITY_USD,
        )
        self.dex_scanner = DexScanner()
        self.security_checker = SecurityScoreChecker()
        self.honeypot_checker = HoneypotChecker()
        self.holders_checker = HoldersChecker(basescan_api_key=BASESCAN_API_KEY)
        self.liquidity_checker = LiquidityChecker()
        self.github_checker = GitHubChecker(github_token=GITHUB_TOKEN)
        self.chart_gen = ChartGenerator(style="dark") if ENABLE_CHARTS else None
        self.db = Database(db_path=DB_PATH)
        self.telegram: Optional[TelegramSender] = None

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
            self.telegram = TelegramSender(
                bot_token=TELEGRAM_BOT_TOKEN,
                channel_id=TELEGRAM_CHANNEL_ID,
                chart_generator=self.chart_gen,
            )
        else:
            logger.warning("Telegram credentials not set. Skipping Telegram sending.")

    async def run_daily_scan(self) -> Tuple[int, int, int]:
        """
        Run the complete daily scan pipeline.
        Returns (total, positive, negative).
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"=== Starting daily scan for {date_str} ===")

        # Create daily scan record
        scan_id = self.db.create_daily_scan(date_str)

        # Step 1: Scan for new tokens
        logger.info("[1/5] Scanning DexScreener for new Base chain tokens...")
        tokens = await self.scanner.fetch_latest_tokens()
        logger.info(f"Found {len(tokens)} tokens on Base chain")

        if not tokens:
            logger.info("No new tokens found today.")
            self.db.complete_daily_scan(scan_id, 0, 0, 0)
            return 0, 0, 0

        # Step 2: Analyze each token
        logger.info(f"[2/5] Analyzing {len(tokens)} tokens...")
        analyses: List[TokenAnalysisResult] = []

        for i, token in enumerate(tokens):
            token_dict = token.to_dict()
            logger.info(f"  [{i+1}/{len(tokens)}] Analyzing {token.symbol} ({token.name})...")

            result = await self._analyze_token(token_dict)
            analyses.append(result)

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        # Step 3: Classify into positive/negative
        logger.info("[3/5] Classifying tokens...")
        positive_tokens = [a for a in analyses if a.is_positive]
        negative_tokens = [a for a in analyses if not a.is_positive]

        logger.info(
            f"Classification: {len(positive_tokens)} positive, "
            f"{len(negative_tokens)} negative out of {len(analyses)} total"
        )

        # Step 4: Store in database
        logger.info("[4/5] Storing results...")
        for analysis in analyses:
            token_dict = analysis.token_data
            self.db.upsert_token(token_dict)

            # Save each analysis result
            self.db.save_analysis(
                token_dict["address"], "security",
                analysis.security.to_dict(),
                is_safe=analysis.security.is_safe,
                score=analysis.security.score,
            )
            self.db.save_analysis(
                token_dict["address"], "honeypot",
                analysis.honeypot.to_dict(),
                is_safe=analysis.honeypot.is_safe,
                score=100 if analysis.honeypot.is_safe else 0,
            )
            self.db.save_analysis(
                token_dict["address"], "holders",
                analysis.holders.to_dict(),
                is_safe=analysis.holders.is_safe,
                score=80 if analysis.holders.is_safe else 30,
            )
            self.db.save_analysis(
                token_dict["address"], "liquidity",
                analysis.liquidity.to_dict(),
                is_safe=analysis.liquidity.is_safe,
                score=100 if analysis.liquidity.is_safe else 30,
            )
            self.db.save_analysis(
                token_dict["address"], "github",
                analysis.github.to_dict(),
                is_safe=analysis.github.is_legitimate,
                score=analysis.github.score,
            )

            # Add to scan
            self.db.add_scan_token(scan_id, token_dict["address"],
                                   is_positive=analysis.is_positive,
                                   overall_score=analysis.overall_score)

        # Mark scan complete
        self.db.complete_daily_scan(scan_id, len(positive_tokens),
                                     len(negative_tokens), len(analyses))

        # Step 5: Send to Telegram
        logger.info("[5/5] Sending results to Telegram...")
        if self.telegram:
            # Send positive tokens with full details and charts
            for analysis in positive_tokens:
                await self.telegram.send_positive_token(
                    token_data=analysis.token_data,
                    security_result=analysis.security,
                    honeypot_result=analysis.honeypot,
                    holders_result=analysis.holders,
                    liquidity_result=analysis.liquidity,
                    github_result=analysis.github,
                    overall_score=analysis.overall_score,
                )
                await asyncio.sleep(1)  # Rate limit between sends

            # Send negative tokens as concise warnings
            for analysis in negative_tokens:
                await self.telegram.send_negative_token(
                    token_data=analysis.token_data,
                    security_result=analysis.security,
                    honeypot_result=analysis.honeypot,
                    holders_result=analysis.holders,
                    liquidity_result=analysis.liquidity,
                    github_result=analysis.github,
                )
                await asyncio.sleep(0.5)

            # Send daily summary
            positive_list = [
                {
                    "name": a.token_name,
                    "symbol": a.token_symbol,
                    "address": a.token_data["address"],
                    "overall_score": a.overall_score,
                }
                for a in positive_tokens
            ]
            await self.telegram.send_daily_summary(
                date_str=date_str,
                total_tokens=len(analyses),
                positive_count=len(positive_tokens),
                negative_count=len(negative_tokens),
                positive_tokens=positive_list,
            )

        logger.info(
            f"=== Daily scan complete: {len(analyses)} tokens, "
            f"{len(positive_tokens)} positive, {len(negative_tokens)} negative ==="
        )

        return len(analyses), len(positive_tokens), len(negative_tokens)

    async def _analyze_token(self, token_dict: Dict) -> TokenAnalysisResult:
        """Run all 5 analyzers on a single token."""
        address = token_dict["address"]
        name = token_dict.get("name", "Unknown")
        symbol = token_dict.get("symbol", "UNKNOWN")
        github_url = token_dict.get("github", "")
        liquidity_usd = token_dict.get("liquidity_usd", 0)

        # Run all analyzers concurrently
        security_task = self.security_checker.check(address, name, symbol)
        honeypot_task = self.honeypot_checker.check(address, name, symbol)
        holders_task = self.holders_checker.check(address, name, symbol)
        liquidity_task = self.liquidity_checker.check(address, name, symbol, liquidity_usd)
        github_task = self.github_checker.check(address, name, symbol, github_url)

        security, honeypot, holders, liquidity, github = await asyncio.gather(
            security_task, honeypot_task, holders_task, liquidity_task, github_task,
            return_exceptions=True,
        )

        # Handle exceptions gracefully
        if isinstance(security, Exception):
            logger.error(f"Security check failed for {symbol}: {security}")
            security = SecurityScoreResult(token_address=address, error_message=str(security))
        if isinstance(honeypot, Exception):
            logger.error(f"Honeypot check failed for {symbol}: {honeypot}")
            honeypot = HoneypotResult(token_address=address, error_message=str(honeypot))
        if isinstance(holders, Exception):
            logger.error(f"Holders check failed for {symbol}: {holders}")
            holders = HoldersResult(token_address=address, error_message=str(holders))
        if isinstance(liquidity, Exception):
            logger.error(f"Liquidity check failed for {symbol}: {liquidity}")
            liquidity = LiquidityCheckResult(token_address=address, error_message=str(liquidity))
        if isinstance(github, Exception):
            logger.error(f"GitHub check failed for {symbol}: {github}")
            github = GitHubResult(token_address=address, error_message=str(github))

        # Calculate overall score and determine positive/negative
        overall_score, is_positive = self._evaluate_token(
            security, honeypot, holders, liquidity, github
        )

        return TokenAnalysisResult(
            token_data=token_dict,
            security=security,
            honeypot=honeypot,
            holders=holders,
            liquidity=liquidity,
            github=github,
            overall_score=overall_score,
            is_positive=is_positive,
        )

    @staticmethod
    def _evaluate_token(
        security: SecurityScoreResult,
        honeypot: HoneypotResult,
        holders: HoldersResult,
        liquidity: LiquidityCheckResult,
        github: GitHubResult,
    ) -> Tuple[int, bool]:
        """
        Calculate overall score and determine if token is positive.
        Weights:
        - Security: 30%
        - Honeypot: 25%
        - Holders: 20%
        - Liquidity: 20%
        - GitHub: 5%
        """
        scores = []

        # Security score (0-100)
        scores.append((security.score if security.success else 0, 30))

        # Honeypot (0 or 100)
        hp_score = 100 if (honeypot.success and honeypot.is_safe) else 0
        scores.append((hp_score, 25))

        # Holders
        if holders.concentration_level == "low":
            h_score = 100
        elif holders.concentration_level == "medium":
            h_score = 60
        elif holders.concentration_level == "high":
            h_score = 30
        elif holders.concentration_level == "extreme":
            h_score = 0
        else:
            h_score = 50  # unknown
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

        # Weighted average
        total_weight = sum(w for _, w in scores)
        if total_weight > 0:
            weighted = sum(s * w for s, w in scores) / total_weight
        else:
            weighted = 0

        overall_score = round(weighted)

        # Positive criteria:
        # - Overall score >= 60
        # - Not a honeypot
        # - Security score >= 40
        is_positive = (
            overall_score >= 60
            and not honeypot.is_honeypot
            and security.score >= 40
            and not (liquidity.locked_percentage == 0 and liquidity.total_liquidity_usd > 0)
        )

        return overall_score, is_positive

    async def run_single_token_check(self, token_address: str, token_name: str = "",
                                      token_symbol: str = "") -> TokenAnalysisResult:
        """Run analysis on a single specific token address."""
        token_dict = {
            "address": token_address,
            "name": token_name or "Custom Token",
            "symbol": token_symbol or "CUSTOM",
            "chain": "base",
            "liquidity_usd": 0,
            "github": "",
            "dex_url": f"https://dexscreener.com/base/{token_address}",
        }
        return await self._analyze_token(token_dict)

    async def print_stats(self):
        """Print database statistics."""
        stats = self.db.get_statistics()
        print("\n📊 Base Bot Statistics:")
        print(f"  Total tokens tracked: {stats['total_tokens']}")
        print(f"  Total analyses run: {stats['total_analyses']}")
        print(f"  Total daily scans: {stats['total_scans']}")
        print(f"  Positive tokens found: {stats['total_positive']}")
        print(f"  Negative tokens flagged: {stats['total_negative']}")

    async def close(self):
        """Clean up all resources."""
        await self.scanner.close()
        await self.dex_scanner.close()
        await self.security_checker.close()
        await self.honeypot_checker.close()
        await self.holders_checker.close()
        await self.liquidity_checker.close()
        await self.github_checker.close()
        if self.telegram:
            await self.telegram.close()
        self.db.close()
        logger.info("All resources cleaned up.")


# ── Entry Points ──────────────────────────────────────────────────

async def main_daily_scan():
    """Entry point: daily automatic scan."""
    bot = BaseBotOrchestrator()
    try:
        total, positive, negative = await bot.run_daily_scan()
        print(f"\n✅ Scan complete: {total} tokens ({positive} positive, {negative} negative)")
        await bot.print_stats()
    finally:
        await bot.close()


async def main_check_single(address: str, name: str = "", symbol: str = ""):
    """Entry point: check a single token."""
    bot = BaseBotOrchestrator()
    try:
        print(f"\n🔍 Analyzing token: {address}")
        result = await bot.run_single_token_check(address, name, symbol)
        print(f"\n{'='*60}")
        print(f"Token: {result.token_name} (${result.token_symbol})")
        print(f"Address: {address}")
        print(f"Overall Score: {result.overall_score}/100")
        print(f"Classification: {'✅ POSITIVE' if result.is_positive else '🔴 NEGATIVE'}")
        print(f"{'='*60}")
        print(f"Security Score: {result.security.score}/100 — {result.security.summary}")
        print(f"Honeypot: {result.honeypot.status_text}")
        print(f"Holders: {result.holders.status_text}")
        print(f"Liquidity: {result.liquidity.status_text}")
        print(f"GitHub: {result.github.status_text}")

        # Send to Telegram if configured
        if bot.telegram:
            if result.is_positive:
                await bot.telegram.send_positive_token(
                    token_data=result.token_data,
                    security_result=result.security,
                    honeypot_result=result.honeypot,
                    holders_result=result.holders,
                    liquidity_result=result.liquidity,
                    github_result=result.github,
                    overall_score=result.overall_score,
                )
            else:
                await bot.telegram.send_negative_token(
                    token_data=result.token_data,
                    security_result=result.security,
                    honeypot_result=result.honeypot,
                    holders_result=result.holders,
                    liquidity_result=result.liquidity,
                    github_result=result.github,
                )
    finally:
        await bot.close()


async def main_test():
    """Entry point: run with mock data for testing."""
    bot = BaseBotOrchestrator()
    try:
        print("\n🧪 Running in test mode (scanning live DexScreener)...")
        # Use the live scanner but with reduced tokens
        bot.scanner.max_results = 5
        total, positive, negative = await bot.run_daily_scan()
        print(f"\n✅ Test complete: {total} tokens ({positive} positive, {negative} negative)")
        await bot.print_stats()
    finally:
        await bot.close()


def run_daily():
    """Synchronous entry point for cron/scheduler."""
    asyncio.run(main_daily_scan())


def run_single(address: str, name: str = "", symbol: str = ""):
    """Synchronous entry point for single token check."""
    asyncio.run(main_check_single(address, name, symbol))


def run_test():
    """Synchronous entry point for testing."""
    asyncio.run(main_test())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Base Chain Token Scanner Bot")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Daily scan
    subparsers.add_parser("scan", help="Run daily scan of new tokens")

    # Single token check
    single_parser = subparsers.add_parser("check", help="Check a single token")
    single_parser.add_argument("address", help="Token contract address")
    single_parser.add_argument("--name", default="", help="Token name")
    single_parser.add_argument("--symbol", default="", help="Token symbol")

    # Test mode
    subparsers.add_parser("test", help="Run in test mode (limited tokens)")

    # Stats
    subparsers.add_parser("stats", help="Show database statistics")

    args = parser.parse_args()

    if args.command == "scan":
        asyncio.run(main_daily_scan())
    elif args.command == "check":
        asyncio.run(main_check_single(args.address, args.name, args.symbol))
    elif args.command == "test":
        asyncio.run(main_test())
    elif args.command == "stats":
        asyncio.run(BaseBotOrchestrator().print_stats())
    else:
        parser.print_help()