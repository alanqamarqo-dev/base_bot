"""
Uniswap V3 Factory Event Listener
==================================
Listens for PoolCreated events from Uniswap V3 Factory
on Base chain via WebSocket subscription.

Factory: 0x33128a8fC17869897dcE68Ed026d694621f6FDfD
Event: PoolCreated(token0, token1, fee, tickSpacing, pool)
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from config.settings import settings
from config.contracts import (
    UNISWAP_V3_FACTORY_ADDRESS,
    UNISWAP_V3_FACTORY_ABI,
    UNISWAP_V3_POOL_CREATED_TOPIC,
    get_base_token_symbol,
    is_known_base_token,
)

logger = logging.getLogger("UniswapV3Factory")


@dataclass
class UniswapV3PairInfo:
    """Parsed UniswapV3 PoolCreated event data."""
    token_address: str
    pair_address: str
    base_token: str
    base_token_address: str
    fee: int               # e.g., 500 = 0.05%, 3000 = 0.3%
    tick_spacing: int
    dex: str = "uniswap_v3"
    created_at: float = 0.0
    block_number: int = 0
    tx_hash: str = ""


class UniswapV3FactoryListener:
    """
    Subscribes to Uniswap V3 Factory PoolCreated events via WebSocket.
    Handles reconnection and fallback to polling.
    """

    def __init__(self, w3: AsyncWeb3, queue: asyncio.Queue):
        self.w3 = w3
        self.queue = queue
        self.factory_address = UNISWAP_V3_FACTORY_ADDRESS
        self._running = False
        self._subscription_id: Optional[str] = None
        self._last_processed_block: int = 0

    async def start(self):
        """Start listening for UniswapV3 PoolCreated events."""
        self._running = True
        logger.info(
            f"🎧 Uniswap V3 Factory listener starting on {self.factory_address[:10]}..."
        )

        # Backfill recent blocks
        current_block = await self.w3.eth.block_number
        backfill_from = max(current_block - 500, self._last_processed_block or current_block - 500)

        if backfill_from < current_block:
            logger.info(
                f"Backfilling UniswapV3 events from block {backfill_from} to {current_block}"
            )
            await self._backfill_events(backfill_from, current_block)

        self._last_processed_block = current_block

        # Try WebSocket subscription, fallback to polling
        try:
            await self._subscribe_live()
        except Exception as e:
            logger.error(f"UniswapV3 WebSocket subscription failed: {e}")
            await self._poll_loop()

    async def _subscribe_live(self):
        """Set up WebSocket log subscription."""
        filter_params = {
            "address": self.factory_address,
            "topics": [UNISWAP_V3_POOL_CREATED_TOPIC],
        }
        try:
            self._subscription_id = await self.w3.eth.subscribe("logs", filter_params)
            logger.info(f"UniswapV3 subscription active: {self._subscription_id}")

            while self._running:
                try:
                    event = await asyncio.wait_for(
                        self.w3.eth.get_subscription_message(self._subscription_id),
                        timeout=30.0,
                    )
                    await self._handle_log(event)
                except asyncio.TimeoutError:
                    continue
                except Web3Exception as e:
                    logger.warning(f"UniswapV3 subscription error: {e}, retrying...")
                    await asyncio.sleep(settings.monitor.reconnection_delay)
        except Exception as e:
            logger.error(f"Failed to subscribe UniswapV3: {e}")
            raise

    async def _poll_loop(self):
        """Fallback polling mode."""
        logger.info("Switched to polling mode for UniswapV3")
        while self._running:
            try:
                current_block = await self.w3.eth.block_number
                if current_block > self._last_processed_block:
                    await self._backfill_events(
                        self._last_processed_block + 1,
                        current_block,
                    )
                    self._last_processed_block = current_block
            except Exception as e:
                logger.warning(f"UniswapV3 poll error: {e}")
            await asyncio.sleep(2.0)

    async def _backfill_events(self, from_block: int, to_block: int):
        """Fetch historical PoolCreated events."""
        try:
            logs = await self.w3.eth.get_logs({
                "address": self.factory_address,
                "topics": [UNISWAP_V3_POOL_CREATED_TOPIC],
                "fromBlock": from_block,
                "toBlock": to_block,
            })
            for log in logs:
                await self._handle_log(log)
            if logs:
                logger.info(f"Backfilled {len(logs)} UniswapV3 events from blocks {from_block}-{to_block}")
        except Exception as e:
            logger.warning(f"UniswapV3 backfill error: {e}")

    async def _handle_log(self, log: Dict[str, Any]):
        """Parse a UniswapV3 PoolCreated log and enqueue."""
        try:
            # UniswapV3 PoolCreated event layout:
            # topics[0]: event signature
            # topics[1]: indexed token0 (address)
            # topics[2]: indexed token1 (address)
            # topics[3]: indexed fee (uint24)
            # data: tickSpacing (int24), pool (address)

            topics = log.get("topics", [])
            data = log.get("data", "0x")

            if len(topics) < 4:
                return

            token0 = self._topic_to_address(topics[1])
            token1 = self._topic_to_address(topics[2])
            fee = int(topics[3], 16)

            # Parse data: first 32 bytes = tickSpacing, second 32 bytes = pool
            tick_spacing, pool_address = self._decode_uniswap_v3_data(data)

            if not pool_address:
                logger.warning("Could not decode UniswapV3 pool address")
                return

            # Determine base token vs new token
            base_token_address = ""
            token_address = ""

            if is_known_base_token(token0):
                base_token_address = token0
                token_address = token1
            elif is_known_base_token(token1):
                base_token_address = token1
                token_address = token0
            else:
                base_token_address = token0
                token_address = token1

            base_token = get_base_token_symbol(base_token_address)

            pair_info = UniswapV3PairInfo(
                token_address=token_address.lower(),
                pair_address=pool_address.lower(),
                base_token=base_token,
                base_token_address=base_token_address.lower(),
                fee=fee,
                tick_spacing=tick_spacing,
                created_at=time.time(),
                block_number=log.get("blockNumber", 0),
                tx_hash=log.get("transactionHash", ""),
            )

            await self.queue.put(pair_info)

            logger.info(
                f"🟣 UniswapV3: {pair_info.base_token}/{token_address[:10]}... "
                f"(pool: {pool_address[:10]}..., fee: {fee/10000:.2f}%)"
            )

        except Exception as e:
            logger.error(f"Error handling UniswapV3 log: {e}")

    async def stop(self):
        """Stop the listener."""
        self._running = False
        if self._subscription_id:
            try:
                await self.w3.eth.unsubscribe(self._subscription_id)
            except Exception:
                pass
            self._subscription_id = None
        logger.info("UniswapV3 Factory listener stopped")

    @staticmethod
    def _topic_to_address(topic: str) -> str:
        """Extract address from event topic."""
        if topic.startswith("0x"):
            return "0x" + topic[-40:]
        return "0x" + topic[-40:]

    @staticmethod
    def _decode_uniswap_v3_data(data: str) -> tuple:
        """
        Decode UniswapV3 PoolCreated data: (int24 tickSpacing, address pool).
        Returns (tick_spacing, pool_address).
        """
        if not data or data == "0x":
            return 0, None

        hex_data = data[2:] if data.startswith("0x") else data
        if len(hex_data) < 128:
            return 0, None

        # First 32 bytes = tickSpacing (int24, right-aligned as signed)
        tick_word = hex_data[:64]
        tick_spacing = int(tick_word, 16)
        # Handle int24 signed
        if tick_spacing > 0x7FFFFF:
            tick_spacing -= 0x1000000

        # Second 32 bytes = pool address
        pool_word = hex_data[64:128]
        pool_address = "0x" + pool_word[-40:]

        return tick_spacing, pool_address
