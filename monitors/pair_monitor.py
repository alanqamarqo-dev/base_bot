"""
Pair Monitor - Main Orchestrator
=================================
Connects to Base chain via WebSocket, starts Aerodrome and Uniswap V3
factory listeners, and provides a unified stream of NewPairEvent objects.

Pipeline:
    Base RPC WS → [Aerodrome Listener + Uniswap V3 Listener]
                  → asyncio.Queue → Consumer (liquidity monitor)
"""

import asyncio
import logging
import time
from typing import Optional, AsyncIterator, Union
from dataclasses import dataclass, field

from web3 import AsyncWeb3
from web3.providers import WebSocketProvider
from web3.exceptions import Web3Exception

from config.settings import settings
from config.contracts import AERODROME_FACTORY_ADDRESS, UNISWAP_V3_FACTORY_ADDRESS
from monitors.aerodrome_factory import (
    AerodromeFactoryListener,
    AerodromePairInfo,
)
from monitors.uniswap_factory import (
    UniswapV3FactoryListener,
    UniswapV3PairInfo,
)

logger = logging.getLogger("PairMonitor")


@dataclass
class NewPairEvent:
    """
    Unified pair creation event from any DEX.
    
    This is the primary output of the Pair Monitor phase.
    """
    token_address: str
    pair_address: str
    dex: str                        # "aerodrome" | "uniswap_v3"
    base_token: str                 # WETH, USDC, cbBTC, etc.
    base_token_address: str
    pair_type: str = ""             # "stable" | "volatile" | "concentrated"
    fee: int = 0                    # UniswapV3 fee in hundredths of a bip
    tick_spacing: int = 0           # UniswapV3 only
    created_at: float = field(default_factory=time.time)
    block_number: int = 0
    tx_hash: str = ""

    @property
    def age_seconds(self) -> float:
        """Age of this pair in seconds."""
        return time.time() - self.created_at

    def to_dict(self) -> dict:
        return {
            "token_address": self.token_address,
            "pair_address": self.pair_address,
            "dex": self.dex,
            "base_token": self.base_token,
            "base_token_address": self.base_token_address,
            "pair_type": self.pair_type,
            "fee": self.fee,
            "tick_spacing": self.tick_spacing,
            "created_at": self.created_at,
            "block_number": self.block_number,
            "tx_hash": self.tx_hash,
            "age_seconds": self.age_seconds,
        }

    def __repr__(self):
        return (
            f"NewPairEvent({self.base_token}/{self.token_address[:10]}... "
            f"on {self.dex}, {self.age_seconds:.0f}s ago)"
        )


class PairMonitor:
    """
    Main pair monitor that manages Web3 connection and DEX factory listeners.
    
    Usage:
        monitor = PairMonitor()
        async for pair in monitor.stream():
            print(f"New pair: {pair}")
    """

    def __init__(self):
        self.w3: Optional[AsyncWeb3] = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._aerodrome_listener: Optional[AerodromeFactoryListener] = None
        self._uniswap_listener: Optional[UniswapV3FactoryListener] = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._pair_count: int = 0
        self._start_time: float = 0.0

    async def start(self):
        """
        Connect to Base RPC and start all factory listeners.
        Tries WebSocket first, falls back to HTTP with polling.
        """
        self._running = True
        self._start_time = time.time()

        # Connect to Base chain
        await self._connect_rpc()

        if not self.w3:
            logger.error("❌ Could not connect to Base RPC. Monitor cannot start.")
            return

        # Verify connection
        try:
            chain_id = await self.w3.eth.chain_id
            block_number = await self.w3.eth.block_number
            logger.info(
                f"✅ Connected to Base chain (ID: {chain_id}, Block: {block_number})"
            )
        except Exception as e:
            logger.error(f"Failed to verify Base connection: {e}")
            return

        # Start DEX listeners
        if settings.monitor.aerodrome:
            self._aerodrome_listener = AerodromeFactoryListener(self.w3, self.queue)
            task = asyncio.create_task(
                self._run_listener("Aerodrome", self._aerodrome_listener)
            )
            self._tasks.append(task)
            logger.info(
                f"🎧 Listening to Aerodrome Factory: "
                f"{AERODROME_FACTORY_ADDRESS[:10]}..."
            )

        if settings.monitor.uniswap_v3:
            self._uniswap_listener = UniswapV3FactoryListener(self.w3, self.queue)
            task = asyncio.create_task(
                self._run_listener("UniswapV3", self._uniswap_listener)
            )
            self._tasks.append(task)
            logger.info(
                f"🎧 Listening to Uniswap V3 Factory: "
                f"{UNISWAP_V3_FACTORY_ADDRESS[:10]}..."
            )

        logger.info("🚀 Pair Monitor started. Waiting for new pairs...")

    async def _connect_rpc(self):
        """Connect to Base RPC with fallback logic."""
        rpc = settings.rpc

        # Try WebSocket first
        for url in [rpc.ws_url, rpc.ws_fallback]:
            if not url:
                continue
            try:
                w3 = AsyncWeb3(WebSocketProvider(url))
                if await w3.is_connected():
                    self.w3 = w3
                    logger.info(f"Connected via WebSocket: {url[:50]}...")
                    return
            except Exception as e:
                logger.warning(f"WebSocket connection failed ({url[:50]}...): {e}")

        # Fallback to HTTP
        for url in [rpc.http_url, rpc.http_fallback]:
            if not url:
                continue
            try:
                from web3 import AsyncWeb3 as AWeb3
                w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(url))
                chain_id = await w3.eth.chain_id
                self.w3 = w3
                logger.warning(
                    f"⚠️  Connected via HTTP (no live subscription, polling mode): "
                    f"{url[:50]}..."
                )
                return
            except Exception as e:
                logger.warning(f"HTTP connection failed ({url[:50]}...): {e}")

    async def _run_listener(self, name: str, listener):
        """Run a factory listener with automatic restart on failure."""
        attempt = 0
        max_attempts = settings.monitor.max_reconnection_attempts

        while self._running and attempt < max_attempts:
            try:
                if attempt > 0:
                    delay = settings.monitor.reconnection_delay * (2 ** (attempt - 1))
                    delay = min(delay, 60.0)
                    logger.info(f"Restarting {name} listener in {delay:.1f}s (attempt {attempt})...")
                    await asyncio.sleep(delay)
                await listener.start()
            except Exception as e:
                attempt += 1
                logger.error(f"{name} listener error (attempt {attempt}/{max_attempts}): {e}")
            else:
                attempt = 0

        if attempt >= max_attempts:
            logger.critical(f"❌ {name} listener failed after {max_attempts} attempts. Giving up.")

    async def stream(self) -> AsyncIterator[NewPairEvent]:
        """
        Yield NewPairEvent objects as they are detected.
        
        Usage:
            async for pair_event in monitor.stream():
                process(pair_event)
        """
        while self._running:
            try:
                # Wait for next event with timeout to check running flag
                raw_pair = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                event = self._convert_event(raw_pair)
                if event:
                    self._pair_count += 1
                    yield event
            except asyncio.TimeoutError:
                continue

    def _convert_event(self, raw) -> Optional[NewPairEvent]:
        """Convert DEX-specific pair info to unified NewPairEvent."""
        if isinstance(raw, AerodromePairInfo):
            return NewPairEvent(
                token_address=raw.token_address,
                pair_address=raw.pair_address,
                dex=raw.dex,
                base_token=raw.base_token,
                base_token_address=raw.base_token_address,
                pair_type="stable" if raw.is_stable else "volatile",
                created_at=raw.created_at,
                block_number=raw.block_number,
                tx_hash=raw.tx_hash,
            )
        elif isinstance(raw, UniswapV3PairInfo):
            return NewPairEvent(
                token_address=raw.token_address,
                pair_address=raw.pair_address,
                dex=raw.dex,
                base_token=raw.base_token,
                base_token_address=raw.base_token_address,
                pair_type="concentrated",
                fee=raw.fee,
                tick_spacing=raw.tick_spacing,
                created_at=raw.created_at,
                block_number=raw.block_number,
                tx_hash=raw.tx_hash,
            )
        else:
            logger.warning(f"Unknown pair info type: {type(raw)}")
            return None

    async def get_next_pair(self, timeout: float = 30.0) -> Optional[NewPairEvent]:
        """
        Block until a new pair is detected or timeout.
        Returns None on timeout.
        """
        try:
            raw_pair = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            event = self._convert_event(raw_pair)
            if event:
                self._pair_count += 1
            return event
        except asyncio.TimeoutError:
            return None

    @property
    def pair_count(self) -> int:
        """Total pairs detected since start."""
        return self._pair_count

    @property
    def uptime_seconds(self) -> float:
        """Monitor uptime in seconds."""
        if self._start_time == 0:
            return 0
        return time.time() - self._start_time

    def get_stats(self) -> dict:
        """Return current monitor statistics."""
        return {
            "running": self._running,
            "pairs_detected": self._pair_count,
            "uptime_seconds": self.uptime_seconds,
            "listeners": {
                "aerodrome": self._aerodrome_listener is not None,
                "uniswap_v3": self._uniswap_listener is not None,
            },
        }

    async def stop(self):
        """Gracefully stop all listeners and clean up."""
        logger.info("Stopping Pair Monitor...")
        self._running = False

        # Stop listeners
        if self._aerodrome_listener:
            await self._aerodrome_listener.stop()
        if self._uniswap_listener:
            await self._uniswap_listener.stop()

        # Cancel tasks
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        logger.info(f"Pair Monitor stopped. Total pairs: {self._pair_count}")
