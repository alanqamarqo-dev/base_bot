"""
Base Monitor - Central Configuration
=====================================
All settings for the real-time Base chain monitoring system.
Loaded from environment variables with sensible defaults.
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RPCConfig:
    """WebSocket and HTTP RPC endpoints for Base chain."""
    ws_url: str = os.getenv(
        "BASE_RPC_WS",
        "wss://base-mainnet.g.alchemy.com/v2/demo"
    )
    http_url: str = os.getenv(
        "BASE_RPC_HTTP", 
        "https://mainnet.base.org"
    )
    ws_fallback: str = os.getenv(
        "BASE_RPC_WS_FALLBACK",
        "wss://base-rpc.publicnode.com"
    )
    http_fallback: str = os.getenv(
        "BASE_RPC_HTTP_FALLBACK",
        "https://mainnet.base.org"
    )


@dataclass
class MonitorConfig:
    """Monitor behaviour settings."""
    enabled: bool = os.getenv("MONITOR_ENABLED", "true").lower() == "true"
    aerodrome: bool = os.getenv("MONITOR_AERODROME", "true").lower() == "true"
    uniswap_v3: bool = os.getenv("MONITOR_UNISWAP_V3", "true").lower() == "true"
    min_liquidity_alert_usd: float = float(os.getenv("MIN_LIQUIDITY_ALERT_USD", "500"))
    momentum_check_after_seconds: int = int(os.getenv("MOMENTUM_CHECK_AFTER_SECONDS", "300"))
    whale_threshold_percent: float = float(os.getenv("WHALE_THRESHOLD_PERCENT", "5"))
    whale_exit_threshold_percent: float = float(os.getenv("WHALE_EXIT_THRESHOLD_PERCENT", "30"))
    reconnection_delay: float = float(os.getenv("RECONNECTION_DELAY", "3.0"))
    max_reconnection_attempts: int = int(os.getenv("MAX_RECONNECTION_ATTEMPTS", "10"))


@dataclass
class APIConfig:
    """FastAPI server settings."""
    enabled: bool = os.getenv("API_ENABLED", "true").lower() == "true"
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))


@dataclass  
class TelegramConfig:
    """Telegram bot settings (shared with existing system)."""
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "")


@dataclass
class AnalyzerConfig:
    """Analyzer API keys."""
    basescan_api_key: str = os.getenv("BASESCAN_API_KEY", "")
    github_token: str = os.getenv("GITHUB_TOKEN", "")


@dataclass
class Settings:
    """Root settings container."""
    rpc: RPCConfig = field(default_factory=RPCConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    api: APIConfig = field(default_factory=APIConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    analyzers: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    db_path: str = os.getenv("DB_PATH", "base_bot.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    chain_id: int = 8453


# Singleton instance
settings = Settings()
