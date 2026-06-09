"""
Known Smart Money Wallets
==========================
Database of known wallet addresses on Base chain:
- Professional traders / snipers
- Market makers
- Bot addresses
- Known whale wallets

These are used for Smart Money detection and Sniper detection.
In production, this should be loaded from a database or API.
"""

# ── Smart Money Wallets (Professional Traders / Funds) ────────────
# These wallets are known for consistently profitable early entries.
# Format: {"address": "0x...", "label": "Trader Name"}

SMART_MONEY_WALLETS = {
    # Add known smart money addresses here
    # Example format:
    # "0x1234...5678": {"label": "Known Trader", "type": "trader"},
}

# ── Sniper / MEV Bot Addresses ────────────────────────────────────
# These are known sniper bots that buy in first block(s).

SNIPER_BOTS = {
    # Add known sniper bot addresses here
}

# ── Market Maker Addresses ────────────────────────────────────────
# Known market maker contracts/EOAs on Base.

MARKET_MAKERS = {
    # Add known market maker addresses here
}

# ── Known Whale Wallets ───────────────────────────────────────────
# These wallets are tracked for whale exit detection.

WHALE_WALLETS = {
    # Add known whale wallets here
}


def is_smart_money(address: str) -> bool:
    """Check if an address is a known smart money wallet."""
    return address.lower() in SMART_MONEY_WALLETS


def is_sniper_bot(address: str) -> bool:
    """Check if an address is a known sniper bot."""
    return address.lower() in SNIPER_BOTS


def is_market_maker(address: str) -> bool:
    """Check if an address is a known market maker."""
    return address.lower() in MARKET_MAKERS


def get_wallet_label(address: str) -> str:
    """Get the label for a known wallet address."""
    addr = address.lower()
    if addr in SMART_MONEY_WALLETS:
        return SMART_MONEY_WALLETS[addr].get("label", "Smart Money")
    if addr in SNIPER_BOTS:
        return "Sniper Bot"
    if addr in MARKET_MAKERS:
        return "Market Maker"
    return "Unknown"
