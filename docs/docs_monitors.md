# 🎧 توثيق نظام المراقبة (Monitors)

## نظرة عامة

نظام المراقبة هو قلب **Base Launch Detector** - يستمع لأحداث البلوكشين مباشرة عبر WebSocket بدلاً من الاعتماد على APIs خارجية.

## هيكل المجلد

```
monitors/
├── __init__.py                # تصدير جميع المكونات
├── pair_monitor.py            # المنسق الرئيسي للمراقبة
├── aerodrome_factory.py       # مستمع مصنع Aerodrome V2
├── uniswap_factory.py         # مستمع مصنع Uniswap V3
├── liquidity_monitor.py       # مراقب السيولة (Mint/Burn/Swap)
├── risk_scanner.py            # ماسح المخاطر السريع
└── momentum_engine.py         # محرك الزخم (Buy/Sell/Volume)
```

---

## 1. Pair Monitor (`pair_monitor.py`)

### الوصف
المنسق الرئيسي الذي يربط Web3 بمستمعي المصانع.

### المكونات
| الفئة | الوصف |
|-------|-------|
| `PairMonitor` | المنسق الرئيسي - يدير اتصال Web3 والمستمعين |
| `NewPairEvent` | حدث موحد لأي زوج جديد من أي منصة |

### طريقة العمل
```python
from monitors.pair_monitor import PairMonitor

monitor = PairMonitor()
await monitor.start()

async for event in monitor.stream():
    print(f"New pair: {event.base_token}/{event.token_address}")
    print(f"DEX: {event.dex}")
    print(f"Type: {event.pair_type}")
```

### أنواع الأزواج
- `volatile` - زوج متغير (Aerodrome volatile)
- `stable` - زوج مستقر (Aerodrome stable)
- `concentrated` - سيولة مركزة (Uniswap V3)

---

## 2. Aerodrome Factory (`aerodrome_factory.py`)

### الوصف
يستمع لأحداث `PoolCreated` من مصنع Aerodrome V2.

### عنوان المصنع
`0x420DD381b31aEf6683db6B902084cB0FFEe40Da`

### الحدث
```solidity
event PoolCreated(
    indexed address token0,
    indexed address token1,
    indexed bool stable,
    address pool,
    uint256
)
```

### الميزات
- ✅ WebSocket subscription (أساسي)
- ✅ Fallback إلى polling عبر HTTP
- ✅ Backfill للبلوكات الفائتة
- ✅ إعادة اتصال تلقائية

### المخرجات
```python
@dataclass
class AerodromePairInfo:
    token_address: str       # عنوان العملة الجديدة
    pair_address: str        # عنوان الزوج
    base_token: str          # WETH, USDC, cbBTC...
    base_token_address: str
    is_stable: bool          # Stable or Volatile
    dex: str = "aerodrome"
    created_at: float        # Unix timestamp
    block_number: int
    tx_hash: str
```

---

## 3. Uniswap V3 Factory (`uniswap_factory.py`)

### الوصف
يستمع لأحداث `PoolCreated` من مصنع Uniswap V3 على Base.

### عنوان المصنع
`0x33128a8fC17869897dcE68Ed026d694621f6FDfD`

### الحدث
```solidity
event PoolCreated(
    indexed address token0,
    indexed address token1,
    indexed uint24 fee,
    int24 tickSpacing,
    address pool
)
```

### الميزات
- ✅ نفس آلية Aerodrome (WS + fallback + backfill)
- ✅ فك ترميز fee و tickSpacing
- ✅ تصنيف العملات الأساسية آلياً

---

## 4. Liquidity Monitor (`liquidity_monitor.py`)

### الوصف
يراقب الأزواج الجديدة لأحداث السيولة (Mint, Burn, Swap).

### الأحداث المراقبة
| الحدث | الوصف | النوع |
|-------|-------|-------|
| `Mint` | إضافة سيولة | إيجابي ✅ |
| `Burn` | سحب سيولة | سلبي ❌ |
| `Swap` | تداول | محايد |

### تصنيف السيولة
| المستوى | النطاق | الرمز |
|---------|--------|-------|
| MICRO | < $1,000 | 🔸 |
| LOW | $1,000 - $5,000 | 🔹 |
| MEDIUM | $5,000 - $20,000 | 💠 |
| HIGH | $20,000 - $100,000 | 💎 |
| WHALE | > $100,000 | 🐋 |

### اكتشافات خاصة
- 🟢 **INITIAL_LIQUIDITY**: أول إضافة سيولة (الزوج يصبح قابلاً للتداول)
- 📈 **LIQUIDITY_INCREASED**: زيادة بأكثر من 100%
- 🚨 **LIQUIDITY_REMOVED**: سحب أكثر من 50% من السيولة

---

## 5. Risk Scanner (`risk_scanner.py`)

### الوصف
يشغل المحللات الأربعة الموجودة concurrently عبر `asyncio.gather`.

### المحللات المستخدمة
| المحلل | المهمة | الوقت التقريبي |
|--------|-------|---------------|
| `SecurityScoreChecker` | درجة الأمان 0-100 | ~2s |
| `HoneypotChecker` | كشف Honeypot | ~2s |
| `HoldersChecker` | توزيع الحاملين | ~3s |
| `LiquidityChecker` | قفل السيولة | ~2s |

> ⚠️ لا يستخدم GitHub Checker لتوفير السرعة

### المخرجات
```python
@dataclass
class RiskScanResult:
    security_score: int          # 0-100
    is_honeypot: bool
    has_proxy: bool
    is_mintable: bool
    is_blacklisted: bool
    owner_renounced: bool
    holders_concentration: str   # low/medium/high/extreme
    locked_percentage: float
    overall_risk_score: int      # Combined 0-100
```

---

## 6. Momentum Engine (`momentum_engine.py`)

### الوصف
بعد 5 دقائق من الإطلاق، يحلل نشاط التداول.

### المقاييس المحسوبة
| المقياس | الفترة | الوصف |
|---------|--------|-------|
| `buy_count_5m` | 5 دقائق | عدد المشترين |
| `sell_count_5m` | 5 دقائق | عدد البائعين |
| `volume_5m_usd` | 5 دقائق | حجم التداول |
| `volume_15m_usd` | 15 دقيقة | حجم التداول |
| `unique_buyers` | - | مشترين فريدين |
| `buy_sell_ratio` | 5 دقائق | نسبة الشراء/البيع |

### الكشف المتقدم
- 🐋 **Whale Detection**: شراء >5% من العرض
- 🧠 **Smart Money**: محافظ معروفة
- 🎯 **Sniper Detection**: شراء في أول 3 بلوكات
- 🤖 **Bot Activity**: نمط شراء آلي

---

## إعدادات المراقبة (.env)

```env
# أي المنصات نراقب
MONITOR_ENABLED=true
MONITOR_AERODROME=true
MONITOR_UNISWAP_V3=true

# إعدادات السيولة
MIN_LIQUIDITY_ALERT_USD=500

# متى نبدأ تحليل الزخم
MOMENTUM_CHECK_AFTER_SECONDS=300

# حدود الحيتان
WHALE_THRESHOLD_PERCENT=5
WHALE_EXIT_THRESHOLD_PERCENT=30