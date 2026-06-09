"""
Liquidity Monitor - Phase 2
=============================
After a pair is created, watches for liquidity events:
- Mint (liquidity added)
- Burn (liquidity removed)
- Swap (trading activity)

Tracks liquidity levels and classifies them:
  MICRO:  < $1,000
  LOW:    $1,000 - $5,000
  MEDIUM: $5,000 - $20,000
  HIGH:   $20,000 - $100,000
  WHALE:  > $100,000

Also detects:
- Liquidity removal (potential rug pull)
- Liquidity increase (confidence signal)
- First liquidity event (pair becomes tradeable)
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from config.settings import settings
from config.contracts import (
    AERODROME_POOL_ABI,
    UNISWAP_V3_POOL_ABI,
    AERODROME_MINT_TOPIC,
    AERODROME_BURN_TOPIC,
    AERODROME_SWAP_TOPIC,
    UNISWAP_V3_MINT_TOPIC,
    UNISWAP_V3_BURN_TOPIC,
    UNISWAP_V3_SWAP_TOPIC,
    ERC20_ABI,
    get_base_token_symbol,
    is_known_base_token,
)
from monitors.pair_monitor import NewPairEvent

logger = logging.getLogger("LiquidityMonitor")


# ── Liquidity Classification ──────────────────────────────────────

class LiquidityLevel(Enum):
    MICRO = "micro"       # < $1,000
    LOW = "low"           # $1,000 - $5,000
    MEDIUM = "medium"     # $5,000 - $20,000
    HIGH = "high"         # $20,000 - $100,000
    WHALE = "whale"       # > $100,000

    @classmethod
    def from_usd(cls, amount_usd: float) -> "LiquidityLevel":
        if amount_usd < 1_000:
            return cls.MICRO
        elif amount_usd < 5_000:
            return cls.LOW
        elif amount_usd < 20_000:
            return cls.MEDIUM
        elif amount_usd < 100_000:
            return cls.HIGH
        else:
            return cls.WHALE

    @property
    def emoji(self) -> str:
        return {
            "micro": "🔸",
            "low": "🔹",
            "medium": "�",
            "high": "💎",
            "whale": "🐋",
        }.get(self.value, "❓")

    @property
    def label(self) -> str:
        return {
            "micro": "Micro (<$1k)",
            "low": "Low ($1k-$5k)",
            "medium": "Medium ($5k-$20k)",
            "high": "High ($20k-$100k)",
            "whale": "Whale (>$100k)",
        }.get(self.value, "Unknown")


# ── Event Types ───────────────────────────────────────────────────

class LiquidityEventType(Enum):
    MINT = "mint"               # Liquidity added
    BURN = "burn"               # Liquidity removed
    SWAP = "swap"               # Trade executed
    INITIAL_LIQUIDITY = "initial"  # First liquidity event
    LIQUIDITY_INCREASED = "increased"
    LIQUIDITY_REMOVED = "removed"


@dataclass
class LiquidityEvent:
    """A single liquidity-related event on a pair."""
    token_address: str
    pair_address: str
    base_token: str
    event_type: LiquidityEventType
    amount0: float = 0.0
    amount1: float = 0.0
    liquidity_usd: float = 0.0
    previous_liquidity_usd: float = 0.0
    liquidity_change_pct: float = 0.0
    block_number: int = 0
    tx_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    sender: str = ""
    to: str = ""

    def to_dict(self) -> dict:
        return {
            "token_address": self.token_address,
            "pair_address": self.pair_address,
            "base_token": self.base_token,
            "event_type": self.event_type.value,
            "amount0": self.amount0,
            "amount1": self.amount1,
            "liquidity_usd": self.liquidity_usd,
            "previous_liquidity_usd": self.previous_liquidity_usd,
            "liquidity_change_pct": self.liquidity_change_pct,
            "block_number": self.block_number,
            "tx_hash": self.tx_hash,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "to": self.to,
        }

    @property
    def is_positive(self) -> bool:
        """Whether this is a positive liquidity signal."""
        return self.event_type in (
            LiquidityEventType.MINT,
            LiquidityEventType.INITIAL_LIQUIDITY,
            LiquidityEventType.LIQUIDITY_INCREASED,
        )

    @property
    def is_negative(self) -> bool:
        """Whether this is a negative liquidity signal."""
        return self.event_type in (
            LiquidityEventType.BURN,
            LiquidityEventType.LIQUIDITY_REMOVED,
        )

    @property
    def level(self) -> LiquidityLevel:
        return LiquidityLevel.from_usd(self.liquidity_usd)


@dataclass
class TrackedPair:
    """State for a pair being watched for liquidity."""
    token_address: str
    pair_address: str
    base_token: str
    base_token_address: str
    dex: str
    created_at: float
    first_liquidity_at: Optional[float] = None
    current_liquidity_usd: float = 0.0
    peak_liquidity_usd: float = 0.0
    has_liquidity: bool = False
    liquidity_events_count: int = 0
    swap_count: int = 0
    last_event_at: float = 0.0
    token_symbol: str = ""
    token_name: str = ""
    token_decimals: int = 18
    base_decimals: int = 18


class LiquidityMonitor:
    """
    Watches newly created pairs for liquidity events.
    
    For each new pair:
    1. Subscribe to Mint/Burn/Swap events
    2. Track liquidity levels over time
    3. Detect significant changes (adds, removals)
    4. Emit LiquidityEvent when liquidity is detected
    """

    def __init__(
        self,
        w3: AsyncWeb3,
        pair_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
    ):
        self.w3 = w3
        self.pair_queue = pair_queue
        self.output_queue = output_queue
        self._running = False
        self._watched_pairs: Dict[str, TrackedPair] = {}
        self._tasks: list[asyncio.Task] = []
        self._liquidity_count: int = 0

    async def start(self):
        """Start watching for new pairs and their liquidity."""
        self._running = True
        logger.info("💧 Liquidity Monitor started. Waiting for new pairs...")

        # Main loop: consume new pairs from pair_queue
        consumer_task = asyncio.create_task(self._consume_new_pairs())
        self._tasks.append(consumer_task)

    async def _consume_new_pairs(self):
        """Continuously consume new pairs and start watching them."""
        while self._running:
            try:
                event = await asyncio.wait_for(self.pair_queue.get(), timeout=5.0)
                if isinstance(event, NewPairEvent):
                    await self._watch_pair(event)
            except asyncio.TimeoutError:
                continue

    async def _watch_pair(self, event: NewPairEvent):
        """Start watching a specific pair for liquidity events."""
        pair_key = event.pair_address.lower()

        if pair_key in self._watched_pairs:
            return  # Already watching

        # Fetch token metadata
        token_symbol, token_name, token_decimals = await self._fetch_token_metadata(
            event.token_address
        )
        base_decimals = await self._fetch_decimals(event.base_token_address)

        tracked = TrackedPair(
            token_address=event.token_address,
            pair_address=event.pair_address,
            base_token=event.base_token,
            base_token_address=event.base_token_address,
            dex=event.dex,
            created_at=event.created_at,
            token_symbol=token_symbol,
            token_name=token_name,
            token_decimals=token_decimals,
            base_decimals=base_decimals,
        )

        self._watched_pairs[pair_key] = tracked

        logger.info(
            f"👀 Watching pair: {tracked.base_token}/{tracked.token_symbol or event.token_address[:10]}... "
            f"({event.dex})"
        )

        # Start event listener for this pair
        task = asyncio.create_task(self._listen_pair_events(pair_key))
        self._tasks.append(task)

    async def _listen_pair_events(self, pair_key: str):
        """Listen for Mint/Burn/Swap events on a specific pair."""
        tracked = self._watched_pairs.get(pair_key)
        if not tracked:
            return

        pair_address = tracked.pair_address

        # Determine which ABI to use
        if tracked.dex == "aerodrome":
            pool_abi = AERODROME_POOL_ABI
            mint_topic = AERODROME_MINT_TOPIC
            burn_topic = AERODROME_BURN_TOPIC
            swap_topic = AERODROME_SWAP_TOPIC
        else:
            pool_abi = UNISWAP_V3_POOL_ABI
            mint_topic = UNISWAP_V3_MINT_TOPIC
            burn_topic = UNISWAP_V3_BURN_TOPIC
            swap_topic = UNISWAP_V3_SWAP_TOPIC

        # Subscribe to all relevant events
        filter_params = {
            "address": pair_address,
            "topics": [[mint_topic, burn_topic, swap_topic]],
        }

        try:
            sub_id = await self.w3.eth.subscribe("logs", filter_params)
            logger.debug(f"Subscribed to events on {pair_address[:10]}... (id: {sub_id})")

            while self._running and pair_key in self._watched_pairs:
                try:
                    log = await asyncio.wait_for(
                        self.w3.eth.get_subscription_message(sub_id),
                        timeout=30.0,
                    )
                    await self._handle_pair_log(log, tracked)
                except asyncio.TimeoutError:
                    continue
                except Web3Exception:
                    await asyncio.sleep(1.0)
        except Exception as e:
            logger.warning(f"Failed to subscribe to pair {pair_address[:10]}...: {e}")
            # Fallback: poll getLogs
            await self._poll_pair_events(pair_address, tracked)

    async def _poll_pair_events(self, pair_address: str, tracked: TrackedPair):
        """Fallback polling for pair events."""
        last_block = await self.w3.eth.block_number
        while self._running and tracked.pair_address.lower() in self._watched_pairs:
            try:
                current_block = await self.w3.eth.block_number
                if current_block > last_block:
                    logs = await self.w3.eth.get_logs({
                        "address": pair_address,
                        "fromBlock": last_block + 1,
                        "toBlock": current_block,
                    })
                    for log in logs:
                        await self._handle_pair_log(log, tracked)
                    last_block = current_block
            except Exception as e:
                logger.warning(f"Poll error for {pair_address[:10]}...: {e}")
            await asyncio.sleep(2.0)

    async def _handle_pair_log(self, log: Dict[str, Any], tracked: TrackedPair):
        """Parse a log event from a watched pair."""
        try:
            topics = log.get("topics", [])
            if not topics:
                return

            event_topic = topics[0].hex() if hasattr(topics[0], "hex") else str(topics[0])

            # Determine event type
            if event_topic == AERODROME_MINT_TOPIC or event_topic == UNISWAP_V3_MINT_TOPIC:
                event_type = LiquidityEventType.MINT
            elif event_topic == AERODROME_BURN_TOPIC or event_topic == UNISWAP_V3_BURN_TOPIC:
                event_type = LiquidityEventType.BURN
            elif event_topic == AERODROME_SWAP_TOPIC or event_topic == UNISWAP_V3_SWAP_TOPIC:
                event_type = LiquidityEventType.SWAP
                tracked.swap_count += 1
            else:
                return

            # Parse amounts from data
            data = log.get("data", "0x")
            if isinstance(data, bytes):
                data = data.hex()

            amount0, amount1 = self._decode_amounts(data, tracked)

            # Calculate USD value (approximate)
            liquidity_usd = self._estimate_usd(amount0, amount1, tracked)

            # Determine if this is the first liquidity event
            if not tracked.has_liquidity and event_type == LiquidityEventType.MINT:
                event_type = LiquidityEventType.INITIAL_LIQUIDITY
                tracked.first_liquidity_at = time.time()
                tracked.has_liquidity = True
                logger.info(
                    f"🟢 FIRST LIQUIDITY: {tracked.base_token}/{tracked.token_symbol} "
                    f"on {tracked.dex} — ${liquidity_usd:,.0f}"
                )

            # Track changes
            prev_liquidity = tracked.current_liquidity_usd
            change_pct = 0.0
            if prev_liquidity > 0:
                change_pct = ((liquidity_usd - prev_liquidity) / prev_liquidity) * 100

            # Update tracked state
            if event_type in (LiquidityEventType.MINT, LiquidityEventType.INITIAL_LIQUIDITY):
                tracked.current_liquidity_usd = max(tracked.current_liquidity_usd, liquidity_usd)
                if liquidity_usd > tracked.peak_liquidity_usd:
                    tracked.peak_liquidity_usd = liquidity_usd
            elif event_type == LiquidityEventType.BURN:
                tracked.current_liquidity_usd = max(0, tracked.current_liquidity_usd - liquidity_usd)

            tracked.liquidity_events_count += 1
            tracked.last_event_at = time.time()

            # Detect significant changes
            if event_type == LiquidityEventType.BURN and change_pct < -50:
                event_type = LiquidityEventType.LIQUIDITY_REMOVED
                logger.warning(
                    f"🚨 LIQUIDITY REMOVED: {tracked.base_token}/{tracked.token_symbol} "
                    f"${prev_liquidity:,.0f} → ${liquidity_usd:,.0f} ({change_pct:.1f}%)"
                )
            elif change_pct > 100:
                event_type = LiquidityEventType.LIQUIDITY_INCREASED

            # Build event
            liq_event = LiquidityEvent(
                token_address=tracked.token_address,
                pair_address=tracked.pair_address,
                base_token=tracked.base_token,
                event_type=event_type,
                amount0=amount0,
                amount1=amount1,
                liquidity_usd=liquidity_usd,
                previous_liquidity_usd=prev_liquidity,
                liquidity_change_pct=change_pct,
                block_number=log.get("blockNumber", 0),
                tx_hash=log.get("transactionHash", ""),
                sender=self._topic_to_address(topics[1]) if len(topics) > 1 else "",
                to=self._topic_to_address(topics[2]) if len(topics) > 2 else "",
            )

            # Push to output queue
            await self.output_queue.put(liq_event)
            self._liquidity_count += 1

        except Exception as e:
            logger.error(f"Error handling pair log: {e}")

    async def _fetch_token_metadata(self, token_address: str) -> tuple:
        """Fetch token symbol, name, and decimals."""
        try:
            contract = self.w3.eth.contract(address=token_address, abi=ERC20_ABI)
            symbol = await contract.functions.symbol().call()
            name = await contract.functions.name().call()
            decimals = await contract.functions.decimals().call()
            return symbol, name, decimals
        except Exception:
            return "", "", 18

    async def _fetch_decimals(self, address: str) -> int:
        """Fetch decimals for a token address."""
        try:
            contract = self.w3.eth.contract(address=address, abi=ERC20_ABI)
            return await contract.functions.decimals().call()
        except Exception:
            return 18

    def _decode_amounts(self, data: str, tracked: TrackedPair) -> tuple:
        """Decode amount0 and amount1 from event data."""
        try:
            if isinstance(data, bytes):
                data = data.hex()
            if data.startswith("0x"):
                data = data[2:]
            if len(data) < 128:
                return 0.0, 0.0

            # First two 32-byte words are amount0 and amount1
            amount0_raw = int(data[:64], 16)
            amount1_raw = int(data[64:128], 16)

            amount0 = amount0_raw / (10 ** tracked.token_decimals)
            amount1 = amount1_raw / (10 ** tracked.base_decimals)
            return amount0, amount1
        except Exception:
            return 0.0, 0.0

    def _estimate_usd(self, amount0: float, amount1: float, tracked: TrackedPair) -> float:
        """Estimate USD value of liquidity. Uses base token as reference."""
        # If base is WETH, use approximate ETH price
        if tracked.base_token in ("WETH", "BRIDGED_ETH"):
            eth_price = 3000.0  # Approximate; in production, use oracle
            return amount1 * eth_price
        # If base is USDC/USDbC/USDT/DAI, it's ~$1
        elif tracked.base_token in ("USDC", "USDbC", "USDT", "DAI"):
            return amount1
        # Otherwise, use the larger of the two as estimate
        return max(amount0, amount1)

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
        """Stop the liquidity monitor."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info(f"Liquidity Monitor stopped. Events: {self._liquidity_count}")

    @property
    def watched_count(self) -> int:
        """Number of pairs currently being watched."""
        return len(self._watched_pairs)

    @property
    def liquidity_count(self) -> int:
        """Total liquidity events detected."""
        return self._liquidity_count

    def get_stats(self) -> dict:
        """Return current monitor statistics."""
        return {
            "watched_pairs": self.watched_count,
            "liquidity_events": self._liquidity_count,
            "pairs_with_liquidity": sum(
                1 for p in self._watched_pairs.values() if p.has_liquidity
            ),
        }