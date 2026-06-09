# ⚙️ توثيق الإعدادات والعقود (Config)

## نظرة عامة

مجلد `config/` يحتوي على جميع الإعدادات وعناوين العقود وقاعدة المحافظ المعروفة.

## هيكل الملفات

```
config/
├── __init__.py         # إعدادات النظام (Settings)
├── contracts.py        # عناوين العقود و ABI وأحداث
└── known_wallets.py    # محافظ Smart Money/Snipers
```

---

## 1. الإعدادات (`__init__.py`)

### RPC Config
```python
@dataclass
class RPCConfig:
    ws_url: str           # WebSocket RPC URL
    http_url: str         # HTTP RPC URL (fallback)
    ws_fallback: str      # WebSocket احتياطي
    http_fallback: str    # HTTP احتياطي
```

### Monitor Config
```python
@dataclass
class MonitorConfig:
    enabled: bool                     # تشغيل/إيقاف المراقب
    aerodrome: bool                   # مراقبة Aerodrome
    uniswap_v3: bool                  # مراقبة Uniswap V3
    min_liquidity_alert_usd: float    # حد أدنى للسيولة ($500)
    momentum_check_after_seconds: int # وقت انتظار تحليل الزخم (300)
    whale_threshold_percent: float    # حد الحوت (5%)
    whale_exit_threshold_percent: float # حد خروج الحيتان (30%)
    reconnection_delay: float         # تأخير إعادة الاتصال (3.0s)
    max_reconnection_attempts: int    # محاولات إعادة الاتصال (10)
```

### API Config
```python
@dataclass
class APIConfig:
    enabled: bool    # تشغيل/إيقاف API
    host: str        # عنوان الخادم (0.0.0.0)
    port: int        # المنفذ (8000)
```

### الاستخدام
```python
from config.settings import settings

print(settings.rpc.ws_url)
print(settings.monitor.aerodrome)
print(settings.api.port)
```

---

## 2. العقود (`contracts.py`)

### المصانع المدعومة

| المنصة | عنوان المصنع | الحدث |
|--------|-------------|-------|
| Aerodrome V2 | `0x420DD381b31aEf6683db6B902084cB0FFEe40Da` | `PoolCreated` |
| Uniswap V3 | `0x33128a8fC17869897dcE68Ed026d694621f6FDfD` | `PoolCreated` |

### ABIs المتوفرة

| ABI | الاستخدام |
|-----|----------|
| `AERODROME_FACTORY_ABI` | مستمع المصنع |
| `AERODROME_POOL_ABI` | مراقب الزوج (Mint/Burn/Swap) |
| `UNISWAP_V3_FACTORY_ABI` | مستمع المصنع |
| `UNISWAP_V3_POOL_ABI` | مراقب الزوج |
| `ERC20_ABI` | بيانات العملة (symbol, name, decimals) |

### Event Topics (Keccak-256 hashes)

| الحدث | الـ topic |
|-------|----------|
| `AERODROME_POOL_CREATED_TOPIC` | `0x0d3640c5...` |
| `UNISWAP_V3_POOL_CREATED_TOPIC` | `0x783cca1c...` |
| `AERODROME_MINT_TOPIC` | `0xd3cd3a48...` |
| `AERODROME_BURN_TOPIC` | `0xdccd412f...` |
| `AERODROME_SWAP_TOPIC` | `0xd78ad95f...` |
| `UNISWAP_V3_MINT_TOPIC` | `0x7a53080b...` |
| `UNISWAP_V3_BURN_TOPIC` | `0x0c396cd9...` |
| `UNISWAP_V3_SWAP_TOPIC` | `0xc42079f9...` |

### العملات الأساسية المعروفة

| العنوان | الرمز |
|---------|-------|
| `0x4200...0006` | WETH |
| `0x833589fC...` | USDC |
| `0xd9aAEc86...` | USDbC |
| `0xcbB7C000...` | cbBTC |
| `0x50c57259...` | DAI |

---

## 3. المحافظ المعروفة (`known_wallets.py`)

### أنواع المحافظ

| النوع | الوصف |
|-------|-------|
| `SMART_MONEY_WALLETS` | متداولين محترفين وصناديق |
| `SNIPER_BOTS` | روبوتات السناب |
| `MARKET_MAKERS` | صانعي السوق |
| `WHALE_WALLETS` | محافظ الحيتان |

### إضافة محفظة

```python
SMART_MONEY_WALLETS = {
    "0x1234...5678": {"label": "Trader Name", "type": "trader"},
    "0xabcd...ef01": {"label": "Fund Name", "type": "fund"},
}
```

### دوال التحقق

```python
from config.known_wallets import (
    is_smart_money,
    is_sniper_bot,
    is_market_maker,
    get_wallet_label,
)

if is_smart_money("0x1234..."):
    label = get_wallet_label("0x1234...")
    print(f"Smart Money: {label}")