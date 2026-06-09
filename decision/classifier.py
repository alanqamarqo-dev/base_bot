"""
Token Decision Classifier
==========================
Classifies each token into one of three categories:
  SKIP       - High risk, ignore
  WATCH      - Some potential, monitor closely
  EARLY GEM  - Strong signal, act now

Decision Matrix:
┌─────────────────┬───────────┬───────────┬──────────────┐
│     Criteria     │   SKIP    │   WATCH   │  EARLY GEM   │
├─────────────────┼───────────┼───────────┼──────────────┤
│ Security Score   │ <40       │ 40-70     │ >70          │
│ Honeypot         │ YES       │ No w/ tax │ NO           │
│ Liquidity        │ <$1k      │ $1k-$10k  │ >$10k        │
│ Buy/Sell Ratio   │ <0.5      │ 0.5-1.5   │ >1.5         │
│ Volume 5min      │ <$500     │ $500-$5k  │ >$5k         │
│ Age              │ <30s      │ 30s-5min  │ >5min        │
│ Whale Dominance  │ >50%      │ 20-50%    │ <20%         │
│ Momentum Score   │ <30       │ 30-60     │ >60          │
└─────────────────┴───────────┴───────────┴──────────────┘
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from decision.scoring import MomentumScoreResult

logger = logging.getLogger("Classifier")


class Decision(Enum):
    """Final decision category for a token."""
    SKIP = "skip"               # ❌ Ignore - too risky
    WATCH = "watch"             # 👀 Monitor - potential
    EARLY_GEM = "early_gem"     # 💎 Act - strong signal

    @property
    def emoji(self) -> str:
        return {
            "skip": "❌",
            "watch": "👀",
            "early_gem": "💎",
        }.get(self.value, "❓")

    @property
    def label(self) -> str:
        return {
            "skip": "SKIP",
            "watch": "WATCH",
            "early_gem": "EARLY GEM",
        }.get(self.value, "UNKNOWN")

    @property
    def color(self) -> str:
        return {
            "skip": "#ef4444",       # red
            "watch": "#f59e0b",      # amber
            "early_gem": "#22c55e",  # green
        }.get(self.value, "#9ca3af")

    @property
    def priority(self) -> int:
        """Higher priority = more important for alerts."""
        return {
            "skip": 0,
            "watch": 5,
            "early_gem": 10,
        }.get(self.value, 0)


@dataclass
class ClassificationResult:
    """Complete classification result with reasoning."""
    token_address: str
    token_symbol: str = ""
    decision: Decision = Decision.SKIP
    momentum_score: int = 0
    confidence: float = 0.0       # 0.0 - 1.0
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    positive_signals: list = field(default_factory=list)
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "decision": self.decision.value,
            "decision_label": self.decision.label,
            "decision_emoji": self.decision.emoji,
            "momentum_score": self.momentum_score,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "positive_signals": self.positive_signals,
            "timestamp": self.timestamp,
        }


class DecisionEngine:
    """
    Classifies tokens into SKIP / WATCH / EARLY GEM.
    
    Uses a points-based system with the decision matrix.
    Each criterion votes for a category, and the majority wins.
    """

    def classify(
        self,
        momentum_result: MomentumScoreResult,
        is_honeypot: bool = False,
        has_proxy: bool = False,
        is_mintable: bool = False,
        is_blacklisted: bool = False,
        owner_renounced: bool = False,
    ) -> ClassificationResult:
        """
        Classify a token based on its analysis results.
        
        Args:
            momentum_result: The calculated momentum score
            is_honeypot: Whether the token is a honeypot
            has_proxy: Whether the contract uses a proxy
            is_mintable: Whether mint function is active
            is_blacklisted: Whether blacklist exists
            owner_renounced: Whether owner has renounced
        """
        score = momentum_result.total_score
        liquidity = momentum_result.raw_liquidity_usd
        ratio = momentum_result.raw_buy_sell_ratio
        volume = momentum_result.raw_volume_5m_usd
        age = momentum_result.raw_age_seconds
        security = momentum_result.raw_security

        result = ClassificationResult(
            token_address=momentum_result.token_address,
            token_symbol=momentum_result.token_symbol,
            momentum_score=score,
        )

        # ── Hard stops (immediate SKIP) ──
        if is_honeypot:
            result.decision = Decision.SKIP
            result.reasons.append("Honeypot detected")
            result.warnings.append("Token is a honeypot - cannot sell")
            result.confidence = 1.0
            return result

        if is_blacklisted:
            result.decision = Decision.SKIP
            result.reasons.append("Blacklisted token")
            result.warnings.append("Token has blacklist functionality")
            result.confidence = 1.0
            return result

        if momentum_result.liquidity_removed_penalty >= 50:
            result.decision = Decision.SKIP
            result.reasons.append("Liquidity removed (possible rug)")
            result.warnings.append("Liquidity was pulled from pool")
            result.confidence = 1.0
            return result

        # ── Points-based decision ──
        points_skip = 0
        points_watch = 0
        points_gem = 0
        total_criteria = 0

        # Criterion 1: Security Score
        if security < 40:
            points_skip += 1
        elif security < 70:
            points_watch += 1
        else:
            points_gem += 1
        total_criteria += 1

        # Criterion 2: Liquidity
        if liquidity < 1_000:
            points_skip += 1
        elif liquidity < 10_000:
            points_watch += 1
        else:
            points_gem += 1
        total_criteria += 1

        # Criterion 3: Buy/Sell Ratio
        if ratio < 0.5:
            points_skip += 1
        elif ratio < 1.5:
            points_watch += 1
        else:
            points_gem += 1
        total_criteria += 1

        # Criterion 4: Volume 5min
        if volume < 500:
            points_skip += 1
        elif volume < 5_000:
            points_watch += 1
        else:
            points_gem += 1
        total_criteria += 1

        # Criterion 5: Age
        if age < 30:
            points_skip += 1
        elif age < 300:  # 5 minutes
            points_watch += 1
        else:
            points_gem += 1
        total_criteria += 1

        # Criterion 6: Momentum Score
        if score < 30:
            points_skip += 1
        elif score < 60:
            points_watch += 1
        else:
            points_gem += 1
        total_criteria += 1

        # ── Determine decision ──
        if points_gem >= points_watch and points_gem >= points_skip:
            result.decision = Decision.EARLY_GEM
            result.confidence = points_gem / total_criteria
            result.positive_signals.append(f"Strong momentum: {points_gem}/{total_criteria} criteria passed")
        elif points_watch >= points_skip:
            result.decision = Decision.WATCH
            result.confidence = points_watch / total_criteria
        else:
            result.decision = Decision.SKIP
            result.confidence = points_skip / total_criteria

        # ── Build reasoning ──
        if security >= 70:
            result.positive_signals.append(f"Security score: {security}/100")
        if liquidity >= 10_000:
            result.positive_signals.append(f"Liquidity: ${liquidity:,.0f}")
        if ratio >= 1.5:
            result.positive_signals.append(f"Buy/Sell ratio: {ratio:.1f}x")
        if volume >= 5_000:
            result.positive_signals.append(f"Volume 5min: ${volume:,.0f}")
        if age >= 300:
            result.positive_signals.append(f"Age: {int(age//60)}min+")

        if has_proxy:
            result.warnings.append("Proxy contract detected")
        if is_mintable:
            result.warnings.append("Mint function is active")
        if not owner_renounced:
            result.warnings.append("Owner has not renounced")
        if momentum_result.whale_penalty > 0:
            result.warnings.append(f"Whale dominance detected")

        if not result.positive_signals:
            result.reasons.append("No strong positive signals")
        if not result.warnings:
            result.positive_signals.append("No security warnings found")

        result.reasons.extend(result.positive_signals)
        result.reasons.extend(result.warnings)

        import time
        result.timestamp = time.time()

        logger.info(
            f"Decision for {result.token_symbol or result.token_address[:10]}: "
            f"{result.decision.emoji} {result.decision.label} "
            f"(score: {score}, confidence: {result.confidence:.0%})"
        )

        return result
