"""
Base Launch Detector - Main Orchestrator
=========================================
Real-time streaming pipeline that monitors Base chain DEX factories,
tracks new pairs, liquidity, runs risk analysis, calculates momentum,
and classifies tokens as SKIP / WATCH / EARLY GEM.

Pipeline:
    Base RPC WS → Pair Monitor → Liquidity Monitor → Risk Scanner
                 → Momentum Engine → Decision Engine → Telegram + API

Usage:
    python main_monitor.py
    
    # Or with custom settings:
    MONITOR_AERODROME=true MONITOR_UNISWAP_V3=false python main_monitor.py
"""

import asyncio
import logging
import signal
import sys
import os
import time
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config.settings import settings
from monitors.pair_monitor import PairMonitor, NewPairEvent
from monitors.liquidity_monitor import LiquidityMonitor, LiquidityEvent, LiquidityEventType
from monitors.risk_scanner import RiskScanner, RiskScanResult
from monitors.momentum_engine import MomentumEngine, MomentumSnapshot
from decision.scoring import MomentumScorer, MomentumScoreResult
from decision.classifier import DecisionEngine, Decision, ClassificationResult
from alerts.alert_manager import AlertManager, Alert, AlertType
from api.server import APIServer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("base_monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("BaseLaunchDetector")


class BaseLaunchDetector:
    """
    Main orchestrator for the real-time Base chain monitoring pipeline.
    
    Connects all phases:
    1. Pair Monitor - detects new pairs from DEX factories
    2. Liquidity Monitor - watches for liquidity events
    3. Risk Scanner - runs existing analyzers concurrently
    4. Momentum Engine - tracks trading activity
    5. Decision Engine - classifies tokens
    6. Alert Manager - dispatches alerts
    7. API Server - provides REST + WebSocket access
    """

    def __init__(self):
        # Queues for inter-phase communication
        self.pair_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.liquidity_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.momentum_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

        # Components
        self.pair_monitor: Optional[PairMonitor] = None
        self.liquidity_monitor: Optional[LiquidityMonitor] = None
        self.risk_scanner: Optional[RiskScanner] = None
        self.momentum_engine: Optional[MomentumEngine] = None
        self.scorer: MomentumScorer = MomentumScorer()
        self.classifier: DecisionEngine = DecisionEngine()
        self.alert_manager: AlertManager = AlertManager()
        self.api_server: Optional[APIServer] = None

        # State
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._start_time: float = 0.0

        # Stats
        self._pairs_detected: int = 0
        self._liquidity_events: int = 0
        self._scans_completed: int = 0
        self._momentum_snapshots: int = 0
        self._decisions_made: int = 0
        self._alerts_sent: int = 0

    async def start(self):
        """Start the entire monitoring pipeline."""
        self._running = True
        self._start_time = time.time()

        logger.info("=" * 60)
        logger.info("🚀 Base Launch Detector v2.0 Starting...")
        logger.info(f"   RPC: {settings.rpc.ws_url[:50]}...")
        logger.info(f"   Aerodrome: {settings.monitor.aerodrome}")
        logger.info(f"   Uniswap V3: {settings.monitor.uniswap_v3}")
        logger.info(f"   Min Liquidity Alert: ${settings.monitor.min_liquidity_alert_usd:,.0f}")
        logger.info(f"   Momentum Check After: {settings.monitor.momentum_check_after_seconds}s")
        logger.info(f"   API Server: {settings.api.host}:{settings.api.port}")
        logger.info("=" * 60)

        # ── Phase 1: Start Pair Monitor ──
        self.pair_monitor = PairMonitor()
        await self.pair_monitor.start()

        # Start pair consumer
        pair_consumer = asyncio.create_task(self._consume_pairs())
        self._tasks.append(pair_consumer)

        # ── Phase 2: Start Liquidity Monitor ──
        self.liquidity_monitor = LiquidityMonitor(
            w3=self.pair_monitor.w3,
            pair_queue=self.pair_queue,
            output_queue=self.liquidity_queue,
        )
        await self.liquidity_monitor.start()

        # ── Phase 3: Initialize Risk Scanner ──
        self.risk_scanner = RiskScanner()

        # ── Phase 4: Start Momentum Engine ──
        self.momentum_engine = MomentumEngine(
            w3=self.pair_monitor.w3,
            liquidity_queue=self.liquidity_queue,
            output_queue=self.momentum_queue,
        )
        await self.momentum_engine.start()

        # ── Phase 5: Start Decision Pipeline ──
        decision_consumer = asyncio.create_task(self._consume_momentum())
        self._tasks.append(decision_consumer)

        # ── Phase 6: Start Alert Pipeline ──
        alert_consumer = asyncio.create_task(self._consume_decisions())
        self._tasks.append(alert_consumer)

        # ── Phase 7: Start API Server (if enabled) ──
        if settings.api.enabled:
            self.api_server = APIServer()
            # Wire up shared state
            self.api_server.pair_monitor = self.pair_monitor
            self.api_server.liquidity_monitor = self.liquidity_monitor
            self.api_server.momentum_engine = self.momentum_engine
            self.api_server.risk_scanner = self.risk_scanner
            self.api_server.alert_manager = self.alert_manager

            # Subscribe API to alerts for WebSocket broadcasting
            self.alert_manager.subscribe(self.api_server.broadcast)

            api_task = asyncio.create_task(
                self.api_server.run(settings.api.host, settings.api.port)
            )
            self._tasks.append(api_task)
            logger.info(f"🌐 API Server: http://{settings.api.host}:{settings.api.port}")

        logger.info("✅ All systems started. Monitoring Base chain...")

        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1.0)

    async def _consume_pairs(self):
        """Consume new pairs from Pair Monitor and feed to Liquidity Monitor."""
        async for pair_event in self.pair_monitor.stream():
            if not self._running:
                break

            self._pairs_detected += 1

            # Store in API cache
            if self.api_server:
                self.api_server.add_token(pair_event.to_dict())

            # Send alert
            await self.alert_manager.send_alert(Alert(
                alert_type=AlertType.NEW_PAIR,
                title=f"New Pair: {pair_event.base_token}/{pair_event.token_address[:10]}...",
                body=f"DEX: {pair_event.dex} | Type: {pair_event.pair_type}",
                data=pair_event.to_dict(),
                priority=3,
            ))

            # Forward to liquidity monitor queue
            await self.pair_queue.put(pair_event)

    async def _consume_momentum(self):
        """Consume momentum snapshots and run decision pipeline."""
        while self._running:
            try:
                snapshot = await asyncio.wait_for(self.momentum_queue.get(), timeout=5.0)
                if isinstance(snapshot, MomentumSnapshot):
                    await self._process_momentum(snapshot)
            except asyncio.TimeoutError:
                continue

    async def _process_momentum(self, snapshot: MomentumSnapshot):
        """Process a momentum snapshot: scan → score → classify → alert."""
        self._momentum_snapshots += 1

        token_address = snapshot.token_address
        token_symbol = snapshot.token_symbol

        # Step 1: Run Risk Scan
        liq_event = LiquidityEvent(
            token_address=token_address,
            pair_address=snapshot.pair_address,
            base_token=snapshot.base_token,
            event_type=LiquidityEventType.INITIAL_LIQUIDITY,
            liquidity_usd=snapshot.current_liquidity_usd or 0,
        )

        risk_result = await self.risk_scanner.scan(liq_event, token_symbol)
        self._scans_completed += 1

        if self.api_server:
            self.api_server.add_analysis(token_address, risk_result.to_dict())

        # Step 2: Calculate Momentum Score
        score_result = self.scorer.calculate(
            token_address=token_address,
            token_symbol=token_symbol,
            security_score=risk_result.security_score,
            liquidity_usd=snapshot.current_liquidity_usd or 0,
            volume_5m_usd=snapshot.volume_5m_usd,
            buy_sell_ratio=snapshot.buy_sell_ratio,
            holders_concentration=risk_result.holders_concentration,
            age_seconds=snapshot.age_seconds,
            smart_money_detected=snapshot.smart_money_detected,
            whale_dominance_pct=snapshot.whale_dominance_pct,
            liquidity_removed=False,
        )

        # Step 3: Classify
        classification = self.classifier.classify(
            momentum_result=score_result,
            is_honeypot=risk_result.is_honeypot,
            has_proxy=risk_result.has_proxy,
            is_mintable=risk_result.is_mintable,
            is_blacklisted=risk_result.is_blacklisted,
            owner_renounced=risk_result.owner_renounced,
        )

        self._decisions_made += 1

        if self.api_server:
            self.api_server.add_decision(token_address, classification.to_dict())

        # Step 4: Alert based on decision
        if classification.decision == Decision.EARLY_GEM:
            await self.alert_manager.send_alert(Alert(
                alert_type=AlertType.EARLY_GEM,
                title=f"EARLY GEM: {token_symbol}/{snapshot.base_token}",
                body=f"Score: {score_result.total_score}/100 | Momentum: Strong",
                data={
                    **snapshot.to_dict(),
                    **risk_result.to_dict(),
                    **score_result.to_dict(),
                    "decision": classification.decision.value,
                    "momentum_score": score_result.total_score,
                    "liquidity_usd": snapshot.current_liquidity_usd,
                    "smart_money": snapshot.smart_money_detected,
                },
                priority=10,
            ))

        elif classification.decision == Decision.WATCH:
            await self.alert_manager.send_alert(Alert(
                alert_type=AlertType.WATCH,
                title=f"WATCH: {token_symbol}/{snapshot.base_token}",
                body=f"Score: {score_result.total_score}/100",
                data={
                    **snapshot.to_dict(),
                    **risk_result.to_dict(),
                    "momentum_score": score_result.total_score,
                },
                priority=5,
            ))

        # Special alerts
        if snapshot.smart_money_detected:
            await self.alert_manager.send_alert(Alert(
                alert_type=AlertType.SMART_MONEY,
                title=f"Smart Money: {token_symbol}",
                body=f"Known wallets detected buying {token_symbol}",
                data=snapshot.to_dict(),
                priority=8,
            ))

        if snapshot.whales_detected > 0:
            await self.alert_manager.send_alert(Alert(
                alert_type=AlertType.WHALE_DETECTED,
                title=f"Whale: {token_symbol}",
                body=f"{snapshot.whales_detected} whale(s) detected",
                data=snapshot.to_dict(),
                priority=7,
            ))

        if snapshot.snipers_detected > 0:
            await self.alert_manager.send_alert(Alert(
                alert_type=AlertType.SNIPER,
                title=f"Sniper: {token_symbol}",
                body=f"{snapshot.snipers_detected} sniper(s) detected",
                data=snapshot.to_dict(),
                priority=6,
            ))

        self._alerts_sent += 1

    async def _consume_decisions(self):
        """Consume decisions for additional processing."""
        while self._running:
            await asyncio.sleep(1.0)

    async def stop(self):
        """Gracefully stop the entire pipeline."""
        logger.info("Shutting down Base Launch Detector...")
        self._running = False

        if self.pair_monitor:
            await self.pair_monitor.stop()
        if self.liquidity_monitor:
            await self.liquidity_monitor.stop()
        if self.momentum_engine:
            await self.momentum_engine.stop()
        if self.risk_scanner:
            await self.risk_scanner.close()

        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        uptime = time.time() - self._start_time
        logger.info("=" * 60)
        logger.info(f"📊 Final Statistics ({uptime:.0f}s uptime):")
        logger.info(f"   Pairs Detected:      {self._pairs_detected}")
        logger.info(f"   Liquidity Events:    {self._liquidity_events}")
        logger.info(f"   Risk Scans:          {self._scans_completed}")
        logger.info(f"   Momentum Snapshots:  {self._momentum_snapshots}")
        logger.info(f"   Decisions Made:      {self._decisions_made}")
        logger.info(f"   Alerts Sent:         {self._alerts_sent}")
        logger.info("=" * 60)

    def get_stats(self) -> dict:
        """Get comprehensive system statistics."""
        return {
            "uptime_seconds": time.time() - self._start_time,
            "pairs_detected": self._pairs_detected,
            "liquidity_events": self._liquidity_events,
            "scans_completed": self._scans_completed,
            "momentum_snapshots": self._momentum_snapshots,
            "decisions_made": self._decisions_made,
            "alerts_sent": self._alerts_sent,
            "components": {
                "pair_monitor": self.pair_monitor.get_stats() if self.pair_monitor else {},
                "liquidity_monitor": self.liquidity_monitor.get_stats() if self.liquidity_monitor else {},
                "momentum_engine": self.momentum_engine.get_stats() if self.momentum_engine else {},
                "risk_scanner": {"scans": self._scans_completed},
                "alert_manager": self.alert_manager.get_stats(),
            },
        }


# ── Entry Point ────────────────────────────────────────────────────

async def main():
    """Main entry point."""
    detector = BaseLaunchDetector()

    loop = asyncio.get_event_loop()

    def shutdown():
        logger.info("Received shutdown signal")
        asyncio.create_task(detector.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            pass  # Windows

    try:
        await detector.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await detector.stop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        await detector.stop()


if __name__ == "__main__":
    asyncio.run(main())
