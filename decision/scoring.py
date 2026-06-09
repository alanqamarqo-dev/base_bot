"""
Momentum Scoring System (0-100)
================================
Calculates a composite score based on:
  - Security Score     × 0.25  (from GoPlus)
  - Liquidity Score    × 0.20  (liquidity in USD)
  - Volume Score       × 0.20  (5-min volume)
  - Buy/Sell Ratio     × 0.15  (buyers vs sellers)
  - Holders Score      × 0.10  (concentration level)
  - Age Score          × 0.10  (time since creation)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("Scoring")


@dataclass
class MomentumScoreResult:
    """Complete momentum score with breakdown."""
    token_address: str
    token_symbol: str = ""
    total_score: int = 0

    # Sub-scores
    security_score: int = 0
    liquidity_score: int = 0
    volume_score: int = 0
    buy_sell_ratio_score: int = 0
    holders_score: int = 0
    age_score: int = 0

    # Raw values
    raw_security: int = 0
    raw_liquidity_usd: float = 0.0
    raw_volume_5m_usd: float = 0.0
    raw_buy_sell_ratio: float = 0.0
    raw_holders_concentration: str = "unknown"
    raw_age_seconds: float = 0.0

    # Bonus/penalty
    smart_money_bonus: int = 0       # +10 if smart money detected
    whale_penalty: int = 0           # -20 if whale dominates
    liquidity_removed_penalty: int = 0  # -50 if liquidity pulled

    def to_dict(self) -> dict:
        return {
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "total_score": self.total_score,
            "breakdown": {
                "security": self.security_score,
                "liquidity": self.liquidity_score,
                "volume": self.volume_score,
                "buy_sell_ratio": self.buy_sell_ratio_score,
                "holders": self.holders_score,
                "age": self.age_score,
            },
            "raw_values": {
                "security": self.raw_security,
                "liquidity_usd": self.raw_liquidity_usd,
                "volume_5m_usd": self.raw_volume_5m_usd,
                "buy_sell_ratio": self.raw_buy_sell_ratio,
                "holders_concentration": self.raw_holders_concentration,
                "age_seconds": self.raw_age_seconds,
            },
            "modifiers": {
                "smart_money_bonus": self.smart_money_bonus,
                "whale_penalty": self.whale_penalty,
                "liquidity_removed_penalty": self.liquidity_removed_penalty,
            },
        }


class MomentumScorer:
    """
    Calculates the 0-100 Momentum Score for a token.
    
    Formula:
        Momentum = Security×0.25 + Liquidity×0.20 + Volume×0.20 
                 + BuySellRatio×0.15 + Holders×0.10 + Age×0.10
                 + SmartMoneyBonus - WhalePenalty - LiquidityRemovedPenalty
    """

    # Weight constants
    W_SECURITY = 0.25
    W_LIQUIDITY = 0.20
    W_VOLUME = 0.20
    W_BUY_SELL = 0.15
    W_HOLDERS = 0.10
    W_AGE = 0.10

    # Liquidity thresholds for scoring
    LIQUIDITY_CAPS = [
        (100_000, 100),   # $100k+ = full score
        (50_000, 90),
        (20_000, 70),
        (10_000, 50),
        (5_000, 30),
        (1_000, 10),
        (0, 0),
    ]

    # Volume thresholds for scoring (5min)
    VOLUME_CAPS = [
        (50_000, 100),    # $50k+ in 5min = full score
        (20_000, 85),
        (10_000, 65),
        (5_000, 40),
        (1_000, 20),
        (0, 0),
    ]

    # Holders concentration mapping
    HOLDERS_SCORE_MAP = {
        "low": 100,
        "medium": 60,
        "high": 30,
        "extreme": 0,
        "unknown": 40,
    }

    def calculate(
        self,
        token_address: str,
        token_symbol: str = "",
        security_score: int = 0,
        liquidity_usd: float = 0.0,
        volume_5m_usd: float = 0.0,
        buy_sell_ratio: float = 0.0,
        holders_concentration: str = "unknown",
        age_seconds: float = 0.0,
        smart_money_detected: bool = False,
        whale_dominance_pct: float = 0.0,
        liquidity_removed: bool = False,
    ) -> MomentumScoreResult:
        """
        Calculate the momentum score.
        
        Args:
            security_score: GoPlus security score (0-100)
            liquidity_usd: Current liquidity in USD
            volume_5m_usd: 5-minute trading volume in USD
            buy_sell_ratio: Ratio of buys to sells (>1 = more buys)
            holders_concentration: low/medium/high/extreme/unknown
            age_seconds: Age of the token in seconds
            smart_money_detected: Whether known smart wallets bought
            whale_dominance_pct: Percentage held by largest whale
            liquidity_removed: Whether liquidity was pulled
        """
        result = MomentumScoreResult(
            token_address=token_address,
            token_symbol=token_symbol,
        )

        # Store raw values
        result.raw_security = security_score
        result.raw_liquidity_usd = liquidity_usd
        result.raw_volume_5m_usd = volume_5m_usd
        result.raw_buy_sell_ratio = buy_sell_ratio
        result.raw_holders_concentration = holders_concentration
        result.raw_age_seconds = age_seconds

        # 1. Security Score (already 0-100 from GoPlus)
        result.security_score = max(0, min(100, security_score))

        # 2. Liquidity Score: logarithmic-ish scale
        result.liquidity_score = self._scale_value(liquidity_usd, self.LIQUIDITY_CAPS)

        # 3. Volume Score
        result.volume_score = self._scale_value(volume_5m_usd, self.VOLUME_CAPS)

        # 4. Buy/Sell Ratio Score
        # ratio > 2 = full (100), ratio = 1 = 50, ratio < 0.5 = 0
        result.buy_sell_ratio_score = self._calc_buy_sell_score(buy_sell_ratio)

        # 5. Holders Score
        result.holders_score = self.HOLDERS_SCORE_MAP.get(
            holders_concentration, 40
        )

        # 6. Age Score: full at 5 minutes (300s)
        result.age_score = min(100, int((age_seconds / 300) * 100))

        # ── Modifiers ──
        # Smart money bonus
        if smart_money_detected:
            result.smart_money_bonus = 10

        # Whale penalty
        if whale_dominance_pct > 50:
            result.whale_penalty = 30
        elif whale_dominance_pct > 30:
            result.whale_penalty = 20
        elif whale_dominance_pct > 15:
            result.whale_penalty = 10

        # Liquidity removal penalty
        if liquidity_removed:
            result.liquidity_removed_penalty = 50

        # ── Calculate total ──
        raw_total = (
            result.security_score * self.W_SECURITY
            + result.liquidity_score * self.W_LIQUIDITY
            + result.volume_score * self.W_VOLUME
            + result.buy_sell_ratio_score * self.W_BUY_SELL
            + result.holders_score * self.W_HOLDERS
            + result.age_score * self.W_AGE
        )

        # Apply modifiers
        total = raw_total + result.smart_money_bonus - result.whale_penalty - result.liquidity_removed_penalty

        # Clamp 0-100
        result.total_score = max(0, min(100, int(total)))

        logger.info(
            f"Score for {token_symbol or token_address[:10]}: "
            f"{result.total_score}/100 "
            f"(Sec:{result.security_score} Liq:{result.liquidity_score} "
            f"Vol:{result.volume_score} B/S:{result.buy_sell_ratio_score} "
            f"Hold:{result.holders_score} Age:{result.age_score})"
            f"{' +SM' if smart_money_detected else ''}"
            f"{' -WHALE' if result.whale_penalty else ''}"
            f"{' -RUG' if result.liquidity_removed_penalty else ''}"
        )

        return result

    @staticmethod
    def _scale_value(value: float, caps: list) -> int:
        """Scale a numeric value to 0-100 based on threshold caps."""
        for threshold, score in caps:
            if value >= threshold:
                # Linear interpolation between this cap and next (higher) cap
                return int(score)
        return 0

    @staticmethod
    def _calc_buy_sell_score(ratio: float) -> int:
        """
        Calculate buy/sell ratio score.
        ratio 3+  → 100
        ratio 2   → 80
        ratio 1.5 → 65
        ratio 1   → 50
        ratio 0.7 → 30
        ratio 0.5 → 10
        ratio <0.3→ 0
        """
        if ratio <= 0:
            return 0
        if ratio >= 3.0:
            return 100
        if ratio >= 2.0:
            return 80
        if ratio >= 1.5:
            return 65
        if ratio >= 1.0:
            return 50
        if ratio >= 0.7:
            return 30
        if ratio >= 0.5:
            return 10
        return 0
