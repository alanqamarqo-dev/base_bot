# 📡 Scanner Module Documentation

## Overview
The scanner module discovers newly listed tokens on the **Base** blockchain using the DexScreener public API.

## Files
- [`scanner/base_scanner.py`](../scanner/base_scanner.py) — Primary token scanner
- [`scanner/dex_scanner.py`](../scanner/dex_scanner.py) — Extended DexScreener operations
- [`scanner/__init__.py`](../scanner/__init__.py) — Package exports

## API Usage

### BaseScanner

```python
from scanner import BaseScanner

scanner = BaseScanner(max_results=30, min_liquidity_usd=1000)

# Fetch latest Base chain tokens
tokens = await scanner.fetch_latest_tokens()

# Get detailed info for a specific address
token = await scanner.get_token_info("0x...")

# Clean up
await scanner.close()
```

### TokenData

```python
@dataclass
class TokenData:
    address: str          # Contract address
    name: str             # Token name
    symbol: str           # Ticker symbol
    chain: str            # "base"
    description: str      # Project description
    website: str          # Official website URL
    twitter: str          # Twitter/X URL
    telegram: str         # Telegram group URL
    discord: str          # Discord server URL
    github: str           # GitHub repository URL
    market_cap: float     # Market capitalization (USD)
    price_usd: float      # Current price (USD)
    liquidity_usd: float  # Total liquidity (USD)
    volume_24h: float     # 24h trading volume (USD)
    price_change_24h: float # 24h price change (%)
    pair_address: str     # Main pair contract
    dex_url: str          # DexScreener page URL
```

### DexScanner

```python
from scanner import DexScanner

dex = DexScanner()

# Get specific pair data
pair = await dex.get_pairs("base", "0xPairAddress")

# Search for tokens
results = await dex.search_pairs("token name")

# Bulk fetch pairs
pairs_map = await dex.get_token_pairs_bulk(["0xAddr1", "0xAddr2"])

await dex.close()
```

## Data Sources
- **DexScreener Latest Profiles**: `GET /token-profiles/latest/v1`
- **DexScreener Search**: `GET /latest/dex/search?q=base`
- **DexScreener Tokens**: `GET /latest/dex/tokens/{address}`

## Filtering
Tokens are filtered by:
- `chainId == "base"` (Base chain only)
- `liquidity_usd >= min_liquidity_usd` (default: $1,000)
- `max_results` (default: 50 tokens per scan)

---

# 📡 توثيق وحدة الماسح (النسخة العربية)

## 📖 نظرة عامة
تُكتشف **التوكنات الجديدة** على سلسلة **Base** باستخدام:
- **DexScreener API** — قاعدة بيانات البورصات اللامركزية
- ✅ لا تحتاج API key
- ✅ مجاني تماماً
- ✅ بيانات حقيقية مباشرة

---

## 🔍 آلية البحث

### الخطوات:
```
1. الاتصال بـ DexScreener
2. البحث عن آخر التوكنات المدرجة (Base chain فقط)
3. تطبيق المرشحات:
   - السيولة > 1000 دولار
   - الحد الأقصى 30 توكن
4. إرجاع البيانات المنسقة
```

---

## 🚀 كيفية الاستخدام

### استخدام أساسي:

```python
from scanner import BaseScanner
import asyncio

async def scan_tokens():
    # إنشاء ماسح
    scanner = BaseScanner(
        max_results=30,                # أقصى عدد توكنات
        min_liquidity_usd=1000,        # حد أدنى للسيولة
    )
    
    # جلب أحدث التوكنات
    tokens = await scanner.fetch_latest_tokens()
    # يرجع قائمة من TokenData objects
    
    # عرض النتائج
    for token in tokens:
        print(f"🔷 {token.name} (${token.symbol})")
        print(f"   عنوان: {token.address}")
        print(f"   السيولة: ${token.liquidity_usd:,.0f}")
        print(f"   الرابط: {token.dex_url}")
        print()
    
    # إغلاق الاتصال
    await scanner.close()

# التشغيل
asyncio.run(scan_tokens())
```

### الحصول على معلومات توكن محدد:

```python
async def get_token_details():
    scanner = BaseScanner()
    
    # البحث عن توكن بالعنوان
    token = await scanner.get_token_info("0xTokenAddress")
    
    if token:
        print(f"✅ وُجد: {token.name}")
        print(f"   S السعر: ${token.price_usd}")
        print(f"   القيمة السوقية: ${token.market_cap:,.0f}")
    else:
        print("❌ لم يُعثر على توكن")
    
    await scanner.close()

asyncio.run(get_token_details())
```

---

## 📊 بيانات TokenData

### كل توكن يحتوي على:

```python
token.address              # عنوان العقد (0x...)
token.name                 # اسم التوكن
token.symbol               # الاختصار (MTK)
token.chain                # السلسلة ("base")
token.description          # وصف المشروع
token.website              # الموقع: https://...
token.twitter              # تويتر: https://twitter.com/...
token.telegram             # تيليجرام: https://t.me/...
token.discord              # ديسكورد: https://discord.gg/...
token.github               # GitHub: https://github.com/...
token.market_cap           # القيمة السوقية (دولار)
token.price_usd            # السعر الحالي (دولار)
token.liquidity_usd        # السيولة (دولار)
token.volume_24h           # حجم التداول 24 ساعة
token.price_change_24h     # تغير السعر % في 24 ساعة
token.pair_address         # عنوان الزوج (في البورصة)
token.dex_url              # رابط DexScreener المباشر
```

---

## 🌐 استخدام DexScanner للاستعلامات المتقدمة:

```python
from scanner import DexScanner
import asyncio

async def advanced_queries():
    dex = DexScanner()
    
    # 1️⃣ الحصول على معلومات زوج محدد
    pair = await dex.get_pairs("base", "0xPairAddress")
    print(f"معلومات الزوج: {pair}")
    
    # 2️⃣ البحث عن توكن بالاسم
    results = await dex.search_pairs("MyToken")
    print(f"وُجدت {len(results)} نتائج")
    
    # 3️⃣ جلب معلومات عدة توكنات معاً
    addresses = ["0xAddr1", "0xAddr2", "0xAddr3"]
    pairs_data = await dex.get_token_pairs_bulk(addresses)
    
    for addr, data in pairs_data.items():
        print(f"📍 {addr}: {data}")
    
    await dex.close()

asyncio.run(advanced_queries())
```

---

## 🔗 مصادر البيانات:

| الـ Endpoint | الاستخدام |
|------------|----------|
| `/token-profiles/latest/v1` | 🆕 آخر التوكنات الجديدة |
| `/latest/dex/search` | 🔍 البحث عن توكن |
| `/latest/dex/tokens/{address}` | 📊 معلومات توكن |

---

## 🎯 معايير التصفية:

```
✅ يتم تضمين التوكن إذا:
  • السلسلة = Base
  • السيولة ≥ $1,000 (قابل للتعديل)
  • البيانات كاملة (اسم، رمز، عنوان)

❌ يتم استبعاد التوكن إذا:
  • السيولة < $1,000
  • السلسلة ليست Base
  • البيانات ناقصة
  • التوكن مكرر من فحص سابق
```

---

## 📈 مثال عملي شامل:

```python
import asyncio
from scanner import BaseScanner, DexScanner

async def full_scan_example():
    print("🔍 بدء الفحص...")
    
    # إعدادات الماسح
    scanner = BaseScanner(
        max_results=10,              # 10 توكنات فقط
        min_liquidity_usd=5000,      # حد أدنى 5000 دولار
    )
    
    try:
        # 1️⃣ جلب آخر التوكنات
        print("⏳ جلب البيانات من DexScreener...")
        tokens = await scanner.fetch_latest_tokens()
        print(f"✅ وُجدت {len(tokens)} توكنات")
        
        # 2️⃣ معالجة كل توكن
        for i, token in enumerate(tokens, 1):
            print(f"\n[{i}/{len(tokens)}] 🔷 {token.name} (${token.symbol})")
            print(f"  السيولة: ${token.liquidity_usd:,.0f}")
            print(f"  السعر: ${token.price_usd}")
            print(f"  التغير 24h: {token.price_change_24h:+.2f}%")
            print(f"  المجموعة: {token.telegram or 'N/A'}")
            
            # يمكن تمرير هذه البيانات للمحللات الآن
        
        print(f"\n✅ انتهى الفحص: {len(tokens)} توكنات جاهزة للتحليل")
    
    except Exception as e:
        print(f"❌ خطأ: {e}")
    
    finally:
        await scanner.close()

# التشغيل
asyncio.run(full_scan_example())
```

---

## 🛠️ استكشاف الأخطاء:

### المشكلة: لا توكنات وُجدت

```
السبب المحتمل:
1. لا يوجد توكنات على Base مع السيولة المطلوبة
2. مشكلة الاتصال بـ DexScreener

الحل:
- قلّل الحد الأدنى للسيولة:
  min_liquidity_usd=100  # بدل 1000
  
- تحقق من الإنترنت
- جرّب من جديد بعد دقائق
```

### المشكلة: أخطاء في الاتصال

```
الحل:
1. تحقق من الإنترنت
2. تحقق من الـ firewall
3. استخدم VPN إذا تم حظر الدول
```

---

## 📌 ملاحظات مهمة:

✅ **مجاني تماماً**: لا تحتاج API key  
✅ **سريع**: البيانات في الوقت الفعلي  
✅ **موثوق**: بيانات من DexScreener الموثوقة  
⚠️ **تحديث**: قد يستغرق بضع ثوانٍ  
⚠️ **حد المعدل**: لا تطلق طلبات كثيرة جداً معاً

---