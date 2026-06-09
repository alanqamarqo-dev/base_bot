"""
Base Chain DEX Contract Registry
=================================
Factory addresses, ABIs, and event signatures for all monitored DEXs.

Aerodrome V2: Dominant DEX on Base (~90%+ volume)
    Factory: 0x420DD381b31aEf6683db6B902084cB0FFEe40Da
    Event: PoolCreated(indexed address token0, indexed address token1, 
           indexed bool stable, address pool, uint256)

Uniswap V3: Secondary DEX
    Factory: 0x33128a8fC17869897dcE68Ed026d694621f6FDfD
    Event: PoolCreated(indexed address token0, indexed address token1, 
           indexed uint24 fee, int24 tickSpacing, address pool)
"""

# ── Aerodrome V2 ──────────────────────────────────────────────────

AERODROME_FACTORY_ADDRESS = "0x420DD381b31aEf6683db6B902084cB0FFEe40Da"
AERODROME_FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "token0", "type": "address"},
            {"indexed": True, "name": "token1", "type": "address"},
            {"indexed": True, "name": "stable", "type": "bool"},
            {"indexed": False, "name": "pool", "type": "address"},
            {"indexed": False, "name": "", "type": "uint256"},
        ],
        "name": "PoolCreated",
        "type": "event",
    },
    {
        "inputs": [{"name": "token", "type": "address"}],
        "name": "isPool",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "allPoolsLength",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

AERODROME_POOL_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Mint",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Burn",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "amount0In", "type": "uint256"},
            {"indexed": False, "name": "amount1In", "type": "uint256"},
            {"indexed": False, "name": "amount0Out", "type": "uint256"},
            {"indexed": False, "name": "amount1Out", "type": "uint256"},
        ],
        "name": "Swap",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "stable",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "_reserve0", "type": "uint256"},
            {"name": "_reserve1", "type": "uint256"},
            {"name": "_blockTimestampLast", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ERC20 minimal ABI for token metadata
ERC20_ABI = [
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ── Uniswap V3 ─────────────────────────────────────────────────────

UNISWAP_V3_FACTORY_ADDRESS = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"

UNISWAP_V3_FACTORY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "token0", "type": "address"},
            {"indexed": True, "name": "token1", "type": "address"},
            {"indexed": True, "name": "fee", "type": "uint24"},
            {"indexed": False, "name": "tickSpacing", "type": "int24"},
            {"indexed": False, "name": "pool", "type": "address"},
        ],
        "name": "PoolCreated",
        "type": "event",
    },
]

UNISWAP_V3_POOL_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": False, "name": "tickLower", "type": "int24"},
            {"indexed": False, "name": "tickUpper", "type": "int24"},
            {"indexed": False, "name": "amount", "type": "uint128"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Mint",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "uint256"},
            {"indexed": False, "name": "amount1", "type": "uint256"},
        ],
        "name": "Burn",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "int256"},
            {"indexed": False, "name": "amount1", "type": "int256"},
            {"indexed": False, "name": "sqrtPriceX96", "type": "uint160"},
            {"indexed": False, "name": "liquidity", "type": "uint128"},
            {"indexed": False, "name": "tick", "type": "int24"},
        ],
        "name": "Swap",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [{"name": "", "type": "uint24"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ── Event Signature Hashes (for eth_getLogs / eth_subscribe) ──────

# PoolCreated(bytes32) indexed by address at topics[0]
# Keccak-256 of "PoolCreated(address,address,bool,address,uint256)" - Aerodrome
# Keccak-256 of "PoolCreated(address,address,uint24,int24,address)" - UniswapV3

AERODROME_POOL_CREATED_TOPIC = (
    "0x0d3640c5a1192b7e0e49735a7a45bb68b27cdc324b50ac1b73d83f468068ee41"
)

UNISWAP_V3_POOL_CREATED_TOPIC = (
    "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
)

# Aerodrome Pool events
AERODROME_MINT_TOPIC = (
    "0xd3cd3a48e5893cdcaf4eef319fa984cd8a880aaa9c5a99d05e2fcf52e428500c"
)
AERODROME_BURN_TOPIC = (
    "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"
)
AERODROME_SWAP_TOPIC = (
    "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
)

# UniswapV3 Pool events
UNISWAP_V3_MINT_TOPIC = (
    "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
)
UNISWAP_V3_BURN_TOPIC = (
    "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
)
UNISWAP_V3_SWAP_TOPIC = (
    "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
)

# ── Known Base Tokens (for classifying pairs) ──────────────────────

KNOWN_BASE_TOKENS = {
    "0x4200000000000000000000000000000000000006": "WETH",
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "USDC",
    "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA": "USDbC",
    "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf": "cbBTC",
    "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb": "DAI",
    "0x2Ae3F1Ec7F1F5012CFEab7675b9843940F26D62a": "USDT",
    "0x4200000000000000000000000000000000000001": "BRIDGED_ETH",
}

# Known token address => symbol for quick lookup
KNOWN_TOKEN_SYMBOLS = {
    "0x4200000000000000000000000000000000000006": "WETH",
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "USDC",
    "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA": "USDbC",
    "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf": "cbBTC",
    "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb": "DAI",
    "0x2Ae3F1Ec7F1F5012CFEab7675b9843940F26D62a": "USDT",
}

def get_base_token_symbol(address: str) -> str:
    """Return the symbol for a known base token, or 'UNKNOWN'."""
    return KNOWN_TOKEN_SYMBOLS.get(address.lower(), "UNKNOWN")

def is_known_base_token(address: str) -> bool:
    """Check if address is a well-known Base chain token."""
    return address.lower() in KNOWN_BASE_TOKENS
