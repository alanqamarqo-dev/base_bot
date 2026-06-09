"""
Alert Manager
==============
Central alert dispatcher. Receives events from all monitors
and formats/sends alerts via Telegram and WebSocket.

Alert Types:
  🚀 New Pair Detected
  💧 Liquidity Added
  🛡️ Risk Scan Complete  
  🔥 EARLY GEM Detected
  🐋 Whale Detected
  🚨 Liquidity Removed
  📤 Whale Exit
  ⚡ Smart Money Entry
  🎯 Sniper Activity
  💀 Possible Rug Pull
"""

import asyncio
import json
import logging
import time
from typing import Optional, List, Callable, Any, Dict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("AlertManager")


class AlertType(Enum):
    NEW_PAIR = "new_pair"                  # 🚀
    LIQUIDITY_ADDED = "liquidity_added"    # 💧
    LIQUIDITY_REMOVED = "liquidity_removed"  # 🚨
    RISK_SCAN = "risk_scan"                # 🛡️
    EARLY_GEM = "early_gem"                # 💎
    WHALE_DETECTED = "whale_detected"      # 🐋
    SMART_MONEY = "smart_money"            # 🧠
    SNIPER = "sniper"                      # 🎯
    WHALE_EXIT = "whale_exit"              # 📤
    RUG_PULL = "rug_pull"                  # 💀
    WATCH = "watch"                        # 👀


@dataclass
class Alert:
    """A single alert to be dispatched."""
    alert_type: AlertType
    title: str
    body: str
    data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0       # 0=low, 5=medium, 10=critical
    timestamp: float = field(default_factory=time.time)

    @property
    def emoji(self) -> str:
        return {
            AlertType.NEW_PAIR: "🚀",
            AlertType.LIQUIDITY_ADDED: "💧",
            AlertType.LIQUIDITY_REMOVED: "🚨",
            AlertType.RISK_SCAN: "🛡️",
            AlertType.EARLY_GEM: "💎",
            AlertType.WHALE_DETECTED: "🐋",
            AlertType.SMART_MONEY: "🧠",
            AlertType.SNIPER: "🎯",
            AlertType.WHALE_EXIT: "📤",
            AlertType.RUG_PULL: "💀",
            AlertType.WATCH: "👀",
        }.get(self.alert_type, "📢")

    def to_dict(self) -> dict:
        return {
            "type": self.alert_type.value,
            "emoji": self.emoji,
            "title": self.title,
            "body": self.body,
            "data": self.data,
            "priority": self.priority,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class AlertManager:
    """
    Central alert dispatcher.
    
    Handles:
    - Telegram message formatting and sending
    - Alert history (last N alerts)
    - WebSocket broadcasting (for API)
    - Priority-based filtering
    """

    def __init__(self, telegram_sender=None):
        self.telegram = telegram_sender
        self._subscribers: List[Callable] = []
        self._alert_history: List[Alert] = []
        self._max_history = 1000

    def subscribe(self, callback: Callable[[Alert], None]):
        """Subscribe to all alerts (for WebSocket broadcasting)."""
        self._subscribers.append(callback)

    async def send_alert(self, alert: Alert):
        """Dispatch an alert to all channels."""
        # Store in history
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]

        # Log
        level = logging.WARNING if alert.priority >= 10 else logging.INFO
        logger.log(level, f"{alert.emoji} {alert.alert_type.value}: {alert.title}")

        # Send to subscribers (WebSocket)
        alert_data = alert.to_dict()
        for callback in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Alert subscriber error: {e}")

        # Send to Telegram
        if self.telegram and alert.priority >= 5:
            await self._send_telegram(alert)

    async def _send_telegram(self, alert: Alert):
        """Format and send alert via Telegram."""
        try:
            message = self._format_telegram_message(alert)
            # In production, use self.telegram.send_message(message)
            logger.info(f"📤 Telegram alert: {alert.title}")
            # self.telegram.send_alert(message)
        except Exception as e:
            logger.error(f"Telegram send error: {e}")

    def _format_telegram_message(self, alert: Alert) -> str:
        """Format an alert as a Telegram-compatible message."""
        d = alert.data

        if alert.alert_type == AlertType.NEW_PAIR:
            return (
                f"{alert.emoji} <b>New Pair Detected</b>\n\n"
                f"<b>Token:</b> {d.get('token_symbol', 'Unknown')}\n"
                f"<b>Pair:</b> {d.get('base_token', '')}/{d.get('token_symbol', '')}\n"
                f"<b>DEX:</b> {d.get('dex', 'Unknown')}\n"
                f"<b>Type:</b> {d.get('pair_type', 'Unknown')}\n"
                f"<b>Contract:</b> <code>{d.get('token_address', '')}</code>\n"
                f"<b>Pair:</b> <code>{d.get('pair_address', '')}</code>\n"
                f"\n<a href='https://dexscreener.com/base/{d.get('pair_address', '')}'>View on DexScreener</a>"
            )

        elif alert.alert_type == AlertType.LIQUIDITY_ADDED:
            level_emoji = d.get('level_emoji', '💧')
            return (
                f"{level_emoji} <b>Liquidity Added</b>\n\n"
                f"<b>Token:</b> {d.get('token_symbol', 'Unknown')}\n"
                f"<b>Amount:</b> ${d.get('liquidity_usd', 0):,.0f}\n"
                f"<b>Level:</b> {d.get('level_label', 'Unknown')}\n"
                f"<b>Base:</b> {d.get('base_token', '')}\n"
                f"<b>Pair:</b> <code>{d.get('pair_address', '')[:10]}...</code>"
            )

        elif alert.alert_type == AlertType.RISK_SCAN:
            return (
                f"{alert.emoji} <b>Risk Analysis: {d.get('token_symbol', 'Unknown')}</b>\n\n"
                f"Security: {d.get('security_score', 0)}/100\n"
                f"Honeypot: {'⚠️ YES' if d.get('is_honeypot') else '✅ NO'}\n"
                f"Proxy: {'⚠️ YES' if d.get('has_proxy') else '✅ NO'}\n"
                f"Mint: {'⚠️ YES' if d.get('is_mintable') else '✅ NO'}\n"
                f"Tax: Buy {d.get('buy_tax', 0):.0f}% / Sell {d.get('sell_tax', 0):.0f}%\n"
                f"Overall Risk: {d.get('overall_risk_score', 0)}/100"
            )

        elif alert.alert_type == AlertType.EARLY_GEM:
            return (
                f"💎 <b>EARLY GEM: {d.get('token_symbol', '')}/{d.get('base_token', '')}</b>\n\n"
                f"Age: {int(d.get('age_seconds', 0) // 60)} min\n"
                f"Buyers: {d.get('buy_count_5m', 0)} | Sells: {d.get('sell_count_5m', 0)}\n"
                f"Volume: ${d.get('volume_5m_usd', 0):,.0f}\n"
                f"Liquidity: ${d.get('liquidity_usd', 0):,.0f}\n"
                f"Score: {d.get('momentum_score', 0)}/100\n"
                f"{'🧠 Smart Money: Yes' if d.get('smart_money') else ''}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"<code>{d.get('token_address', '')}</code>\n"
                f"<a href='https://dexscreener.com/base/{d.get('pair_address', '')}'>DexScreener</a>"
            )

        elif alert.alert_type == AlertType.WHALE_DETECTED:
            return (
                f"🐋 <b>Whale Detected: {d.get('token_symbol', '')}</b>\n\n"
                f"Wallet <code>{d.get('whale_address', '')[:10]}...</code> "
                f"bought {d.get('whale_pct', 0):.1f}%\n"
                f"⚠️ High concentration risk"
            )

        elif alert.alert_type == AlertType.LIQUIDITY_REMOVED:
            return (
                f"🚨 <b>LIQUIDITY REMOVED: {d.get('token_symbol', '')}</b>\n\n"
                f"Before: ${d.get('previous_liquidity', 0):,.0f}\n"
                f"After: ${d.get('current_liquidity', 0):,.0f}\n"
                f"Change: {d.get('change_pct', 0):.1f}%\n"
                f"⚠️ POSSIBLE RUG PULL"
            )

        elif alert.alert_type == AlertType.SMART_MONEY:
            return (
                f"🧠 <b>Smart Money Entry: {d.get('token_symbol', '')}</b>\n\n"
                f"Wallet: <code>{d.get('wallet_address', '')[:10]}...</code>\n"
                f"Token: {d.get('token_symbol', '')}\n"
                f"Amount: ${d.get('amount_usd', 0):,.0f}"
            )

        # Default
        return f"{alert.emoji} <b>{alert.title}</b>\n\n{alert.body}"

    def get_recent_alerts(self, limit: int = 50, alert_type: str = None) -> List[dict]:
        """Get recent alerts, optionally filtered by type."""
        alerts = self._alert_history
        if alert_type:
            alerts = [a for a in alerts if a.alert_type.value == alert_type]
        return [a.to_dict() for a in alerts[-limit:]]

    def get_stats(self) -> dict:
        """Get alert statistics."""
        total = len(self._alert_history)
        by_type = {}
        for a in self._alert_history[-1000:]:
            t = a.alert_type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_alerts": total,
            "by_type": by_type,
        }

    def clear_history(self):
        """Clear alert history."""
        self._alert_history.clear()
