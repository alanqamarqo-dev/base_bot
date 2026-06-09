"""
Alerts Module
=============
Formats and dispatches alerts via Telegram and internal event bus.
"""

from alerts.alert_manager import AlertManager, Alert

__all__ = ["AlertManager", "Alert"]
