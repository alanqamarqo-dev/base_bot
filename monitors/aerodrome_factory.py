"""
Aerodrome V2 Factory Event Listener
====================================
Listens for PoolCreated events from Aerodrome V2 Factory
on Base chain via WebSocket subscription.

Factory: 0x420DD381b31aEf6683db6B902084cB0FFEe40Da
Event: PoolCreated(token0, token1, stable, pool, uint256)
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from web3 import AsyncWeb3, WebSocketProvider
from web3.exceptions import Web3Exception

from config.settings import settings
from config.contracts import (
    AERODROME_FACTORY_ADDRESS,
    AERODROME_FACTORY_ABI,
    AERODROME_POOL_CREATED_TOPIC,
    get_base_token_symbol,
    is_known_base_token,
)

logger = logging.getLogger("AerodromeFactory")


@dataclass
class AerodromePairInfo:
    """Parsed Aerodrome PoolCreated event data."""
    token_address: str
    pair_address: str
    base_token: str
    base_token_address: str
    is_stable: bool
    dex: str = "aerodrome"
    created_at: float = 0.0
    block_number: int = 0
    tx_hash: str = ""


class AerodromeFactoryListener:
    """
    Subscribes to Aerodrome V2 Factory PoolCreated events via WebSocket.
    Parses each event and pushes AerodromePairInfo to the callback queue.
    """

    def __init__(self, w3: AsyncWeb3, queue: asyncio.Queue):
        self.w3 = w3
        self.queue = queue
        self.factory_address = AERODROME_FACTORY_ADDRESS
        self.factory = self.w3.eth.contract(
            address=self.factory_address,
            abi=AERODROME_FACTORY_ABI,
        )
        self._running = False
        self._subscription_id: Optional[str] = None
        self._last_processed_block: int = 0

    async def start(self):
        """Start listening for Aerodrome PoolCreated events."""
        self._running = True
        logger.info(
            f"🎧 Aerodrome Factory listener starting on {self.factory_address[:10]}..."
        )

        # Backfill: fetch recent blocks to catch any missed events
        current_block = await self.w3.eth.block_number
        backfill_from = max(current_block - 500, self._last_processed_block or current_block - 500)

        if backfill_from < current_block:
            logger.info(
                f"Backfilling PoolCreated events from block {backfill_from} to {current_block}"
            )
            await self._backfill_events(backfill_from, current_block)

        self._last_processed_block = current_block

        # Subscribe to live events
        try:
            await self._subscribe_live()
        except Exception as e:
            logger.error(f"WebSocket subscription failed: {e}")
            # Fallback: poll via eth_getLogs periodically
            await self._poll_loop()

    async def _subscribe_live(self):
        """Set up WebSocket log subscription for PoolCreated events."""
        filter_params = {
            "address": self.factory_address,
            "topics": [AERODROME_POOL_CREATED_TOPIC],
        }
        try:
            self._subscription_id = await self.w3.eth.subscribe("logs", filter_params)
            logger.info(f"Aerodrome subscription active: {self._subscription_id}")

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
                    logger.warning(f"Subscription error: {e}, will retry...")
                    await asyncio.sleep(settings.monitor.reconnection_delay)
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            raise

    async def _poll_loop(self):
        """Fallback: poll for new events every block."""
        logger.info("Switched to polling mode for Aerodrome")
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
                logger.warning(f"Poll error: {e}")
            await asyncio.sleep(2.0)  # Base block time ~2s

    async def _backfill_events(self, from_block: int, to_block: int):
        """Fetch historical PoolCreated events via eth_getLogs."""
        try:
            logs = await self.w3.eth.get_logs({
                "address": self.factory_address,
                "topics": [AERODROME_POOL_CREATED_TOPIC],
                "fromBlock": from_block,
                "toBlock": to_block,
            })
            for log in logs:
                await self._handle_log(log)
            if logs:
                logger.info(f"Backfilled {len(logs)} Aerodrome events from blocks {from_block}-{to_block}")
        except Exception as e:
            logger.warning(f"Backfill error: {e}")

    async def _handle_log(self, log: Dict[str, Any]):
        """Parse a PoolCreated log and enqueue the result."""
        try:
            # Aerodrome PoolCreated event layout:
            # topics[0]: event signature
            # topics[1]: indexed token0 (address)
            # topics[2]: indexed token1 (address)
            # topics[3]: indexed stable (bool)
            # data: pool (address), uint256

            topics = log.get("topics", [])
            data = log.get("data", "0x")

            if len(topics) < 4:
                return

            token0 = self._topic_to_address(topics[1])
            token1 = self._topic_to_address(topics[2])
            stable_raw = topics[3]
            is_stable = int(stable_raw, 16) != 0

            # Pool address from data (first 32 bytes)
            pool_address = self._data_to_address(data)

            if not pool_address:
                logger.warning("Could not decode pool address from event data")
                return

            # Determine which is the base token (known) vs the new token
            base_token_address = ""
            token_address = ""

            if is_known_base_token(token0):
                base_token_address = token0
                token_address = token1
            elif is_known_base_token(token1):
                base_token_address = token1
                token_address = token0
            else:
                # Neither is known — both could be new; take token0 as base
                base_token_address = token0
                token_address = token1

            base_token = get_base_token_symbol(base_token_address)

            pair_info = AerodromePairInfo(
                token_address=token_address.lower(),
                pair_address=pool_address.lower(),
                base_token=base_token,
                base_token_address=base_token_address.lower(),
                is_stable=is_stable,
                created_at=time.time(),
                block_number=log.get("blockNumber", 0),
                tx_hash=log.get("transactionHash", ""),
            )

            await self.queue.put(pair_info)

            logger.info(
                f"🟢 Aerodrome: {pair_info.base_token}/{token_address[:10]}... "
                f"(pool: {pool_address[:10]}..., "
                f"{'stable' if is_stable else 'volatile'})"
            )

        except Exception as e:
            logger.error(f"Error handling Aerodrome log: {e}")

    async def stop(self):
        """Stop the listener."""
        self._running = False
        if self._subscription_id:
            try:
                await self.w3.eth.unsubscribe(self._subscription_id)
            except Exception:
                pass
            self._subscription_id = None
        logger.info("Aerodrome Factory listener stopped")

    @staticmethod
    def _topic_to_address(topic: str) -> str:
        """Extract address from event topic (left-padded to 32 bytes)."""
        if topic.startswith("0x"):
            # topic is 32 bytes: 0x + 64 hex chars
            # address is 20 bytes: last 40 hex chars
            return "0x" + topic[-40:]
        return "0x" + topic[-40:]

    @staticmethod
    def _data_to_address(data: str) -> Optional[str]:
        """Extract first address from event data."""
        if not data or data == "0x":
            return None
        # Remove 0x prefix
        hex_data = data[2:] if data.startswith("0x") else data
        if len(hex_data) < 64:
            return None
        # First 32-byte word contains the pool address (right-aligned)
        pool_word = hex_data[:64]
        return "0x" + pool_word[-40:]
