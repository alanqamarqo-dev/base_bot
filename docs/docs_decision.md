# ⚡ توثيق نظام القرار (Decision Engine)

## نظرة عامة

نظام القرار يحول التحليلات الخام إلى قرار نهائي: **SKIP** أو **WATCH** أو **EARLY GEM**.

## هيكل المجلد

```
decision/
├── __init__.py        # تصدير المكونات
├── scoring.py         # نظام الدرجات 0-100
└── classifier.py      # تصنيف SKIP/WATCH/EARLY GEM
```

---

## 1. Momentum Scorer (`scoring.py`)

### المعادلة

```
Momentum Score = 
    Security Score   × 0.25   (GoPlus 0-100)
  + Liquidity Score  × 0.20   (السيولة بالدولار)
  + Volume Score     × 0.20   (حجم 5 دقائق)
  + Buy/Sell Ratio   × 0.15   (نسبة الشراء/البيع)
  + Holders Score    × 0.10   (توزيع الحاملين)
  + Age Score        × 0.10   (العمر بالثواني)
  + Smart Money      × bonus  (+10 إن وجد)
  - Whale Penalty    × penalty (-10 إلى -30)
  - Rug Penalty      × penalty (-50 إن وجد)
```

### حساب كل مكون

#### Liquidity Score
| السيولة | الدرجة |
|---------|--------|
| > $100,000 | 100 |
| > $50,000 | 90 |
| > $20,000 | 70 |
| > $10,000 | 50 |
| > $5,000 | 30 |
| > $1,000 | 10 |

#### Volume Score (5min)
| الحجم | الدرجة |
|-------|--------|
| > $50,000 | 100 |
| > $20,000 | 85 |
| > $10,000 | 65 |
| > $5,000 | 40 |
| > $1,000 | 20 |

#### Buy/Sell Ratio
| النسبة | الدرجة |
|--------|--------|
| > 3.0x | 100 |
| > 2.0x | 80 |
| > 1.5x | 65 |
| 1.0x | 50 |
| < 0.5x | 10 |

#### Holders Concentration
| التوزيع | الدرجة |
|---------|--------|
| low | 100 |
| medium | 60 |
| high | 30 |
| extreme | 0 |

#### Age Score
- يصل للدرجة الكاملة (100) بعد 5 دقائق (300 ثانية)
- `min(age_seconds / 300 * 100, 100)`

---

## 2. Decision Classifier (`classifier.py`)

### الفئات

| القرار | الرمز | الوصف |
|--------|-------|-------|
| `SKIP` | ❌ | خطر عالي - تجاهل |
| `WATCH` | 👀 | فيه إمكانية - راقب |
| `EARLY_GEM` | 💎 | إشارة قوية - تصرف |

### مصفوفة القرار

| المعيار | SKIP | WATCH | EARLY GEM |
|---------|------|-------|-----------|
| Security Score | < 40 | 40 - 70 | > 70 |
| Honeypot | YES | No + Tax | NO |
| Liquidity | < $1,000 | $1k - $10k | > $10,000 |
| Buy/Sell Ratio | < 0.5 | 0.5 - 1.5 | > 1.5 |
| Volume 5min | < $500 | $500 - $5k | > $5,000 |
| Age | < 30s | 30s - 5min | > 5min |
| Momentum Score | < 30 | 30 - 60 | > 60 |

### نقاط التوقف الفورية (Hard Stops)

إذا تحقق أي من هذه الشروط، القرار فوراً = `SKIP`:
- 🚨 Honeypot detected
- 🚨 Blacklist detected
- 🚨 Liquidity removed (>50%)

### مثال

```python
from decision.scoring import MomentumScorer
from decision.classifier import DecisionEngine

scorer = MomentumScorer()
classifier = DecisionEngine()

# حساب الدرجة
score = scorer.calculate(
    token_address="0x...",
    security_score=85,
    liquidity_usd=25000,
    volume_5m_usd=15000,
    buy_sell_ratio=2.1,
    holders_concentration="low",
    age_seconds=360,
    smart_money_detected=True,
)

# تصنيف
result = classifier.classify(
    momentum_result=score,
    is_honeypot=False,
    has_proxy=False,
    is_mintable=False,
    is_blacklisted=False,
)

print(f"{result.decision.emoji} {result.decision.label}")
print(f"Score: {result.momentum_score}/100")
print(f"Confidence: {result.confidence:.0%}")
```

### المخرجات
```
💎 EARLY GEM
Score: 87/100
Confidence: 83%
Positive Signals:
  - Security score: 85/100
  - Liquidity: $25,000
  - Buy/Sell ratio: 2.1x
  - Volume 5min: $15,000
  - Age: 6min+
  - Smart money detected