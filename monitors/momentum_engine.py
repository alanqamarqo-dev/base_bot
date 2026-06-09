"""
Momentum Engine - Phase 4
===========================
After 5 minutes from launch, analyzes trading activity:
- Buy/Sell count
- Volume tracking
- Unique buyers
- Buy/Sell ratio
- Whale detection
- Smart Money detection
- Sniper detection

Uses Swap events from the pair contract to track all trades.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Set, List
from dataclasses import dataclass, field
from collections import defaultdict

from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from config.settings import settings
from config.contracts import (
    AERODROME_POOL_ABI,
    AERODROME_SWAP_TOPIC,
    UNISWAP_V3_SWAP_TOPIC,
    get_base_token_symbol,
)
from monitors.pair_monitor import NewPairEvent
from monitors.liquidity_monitor import TrackedPair, LiquidityEvent

logger = logging.getLogger("MomentumEngine")


# ── Momentum Data Structures ──────────────────────────────────────

@dataclass
class TradeRecord:
    """A single trade (swap) on a pair."""
    tx_hash: str
    buyer: str
    seller: str = ""
    amount_in: float = 0.0
    amount_out: float = 0.0
    is_buy: bool = True       # True if buying the token
    block_number: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MomentumSnapshot:
    """Complete momentum analysis at a point in time."""
    token_address: str
    token_symbol: str = ""
    pair_address: str = ""
    base_token: str = ""
    dex: str = ""

    # Time-based metrics
    age_seconds: float = 0.0
    snapshot_at: float = field(default_factory=time.time)

    # Trading metrics
    buy_count_5m: int = 0
    sell_count_5m: int = 0
    buy_count_15m: int = 0
    sell_count_15m: int = 0
    buy_count_1h: int = 0
    sell_count_1h: int = 0

    volume_5m_usd: float = 0.0
    volume_15m_usd: float = 0.0
    volume_1h_usd: float = 0.0

    unique_buyers: int = 0
    buy_sell_ratio: float = 0.0

    # Liquidity
    current_liquidity_usd: float = 0.0
    peak_liquidity_usd: float = 0.0
    liquidity_change_pct: float = 0.0

    # Detection
    whales_detected: int = 0
    whale_dominance_pct: float = 0.0
    smart_money_detected: bool = False
    smart_money_wallets: List[str] = field(default_factory=list)
    snipers_detected: int = 0
    bot_activity_detected: bool = False

    # Trades
    recent_trades: List[TradeRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "pair_address": self.pair_address,
            "base_token": self.base_token,
            "dex": self.dex,
            "age_seconds": self.age_seconds,
            "snapshot_at": self.snapshot_at,
            "buy_count_5m": self.buy_count_5m,
            "sell_count_5m": self.sell_count_5m,
            "buy_count_15m": self.buy_count_15m,
            "sell_count_15m": self.sell_count_15m,
            "buy_count_1h": self.buy_count_1h,
            "sell_count_1h": self.sell_count_1h,
            "volume_5m_usd": self.volume_5m_usd,
            "volume_15m_usd": self.volume_15m_usd,
            "volume_1h_usd": self.volume_1h_usd,
            "unique_buyers": self.unique_buyers,
            "buy_sell_ratio": self.buy_sell_ratio,
            "current_liquidity_usd": self.current_liquidity_usd,
            "peak_liquidity_usd": self.peak_liquidity_usd,
            "liquidity_change_pct": self.liquidity_change_pct,
            "whales_detected": self.whales_detected,
            "whale_dominance_pct": self.whale_dominance_pct,
            "smart_money_detected": self.smart_money_detected,
            "smart_money_wallets": self.smart_money_wallets,
            "snipers_detected": self.snipers_detected,
            "bot_activity_detected": self.bot_activity_detected,
        }


class MomentumEngine:
    """
    Tracks trading momentum for new pairs.

    For each pair that gets liquidity:
    1. Subscribe to Swap events
    2. Track buy/sell counts and volumes
    3. After 5 minutes, calculate momentum snapshot
    4. Detect whales, smart money, snipers
    5. Push MomentumSnapshot to output queue
    """

    def __init__(
        self,
        w3: AsyncWeb3,
        liquidity_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
    ):
        self.w3 = w3
        self.liquidity_queue = liquidity_queue
        self.output_queue = output_queue
        self._running = False
        self._tracked_tokens: Dict[str, Dict[str, Any]] = {}
        self._tasks: list = []
        self._known_wallets: Set[str] = set()  # Smart money addresses
        self._load_known_wallets()

    def _load_known_wallets(self):
        """Load known smart money / sniper wallet addresses."""
        # These would be loaded from config/known_wallets.py in production
        # For now, we have a minimal set
        self._known_wallets = set()

    async def start(self):
        """Start the momentum engine."""
        self._running = True
        logger.info("📊 Momentum Engine started. Waiting for liquidity events...")

        consumer_task = asyncio.create_task(self._consume_liquidity_events())
        self._tasks.append(consumer_task)

    async def _consume_liquidity_events(self):
        """Consume liquidity events and start tracking momentum."""
        while self._running:
            try:
                event = await asyncio.wait_for(self.liquidity_queue.get(), timeout=5.0)
                if isinstance(event, LiquidityEvent):
                    await self._start_tracking(event)
            except asyncio.TimeoutError:
                continue

    async def _start_tracking(self, event: LiquidityEvent):
        """Start tracking trades for a pair that just got liquidity."""
        token_key = event.token_address.lower()

        if token_key in self._tracked_tokens:
            return  # Already tracking

        tracker = {
            "token_address": event.token_address,
            "pair_address": event.pair_address,
            "base_token": event.base_token,
            "dex": "",  # Will be filled
            "start_time": time.time(),
            "trades": [],
            "buyers": set(),
            "sellers": set(),
            "buy_count": 0,
            "sell_count": 0,
            "volume_usd": 0.0,
            "first_trade_at": None,
            "whale_buys": [],
            "smart_money_buys": [],
            "snipers_found": 0,
        }

        self._tracked_tokens[token_key] = tracker

        logger.info(
            f"📊 Tracking momentum for {event.base_token}/{event.token_address[:10]}..."
        )

        # Schedule momentum check after 5 minutes
        asyncio.create_task(self._schedule_momentum_check(token_key))

        # Start listening to swaps
        asyncio.create_task(self._listen_swaps(token_key, event.pair_address))

    async def _listen_swaps(self, token_key: str, pair_address: str):
        """Listen for Swap events on a specific pair."""
        tracker = self._tracked_tokens.get(token_key)
        if not tracker:
            return

        # Determine which swap topic to use
        # Both Aerodrome and UniswapV3 use the same Swap event signature
        swap_topic = AERODROME_SWAP_TOPIC  # Same as UNISWAP_V3_SWAP_TOPIC

        filter_params = {
            "address": pair_address,
            "topics": [swap_topic],
        }

        try:
            sub_id = await self.w3.eth.subscribe("logs", filter_params)

            while self._running and token_key in self._tracked_tokens:
                try:
                    log = await asyncio.wait_for(
                        self.w3.eth.get_subscription_message(sub_id),
                        timeout=30.0,
                    )
                    await self._handle_swap(log, tracker)
                except asyncio.TimeoutError:
                    continue
                except Web3Exception:
                    await asyncio.sleep(1.0)
        except Exception as e:
            logger.warning(f"Failed to subscribe to swaps on {pair_address[:10]}...: {e}")
            # Fallback polling
            await self._poll_swaps(pair_address, tracker)

    async def _poll_swaps(self, pair_address: str, tracker: dict):
        """Fallback polling for swap events."""
        last_block = await self.w3.eth.block_number
        while self._running and tracker["token_address"].lower() in self._tracked_tokens:
            try:
                current_block = await self.w3.eth.block_number
                if current_block > last_block:
                    logs = await self.w3.eth.get_logs({
                        "address": pair_address,
                        "fromBlock": last_block + 1,
                        "toBlock": current_block,
                    })
                    for log in logs:
                        await self._handle_swap(log, tracker)
                    last_block = current_block
            except Exception as e:
                logger.warning(f"Swap poll error: {e}")
            await asyncio.sleep(2.0)

    async def _handle_swap(self, log: Dict[str, Any], tracker: dict):
        """Parse a Swap event and update momentum tracking."""
        try:
            topics = log.get("topics", [])
            data = log.get("data", "0x")

            if isinstance(data, bytes):
                data = data.hex()

            # Swap event: sender, to, amount0In, amount1In, amount0Out, amount1Out
            # For Aerodrome/UniswapV3 pools:
            # amount0In > 0 means buying token0, amount1In > 0 means buying token1

            sender = self._topic_to_address(topics[1]) if len(topics) > 1 else ""
            to = self._topic_to_address(topics[2]) if len(topics) > 2 else ""

            # Decode amounts
            if data.startswith("0x"):
                data = data[2:]
            if len(data) < 256:
                return

            amount0_in = int(data[:64], 16)
            amount1_in = int(data[64:128], 16)
            amount0_out = int(data[128:192], 16)
            amount1_out = int(data[192:256], 16)

            # Determine if this is a buy or sell of the token
            # If amount0_in > 0, they're buying token0 (selling token1/base)
            # If amount1_in > 0, they're buying token1 (selling token0)
            # We track buys of the NEW token
            is_buy = amount0_in > 0  # Simplified: buying token0 = buying the new token

            # Estimate USD value
            volume_usd = (amount1_in + amount1_out) / 1e18  # Rough ETH estimate

            trade = TradeRecord(
                tx_hash=log.get("transactionHash", ""),
                buyer=to if is_buy else sender,
                seller=sender if is_buy else to,
                amount_in=amount0_in if is_buy else amount1_in,
                amount_out=amount0_out if is_buy else amount1_out,
                is_buy=is_buy,
                block_number=log.get("blockNumber", 0),
            )

            tracker["trades"].append(trade)

            if is_buy:
                tracker["buy_count"] += 1
                tracker["buyers"].add(trade.buyer)
                tracker["volume_usd"] += volume_usd

                # Check for smart money
                if trade.buyer.lower() in self._known_wallets:
                    tracker["smart_money_buys"].append(trade.buyer)

                # Check for sniper (bought in first 3 blocks)
                if not tracker["first_trade_at"]:
                    tracker["first_trade_at"] = time.time()
                elif time.time() - tracker["first_trade_at"] < 15:  # ~3 blocks
                    tracker["snipers_found"] += 1

            else:
                tracker["sell_count"] += 1
                tracker["sellers"].add(trade.seller)

        except Exception as e:
            logger.error(f"Error handling swap: {e}")

    async def _schedule_momentum_check(self, token_key: str):
        """After 5 minutes, calculate momentum snapshot."""
        await asyncio.sleep(settings.monitor.momentum_check_after_seconds)

        tracker = self._tracked_tokens.get(token_key)
        if not tracker:
            return

        snapshot = await self._calculate_momentum(tracker)
        if snapshot:
            await self.output_queue.put(snapshot)
            logger.info(
                f"📊 Momentum snapshot for {snapshot.token_symbol or token_key[:10]}: "
                f"Buys:{snapshot.buy_count_5m} Sells:{snapshot.sell_count_5m} "
                f"Vol:${snapshot.volume_5m_usd:,.0f} "
                f"Ratio:{snapshot.buy_sell_ratio:.1f}x"
            )

    async def _calculate_momentum(self, tracker: dict) -> Optional[MomentumSnapshot]:
        """Calculate the momentum snapshot from tracked data."""
        now = time.time()
        age = now - tracker["start_time"]

        trades = tracker["trades"]

        # Time-windowed metrics
        buy_5m = sum(1 for t in trades if t.is_buy and (now - t.timestamp) <= 300)
        sell_5m = sum(1 for t in trades if not t.is_buy and (now - t.timestamp) <= 300)
        buy_15m = sum(1 for t in trades if t.is_buy and (now - t.timestamp) <= 900)
        sell_15m = sum(1 for t in trades if not t.is_buy and (now - t.timestamp) <= 900)
        buy_1h = sum(1 for t in trades if t.is_buy and (now - t.timestamp) <= 3600)
        sell_1h = sum(1 for t in trades if not t.is_buy and (now - t.timestamp) <= 3600)

        # Volume
        vol_5m = sum(
            (t.amount_in + t.amount_out) / 1e18
            for t in trades
            if (now - t.timestamp) <= 300
        )
        vol_15m = sum(
            (t.amount_in + t.amount_out) / 1e18
            for t in trades
            if (now - t.timestamp) <= 900
        )
        vol_1h = sum(
            (t.amount_in + t.amount_out) / 1e18
            for t in trades
            if (now - t.timestamp) <= 3600
        )

        # Unique buyers
        unique_buyers = len(tracker["buyers"])

        # Buy/Sell ratio
        total_buys = buy_5m
        total_sells = sell_5m
        ratio = total_buys / max(total_sells, 1)

        # Whale detection
        whale_count = len(tracker.get("whale_buys", []))
        whale_pct = 0.0

        # Smart money
        smart_money = len(tracker.get("smart_money_buys", [])) > 0
        smart_wallets = tracker.get("smart_money_buys", [])

        # Snipers
        snipers = tracker.get("snipers_found", 0)

        # Bot detection: many buys from many addresses in short time
        bot_activity = unique_buyers > 10 and (buy_5m / max(age, 1)) > 2

        snapshot = MomentumSnapshot(
            token_address=tracker["token_address"],
            pair_address=tracker["pair_address"],
            base_token=tracker["base_token"],
            dex=tracker.get("dex", ""),
            age_seconds=age,
            buy_count_5m=buy_5m,
            sell_count_5m=sell_5m,
            buy_count_15m=buy_15m,
            sell_count_15m=sell_15m,
            buy_count_1h=buy_1h,
            sell_count_1h=sell_1h,
            volume_5m_usd=vol_5m,
            volume_15m_usd=vol_15m,
            volume_1h_usd=vol_1h,
            unique_buyers=unique_buyers,
            buy_sell_ratio=ratio,
            whales_detected=whale_count,
            whale_dominance_pct=whale_pct,
            smart_money_detected=smart_money,
            smart_money_wallets=smart_wallets,
            snipers_detected=snipers,
            bot_activity_detected=bot_activity,
            recent_trades=trades[-20:],  # Last 20 trades
        )

        return snapshot

    @staticmethod
    def _topic_to_address(topic) -> str:
        """Extract address from event topic."""
        if isinstance(topic, bytes):
            topic = topic.hex()
        topic_str = str(topic)
        if topic_str.startswith("0x"):
            return "0x" + topic_str[-40:]
        return "0x" + topic_str[-40:]

    async def stop(self):
        """Stop the momentum engine."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Momentum Engine stopped")

    @property
    def tracked_count(self) -> int:
        """Number of tokens being tracked."""
        return len(self._tracked_tokens)

    def get_stats(self) -> dict:
        """Return current engine statistics."""
        return {
            "tracked_tokens": self.tracked_count,
            "known_wallets": len(self._known_wallets),
        }