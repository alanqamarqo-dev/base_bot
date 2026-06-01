# 🛡️ Analyzers Module Documentation

## Overview
Five independent analyzers evaluate token safety from different angles. Results are aggregated into a weighted 0-100 score.

## Files
- [`analyzers/security_score.py`](../analyzers/security_score.py) — GoPlus Safety Score
- [`analyzers/honeypot_checker.py`](../analyzers/honeypot_checker.py) — Honeypot Detection
- [`analyzers/holders_checker.py`](../analyzers/holders_checker.py) — Holder Distribution
- [`analyzers/liquidity_checker.py`](../analyzers/liquidity_checker.py) — Liquidity Lock
- [`analyzers/github_checker.py`](../analyzers/github_checker.py) — GitHub Repository

---

## 1. Security Score (GoPlus)

**API**: `https://api.gopluslabs.io/api/v1/token_security?chain_id=8453`

### Checks Performed
| Check | Risk Impact |
|-------|-------------|
| `is_honeypot` | -40 points |
| `is_open_source` | -20 if false |
| `is_proxy` | -25 (upgradable contract) |
| `is_mintable` | -15 |
| `can_take_back_ownership` | -25 |
| `hidden_owner` | -30 |
| `transfer_pausable` | -20 |
| `is_blacklisted` | -30 |
| `slippage_modifiable` | -20 |
| `trading_cooldown` | -10 |
| `buy_tax > 10%` | -15 |
| `sell_tax > 10%` | -25 |

### Result
```python
result.score         # 0-100
result.is_safe       # True if score >= 70 and no flags
result.risk_flags    # List of triggered warnings
result.score_color   # Hex color (green/amber/red)
```

---

## 2. Honeypot Detection (Honeypot.is)

**API**: `https://api.honeypot.is/v2/check/8453/{address}`

### Detection
- Simulates buying and selling the token
- If sell tax ≥ 80% → classified as honeypot
- Falls back to simulation if token not pre-indexed

### Result
```python
result.is_honeypot    # True if can't sell
result.is_safe        # Not honeypot AND sell succeeds
result.buy_tax        # Buy tax percentage
result.sell_tax       # Sell tax percentage
result.status_text    # "✅ SAFE" or "🚨 HONEYPOT DETECTED"
```

---

## 3. Holder Distribution (Basescan)

**API**: `https://api.basescan.org/api` (requires API key for full holder data)

### Concentration Levels
| Level | Top Holder | Top 5 | Top 10 | Risk |
|-------|-----------|-------|--------|------|
| Low | < 20% | < 60% | < 60% | ✅ Safe |
| Medium | 20-40% | 60-70% | 60-75% | ⚠ Monitor |
| High | 40-50% | 70-80% | 75-90% | 🔴 Risky |
| Extreme | > 50% | > 80% | > 90% | 🚨 Rug-pull |

### Result
```python
result.creator_percentage    # Top holder %
result.top_5_percentage      # Top 5 combined %
result.top_10_percentage     # Top 10 combined %
result.concentration_level   # "low" | "medium" | "high" | "extreme"
result.chart_data            # Data for pie chart
```

---

## 4. Liquidity Lock (UNCX)

**API**: `https://app.uncx.network/api/locked/list` + DexScreener fallback

### Checks
- Finds LP pair via DexScreener
- Queries UNCX for lock data
- Falls back to heuristic analysis (age + liquidity)

### Result
```python
result.has_lock           # Any lock detected
result.locked_percentage  # % of liquidity locked
result.is_fully_locked    # ≥ 80% locked
result.lock_expiry_soon   # Unlocks within 14 days
result.unlock_timeline    # List of lock details
result.status_text        # "🔒 LOCKED 98%" etc.
```

---

## 5. GitHub Repository

**API**: `https://api.github.com` (optionally with token)

### Scoring
| Signal | Max Points |
|--------|-----------|
| Stars (≥100) | 25 |
| Forks (≥20) | 10 |
| Has README | 15 |
| Has LICENSE | 15 |
| Recent activity (≤7d) | 20 |
| Not a fork | 5 |
| Not archived | 5 |
| Has topics | 5 |

### Result
```python
result.stars              # GitHub stars
result.forks              # Fork count
result.has_readme         # README exists
result.has_license        # LICENSE exists
result.score              # 0-100 repository quality
result.is_legitimate      # Score ≥ 50
result.days_since_last_update  # Activity freshness
```

---

## Mock Analyzers

Each analyzer has a `Mock*` variant for testing:

```python
from analyzers import (
    MockSecurityScoreChecker,
    MockHoneypotChecker,
    MockHoldersChecker,
    MockLiquidityChecker,
    MockGitHubChecker,
)
```

---

# 🛡️ توثيق وحدة المحللات (النسخة العربية)

## 📖 نظرة عامة
**خمسة محللات مستقلة** تقيّم سلامة التوكن من زوايا مختلفة. تُدمج النتائج في **درجة واحدة موحدة من 0-100**.

---

## 1️⃣ درجة الأمان (GoPlus Security API)

**الـ API**: `https://api.gopluslabs.io/api/v1/token_security?chain_id=8453`

### الفحوصات المنفذة:

| الفحص | تأثير المخاطرة |
|-------|-------------|
| **honeypot** (فخ عسل) | -40 نقطة |
| **open_source** (مفتوح المصدر) | -20 إذا لم يكن |
| **proxy** (عقد قابل للتحديث) | -25 نقطة |
| **mintable** (يمكن طباعة عملات) | -15 نقطة |
| **take_back_ownership** (استرجاع الملكية) | -25 نقطة |
| **hidden_owner** (مالك مخفي) | -30 نقطة |
| **transfer_pausable** (إيقاف التحويلات) | -20 نقطة |
| **blacklisted** (مسجل بسجل أسود) | -30 نقطة |
| **slippage_modifiable** (تعديل الانزلاق) | -20 نقطة |
| **trading_cooldown** (فترة التوقف) | -10 نقاط |
| **رسوم شراء > 10%** | -15 نقطة |
| **رسوم بيع > 10%** | -25 نقطة |

### النتيجة:
```python
result.score           # 0-100 الدرجة
result.is_safe         # True إذا كانت آمنة
result.risk_flags      # قائمة التحذيرات
result.score_color     # اللون (أخضر/أصفر/أحمر)
result.score_label     # "آمن ✓" أو "تحذير ⚠" أو "خطر ✗"
```

---

## 2️⃣ كشف الفخ (Honeypot Detection)

**الـ API**: `https://api.honeypot.is/v2/check/8453/{address}`

### آلية الكشف:
```
1. محاكاة عملية شراء
2. محاكاة عملية بيع
3. إذا rسوم البيع ≥ 80% → يُصنّف كـ "فخ"
4. أو إذا فشلت عملية البيع → "فخ عسل!"
```

### النتيجة:
```python
result.is_honeypot      # True إذا كان فخ
result.is_safe          # آمن للبيع وليس فخاً
result.buy_tax          # % رسوم الشراء
result.sell_tax         # % رسوم البيع
result.status_text      # "✅ آمن" أو "🚨 فخ مكتشف!"
```

**معنى الفخ**: لا تستطيع بيع التوكن بعد شرائه (المحتال يأخذ أموالك)

---

## 3️⃣ توزيع المالكين (Holder Distribution)

**الـ API**: `https://api.basescan.org/api` (يحتاج API key)

### مستويات التركيز:

| المستوى | أكبر مالك | أكبر 5 | أكبر 10 | المخاطرة |
|--------|----------|--------|--------|---------|
| **منخفض** | < 20% | < 60% | < 60% | ✅ آمن |
| **متوسط** | 20-40% | 60-70% | 60-75% | ⚠️ راقب |
| **مرتفع** | 40-50% | 70-80% | 75-90% | 🔴 خطر |
| **أقصى** | > 50% | > 80% | > 90% | 🚨 احتيال |

### النتيجة:
```python
result.total_holders               # عدد المالكين الكلي
result.creator_percentage          # نسبة أكبر مالك
result.top_5_percentage            # نسبة أفضل 5
result.top_10_percentage           # نسبة أفضل 10
result.concentration_level         # مستوى التركيز
```

**لماذا هذا مهم؟** إذا كان مالك واحد يملك 80% يمكنه بيع كل شيء دفعة واحدة وتحطيم السعر!

---

## 4️⃣ قفل السيولة (Liquidity Lock)

**الـ API**: `https://app.uncx.network/api/locked/list`

### الفحوصات:
```
1. البحث عن زوج LP في DexScreener
2. التحقق من UNCX لوامات القفل
3. حساب النسبة المقفولة
4. التحقق من تاريخ الانفتاح
```

### النتيجة:
```python
result.has_lock                # هل يوجد قفل؟
result.locked_percentage       # % المقفول
result.is_fully_locked         # ≥ 80% مقفول؟
result.lock_expiry_soon        # ينفتح قريباً؟ (< 14 يوم)
result.unlock_timeline         # قائمة التواريخ
```

**معنى القفل**: السيولة محجوزة لفترة محددة، لا يمكن سحبها مبكراً.

---

## 5️⃣ مستودع GitHub

**الـ API**: `https://api.github.com`

### نظام الدرجات:

| المؤشر | الدرجة | الوصف |
|--------|--------|-------|
| **⭐ النجوم (≥100)** | +25 | اهتمام كبير بالمشروع |
| **🔀 Forks (≥20)** | +10 | نسخ من المشروع |
| **📄 README** | +15 | توثيق المشروع |
| **📜 LICENSE** | +15 | رخصة قانونية |
| **🔄 نشاط حديث (≤7 أيام)** | +20 | تحديثات مستمرة |
| **🏠 ليس fork** | +5 | مشروع أصلي |
| **📦 غير مؤرشف** | +5 | النشاط متواصل |
| **🏷️ Topics** | +5 | تصنيفات واضحة |

### النتيجة:
```python
result.stars                   # عدد النجوم
result.forks                   # عدد النسخ
result.has_readme              # يوجد توثيق؟
result.has_license             # يوجد رخصة؟
result.score                   # 0-100 درجة المستودع
result.is_legitimate           # مشروع حقيقي؟ (≥50)
result.days_since_last_update  # كم يوم من آخر تحديث
```

---

## 🧪 محللات وهمية (للاختبارات)

كل محلل له نسخة **وهمية** تُرجع نتائج ثابتة:

```python
from analyzers import (
    MockSecurityScoreChecker,      # يرجع درجات ثابتة
    MockHoneypotChecker,           # محاكاة آمن/خطر
    MockHoldersChecker,            # توزيع محاكى
    MockLiquidityChecker,          # قفل محاكى
    MockGitHubChecker,             # GitHub محاكى
)

# مثال:
checker = MockSecurityScoreChecker()
result = await checker.check("0x123")
# يرجع score > 80 و is_safe=True دائماً
```

---

## 📊 مثال عملي شامل:

```python
import asyncio
from analyzers import (
    SecurityScoreChecker,
    HoneypotChecker,
    HoldersChecker,
    LiquidityChecker,
    GitHubChecker
)

async def analyze_token():
    address = "0xTokenAddress"
    name = "MyToken"
    symbol = "MTK"
    
    # إنشاء المحللات
    security = SecurityScoreChecker()
    honeypot = HoneypotChecker()
    holders = HoldersChecker()
    liquidity = LiquidityChecker()
    github = GitHubChecker()
    
    # تشغيلها معاً
    results = await asyncio.gather(
        security.check(address, name, symbol),
        honeypot.check(address, name, symbol),
        holders.check(address, name, symbol),
        liquidity.check(address, name, symbol, 150000),
        github.check(address, name, symbol, "https://github.com/..."),
    )
    
    sec_result, hp_result, h_result, liq_result, gh_result = results
    
    # عرض النتائج
    print(f"أمان: {sec_result.score}/100")
    print(f"فخ: {'نعم 🚨' if hp_result.is_honeypot else 'لا ✅'}")
    print(f"توزيع: {h_result.concentration_level}")
    print(f"قفل: {liq_result.locked_percentage}%")
    print(f"GitHub: {gh_result.score}/100")

asyncio.run(analyze_token())
```

Mock analyzers return pre-configured safe results without making API calls.