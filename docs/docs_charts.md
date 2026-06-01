# 📊 Charts Module Documentation

## Overview
Generates visual charts using **Matplotlib** with a dark theme. Charts are produced as PNG bytes ready for Telegram sending.

## File
- [`charts/chart_generator.py`](../charts/chart_generator.py)

## Chart Types

### 1. Security Score Gauge
```python
chart_gen = ChartGenerator(style="dark")
result = chart_gen.generate_security_gauge(
    score=85,
    token_name="MyToken",
    risk_flags=["High sell tax: 15%"],
)
# result.image_bytes → PNG bytes
# result.buffer       → BytesIO object
```

**Visual**: Donut gauge chart with:
- Colored ring (green 80+, amber 50-79, red <50)
- Center: `85/100` score display
- Right panel: Risk flags list or "No flags triggered"

### 2. Honeypot Badge
```python
result = chart_gen.generate_honeypot_badge(
    is_honeypot=False,
    token_name="MyToken",
    buy_tax=0.5,
    sell_tax=1.0,
    summary="Does not seem to be a honeypot.",
)
```

**Visual**: Large colored badge box:
- Green: "✅ SAFE — Does not seem to be a honeypot"
- Red: "🚨 HONEYPOT DETECTED! — Run away!"
- Tax rates displayed below

### 3. Holders Pie Chart
```python
result = chart_gen.generate_holders_pie(
    holders_data=[
        {"address": "0xDev...", "percentage": 8.5, "label": "Dev Wallet"},
        {"address": "0xLP...", "percentage": 25.0, "label": "LP Pool"},
    ],
    token_name="MyToken",
    total_holders=2500,
    concentration_level="low",
)
```

**Visual**: 
- Left: Colored pie chart with percentages
- Right: Distribution level indicator + top 5 breakdown

### 4. Liquidity Lock Chart
```python
result = chart_gen.generate_liquidity_chart(
    token_name="MyToken",
    locked_percentage=98.0,
    total_liquidity_usd=150000,
    total_locked_usd=147000,
    locks=[
        {"locker": "UNCX", "days_remaining": 730, "amount_usd": 147000},
    ],
)
```

**Visual**:
- Top: Horizontal lock percentage bar (green/amber/red)
- Bottom: Lock expiration timeline as horizontal bars

### 5. Summary Card
```python
result = chart_gen.generate_summary_card(
    token_name="MyToken",
    token_symbol="MTK",
    security_score=85,
    is_honeypot=False,
    concentration_level="low",
    locked_percentage=98.0,
)
```

**Visual**: 2×2 grid with all four metrics in cards with colored borders.

## Color Scheme
```
COLOR_GREEN  = #22c55e  — Safe/Positive
COLOR_RED    = #ef4444  — Danger/Negative
COLOR_AMBER  = #f59e0b  — Caution/Warning
COLOR_BLUE   = #3b82f6  — Neutral
COLOR_DARK_BG  = #1a1a2e  — Background
COLOR_CARD_BG  = #16213e  — Card surface
```

## Dependencies
- `matplotlib >= 3.8.0` with `Agg` backend (non-interactive)
- `numpy >= 1.26.0`

## Performance
- Charts generate in ~50-200ms each
- PNG output: typically 50-200KB per chart
- DPI: 120 (configurable)

---

# 📊 توثيق وحدة الرسوم البيانية (النسخة العربية)

## 📖 نظرة عامة
تُنشئ **رسوم بيانية جميلة** باستخدام **Matplotlib** بـ:
- ✅ ألوان داكنة احترافية
- ✅ تصدير مباشر إلى **PNG bytes** لـ Telegram
- ✅ 5 أنواع من الرسوم البيانية

---

## 🎨 الرسوم البيانية المتاحة

### 1️⃣ مقياس درجة الأمان (Security Gauge)

```python
chart_gen = ChartGenerator(style="dark")
result = chart_gen.generate_security_gauge(
    score=85,
    token_name="MyToken",
    risk_flags=["رسوم بيع عالية: 15%"],
)
# result.image_bytes → بيانات PNG جاهزة للإرسال
```

**الشكل**: رسم دائري بألوان متدرجة:
```
      ┌─────────────┐
      │ 85/100      │  ← درجة الأمان
      │   SAFE ✓    │
      │  ⬤⬤⬤⬤⬤     │  ← شريط ملون
      └─────────────┘
      المخاطر:
      • وقفة تداول
      • مالك مخفي
```

---

### 2️⃣ شارة الفخ (Honeypot Badge)

```python
result = chart_gen.generate_honeypot_badge(
    is_honeypot=False,
    token_name="MyToken",
    buy_tax=0.5,
    sell_tax=1.0,
    summary="يبدو آمناً — لا يوجد فخ",
)
```

**الشكل**: صندوق كبير ملون:

**إذا كان آمناً:**
```
┌────────────────────────────┐
│   ✅ آمن — لا فخ عسل       │
│   رسوم الشراء: 0.5%       │
│   رسوم البيع: 1.0%        │
└────────────────────────────┘
```

**إذا كان فخاً:**
```
┌────────────────────────────┐
│ 🚨 فخ مكتشف! اهرب!        │
│ لا يمكنك البيع!           │
└────────────────────────────┘
```

---

### 3️⃣ مخطط توزيع المالكين (Holders Pie Chart)

```python
result = chart_gen.generate_holders_pie(
    holders_data=[
        {"address": "0xDev...", "percentage": 8.5, "label": "محفظة المطور"},
        {"address": "0xLP...", "percentage": 25.0, "label": "مجموعة LP"},
    ],
    token_name="MyToken",
    total_holders=2500,
    concentration_level="low",
)
```

**الشكل**: رسم دائري (Pie Chart):
```
        المالكون
    ┌─────────────┐
    │  Dev 8.5% │  ← أجزاء ملونة
    │  LP 25%   │
    │  آخرون 66.5%
    └─────────────┘
    
    إجمالي المحافظ: 2500
    الحالة: موزع بشكل جيد ✅
```

---

### 4️⃣ مخطط قفل السيولة (Liquidity Lock Chart)

```python
result = chart_gen.generate_liquidity_chart(
    token_name="MyToken",
    locked_percentage=98.0,
    total_liquidity_usd=150000,
    total_locked_usd=147000,
    locks=[
        {"locker": "UNCX", "days_remaining": 730, "amount_usd": 147000},
    ],
)
```

**الشكل**: رسم بياني بالأشرطة:
```
السيولة
  │
  ├─ المقفول: 98% ████████████████████ آمن ✅
  │
  └─ المفتوح: 2% ██
  
  قفل UNCX: ينفتح بعد 730 يوم
  المبلغ المقفول: 147,000 دولار
```

---

### 5️⃣ بطاقة ملخصة (Summary Card)

```python
result = chart_gen.generate_summary_card(
    token_name="MyToken",
    token_symbol="MTK",
    security_score=85,
    is_honeypot=False,
    concentration_level="low",
    locked_percentage=98.0,
)
```

**الشكل**: شبكة 2×2 بـ 4 بطاقات:
```
┌────────────────────────────────┐
│ 🛡️ أمان      │ 🍯 فخ         │
│ 85/100        │ ✅ آمن        │
├────────────────────────────────┤
│ 👥 توزيع      │ 🔒 قفل        │
│ منخفض ✅      │ 98% ✅        │
└────────────────────────────────┘
```

---

## 🎨 الألوان المستخدمة:

```python
# الألوان الموحدة في البوت
COLOR_GREEN  = #22c55e       # ✅ آمن / إيجابي
COLOR_RED    = #ef4444       # ❌ خطر / سلبي
COLOR_AMBER  = #f59e0b       # ⚠️ تحذير / احذر
COLOR_BLUE   = #3b82f6       # ℹ️ معلومات
COLOR_DARK   = #1a1a2e       # الخلفية الداكنة
COLOR_CARD   = #16213e       # خلفية البطاقات
```

---

## 🚀 مثال عملي كامل:

```python
import asyncio
from charts import ChartGenerator

async def generate_all_charts():
    gen = ChartGenerator(style="dark")
    
    # 1️⃣ رسم درجة الأمان
    security_chart = gen.generate_security_gauge(
        score=88,
        token_name="TokenX",
        risk_flags=["رسوم بيع مرتفعة"]
    )
    
    # 2️⃣ رسم الفخ
    honeypot_chart = gen.generate_honeypot_badge(
        is_honeypot=False,
        token_name="TokenX",
        buy_tax=1.0,
        sell_tax=2.0,
        summary="لا يوجد فخ"
    )
    
    # 3️⃣ رسم التوزيع
    holders_chart = gen.generate_holders_pie(
        holders_data=[
            {"address": "0xaaa", "percentage": 15, "label": "Dev"},
            {"address": "0xbbb", "percentage": 35, "label": "LP"},
        ],
        token_name="TokenX",
        total_holders=5000,
        concentration_level="low"
    )
    
    # 4️⃣ رسم القفل
    liquidity_chart = gen.generate_liquidity_chart(
        token_name="TokenX",
        locked_percentage=95.0,
        total_liquidity_usd=200000,
        total_locked_usd=190000,
        locks=[{"locker": "UNCX", "days_remaining": 365, "amount_usd": 190000}]
    )
    
    # الآن لديك 4 صور PNG جاهزة للإرسال!
    print(f"✅ تم إنشاء {len([security_chart, honeypot_chart, holders_chart, liquidity_chart])} رسوم بيانية")
    
    return [security_chart, honeypot_chart, holders_chart, liquidity_chart]

# التشغيل
charts = asyncio.run(generate_all_charts())
# يمكن إرسالها الآن إلى Telegram
```

---

## 📈 الخصائص التقنية:

| الخاصية | القيمة |
|--------|--------|
| **الدقة (DPI)** | 120 |
| **الحجم النموذجي** | 50-200 KB |
| **وقت الإنشاء** | 50-200 ms |
| **الصيغة** | PNG |
| **الموضوع** | داكن احترافي |

---

## ⚙️ الاعتماديات:

```bash
# تثبيت المكتبات المطلوبة
pip install matplotlib>=3.8.0 numpy>=1.26.0
```

---

## 🔄 دورة الاستخدام في البوت:

```
1. المحللات تشغّل الفحوصات
        ↓
2. ChartGenerator ينشئ الصور
        ↓
3. PNG bytes تُحفظ في الذاكرة
        ↓
4. TelegramSender يُرسلها للقناة
        ↓
5. المستخدمون يرون صور جميلة! 📊
```

---