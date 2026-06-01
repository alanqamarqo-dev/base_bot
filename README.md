# 🚀 Base Chain Token Scanner Bot

A comprehensive Telegram bot that automatically scans, analyzes, and reports on new tokens launched on the **Base** blockchain every day.

## 📋 Features

| Feature | Description |
|---------|-------------|
| 🔍 **Token Discovery** | Scans DexScreener API for newly listed Base chain tokens |
| 🛡️ **Security Score** | GoPlus Security API integration — 0-100 safety gauge with risk flags |
| 🍯 **Honeypot Detection** | Honeypot.is API — detects if token prevents selling |
| 👥 **Holder Distribution** | Analyzes wallet concentration via Basescan/CoinGecko |
| 🔒 **Liquidity Lock** | Verifies UNCX lock status and lock timelines |
| 💻 **GitHub Analysis** | Scores repository legitimacy (stars, activity, license) |
| 📊 **Visual Charts** | Generates gauge, pie, timeline, and badge charts |
| 📨 **Telegram Delivery** | Sends positive tokens with full charts, negative with warnings |
| 💾 **Persistent Storage** | SQLite database for token history and daily scan tracking |

## 🏗️ Architecture

```
project/sr/
├── main.py                    # Orchestrator: scan → analyze → chart → send
├── scanner/
│   ├── base_scanner.py        # DexScreener token discovery
│   └── dex_scanner.py         # Extended DexScreener queries
├── analyzers/
│   ├── security_score.py      # GoPlus Safety Score (0-100 gauge)
│   ├── honeypot_checker.py    # Honeypot.is detection
│   ├── holders_checker.py     # Holder distribution analysis
│   ├── liquidity_checker.py   # UNCX liquidity lock verification
│   └── github_checker.py      # GitHub repository legitimacy
├── charts/
│   └── chart_generator.py     # Matplotlib charts (gauge, pie, timeline)
├── database/
│   └── storage.py             # SQLite storage layer
├── telegram_bot/
│   └── sender.py              # Telegram message formatting & sending
├── test/                      # Unit & integration tests
├── docs/                      # Documentation per module
├── requirements.txt           # Python dependencies
├── .env.example               # Environment configuration template
└── README.md                  # This file
```

## 🔧 Installation

### Prerequisites
- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- (Optional) Basescan API Key
- (Optional) GitHub Personal Access Token

### Setup

```bash
# 1. Clone the project
cd project/sr

# 2. Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your Telegram bot token and channel ID
```

### Configuration (.env)

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghikl
TELEGRAM_CHANNEL_ID=@your_channel
BASESCAN_API_KEY=your_key_here      # Optional
GITHUB_TOKEN=ghp_xxxx               # Optional
MAX_TOKENS_PER_SCAN=30
MIN_LIQUIDITY_USD=1000
```

## 🚀 Usage

### Command Line

```bash
# Run daily scan (finds all new Base tokens and analyzes them)
python main.py scan

# Check a specific token
python main.py check 0xTokenAddress --name "Token Name" --symbol "TKN"

# Run test mode (scans only 5 tokens)
python main.py test

# Show database statistics
python main.py stats
```

### Python API

```python
import asyncio
from main import BaseBotOrchestrator

async def custom_scan():
    bot = BaseBotOrchestrator()
    result = await bot.run_single_token_check(
        "0xTokenAddress",
        token_name="MyToken",
        token_symbol="MTK"
    )
    print(f"Score: {result.overall_score}/100")
    print(f"Safe: {result.is_positive}")
    await bot.close()

asyncio.run(custom_scan())
```

### Cron / Scheduler

To run daily scans automatically:

```bash
# Linux crontab (runs every day at 06:00 UTC)
0 6 * * * cd /path/to/project/sr && python main.py scan >> scan.log 2>&1

# Windows Task Scheduler
# Create a task to run: python main.py scan
```

## 📊 Scoring System

Tokens are scored on a **weighted 0-100 scale**:

| Analysis | Weight | Criteria |
|----------|--------|----------|
| Security Score | 30% | GoPlus API: open-source, proxy, mintable, taxes |
| Honeypot Check | 25% | Can buy AND sell the token? |
| Holder Distribution | 20% | Concentration of top wallets |
| Liquidity Lock | 20% | Percentage locked + lock duration |
| GitHub | 5% | Stars, activity, license, README |

**Positive threshold**: Overall score ≥ 60, not a honeypot, security ≥ 40

## 📸 Chart Outputs

For each **positive** token, the bot generates and sends:

| Chart | Description |
|-------|-------------|
| 🔐 **Security Gauge** | Donut chart showing 0-100 score with risk flags |
| 🍯 **Honeypot Badge** | Green (safe) or Red (honeypot) indicator with tax rates |
| 👥 **Holders Pie** | Distribution pie chart with concentration analysis |
| 🔒 **Liquidity Chart** | Lock percentage bar + expiration timeline |

## 📡 API Integrations

| Service | Endpoint | Rate Limits |
|---------|----------|-------------|
| [DexScreener](https://dexscreener.com) | Free, no key | ~60 req/min |
| [GoPlus Security](https://gopluslabs.io) | Free, no key | ~60 req/min |
| [Honeypot.is](https://honeypot.is) | Free, no key | ~30 req/min |
| [Basescan](https://basescan.org) | Free API key | 5 req/sec |
| [GitHub](https://github.com) | Optional token | 60 req/hr (unauthenticated) |

## 🧪 Testing

```bash
# Run all tests
pytest test/ -v

# Run specific test file
pytest test/test_analyzers.py -v

# Run with coverage
pytest test/ --cov=. --cov-report=html
```

## 📄 License

MIT License

## ⚠️ Disclaimer

This bot is for informational purposes only. It does not constitute financial advice. Always do your own research (DYOR) before investing in any cryptocurrency token. The safety scores and analyses are automated approximations and may not catch all risks.

---

# 🚀 بوت ماسح التوكنات على سلسلة Base (النسخة العربية)

## 📖 حول البوت
**بوت تيليجرام ذكي** يقوم بـ:
- 🔍 البحث عن توكنات جديدة يومياً
- 🛡️ تحليل أمان التوكن
- 🍯 الكشف عن الفخاخ
- 👥 دراسة توزيع المالكين
- 🔒 التحقق من قفل السيولة
- 💻 تقييم مستودع GitHub
- 📊 إرسال رسوم بيانية جميلة
- 💾 تخزين البيانات في قاعدة بيانات

---

## 🎯 الميزات الرئيسية

| الميزة | الشرح |
|--------|--------|
| 🔍 **اكتشاف التوكنات** | يبحث عن توكنات جديدة على Base |
| 🛡️ **درجة الأمان** | يعطي درجة 0-100 لكل توكن |
| 🍯 **كشف الفخ** | يكتشف الفخاخ والاحتيالات |
| 👥 **التوزيع** | يحلل توزيع المحافظ |
| 🔒 **القفل** | يتحقق من قفل السيولة |
| 💻 **GitHub** | يقيّم المشاريع الحقيقية |
| 📊 **رسوم بيانية** | يرسل صور جميلة |
| 📨 **تيليجرام** | يُرسل النتائج مباشرة |

---

## 📋 خطوات التثبيت

### 1. المتطلبات:
```
• Python 3.10+
• توكن بوت من @BotFather
• (اختياري) مفاتيح API
```

### 2. التثبيت:
```bash
# 1. الذهاب للمجلد
cd project/sr

# 2. إنشاء بيئة افتراضية
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. تجهيز الإعدادات
cp .env.example .env
# ثم قم بتعديل .env وإضافة بيانات التيليجرام
```

### 3. الإعدادات (.env):
```env
# Telegram
TELEGRAM_BOT_TOKEN=توكنك_هنا
TELEGRAM_CHANNEL_ID=@اسم_القناة

# APIs (اختياري)
BASESCAN_API_KEY=المفتاح_هنا
GITHUB_TOKEN=التوكن_هنا

# الإعدادات
MAX_TOKENS_PER_SCAN=30
MIN_LIQUIDITY_USD=1000
```

---

## 🚀 طرق الاستخدام

### من سطر الأوامر:
```bash
# فحص يومي كامل
python main.py scan

# فحص توكن واحد
python main.py check 0xTokenAddress --name "اسم" --symbol "رمز"

# اختبار بـ 5 توكنات فقط
python main.py test

# عرض الإحصائيات
python main.py stats
```

### من الكود:
```python
import asyncio
from main import BaseBotOrchestrator

async def فحص_مخصص():
    bot = BaseBotOrchestrator()
    
    result = await bot.run_single_token_check(
        "0xTokenAddress",
        token_name="MyToken",
        token_symbol="MTK"
    )
    
    print(f"الدرجة: {result.overall_score}/100")
    print(f"آمن: {result.is_positive}")
    
    await bot.close()

asyncio.run(فحص_مخصص())
```

### جدولة التشغيل اليومي:

**Linux (Crontab):**
```bash
# كل يوم في الساعة 6 صباحاً
0 6 * * * cd /path/to/project/sr && python main.py scan >> scan.log 2>&1
```

**Windows (Task Scheduler):**
- فتح Task Scheduler
- إنشاء مهمة جديدة
- التشغيل يومياً الساعة 6 صباحاً
- الأمر: `python.exe main.py scan`

---

## 📊 نظام التقييم

الدرجة الكلية من **0 إلى 100** مقسمة كالتالي:

| المحلل | النسبة | المعايير |
|--------|--------|----------|
| 🛡️ الأمان | 30% | مفتوح المصدر، قابلية الترقية، الرسوم |
| 🍯 الفخ | 25% | هل يمكن الشراء والبيع؟ |
| 👥 التوزيع | 20% | تركيز المالكين |
| 🔒 القفل | 20% | نسبة القفل والفترة |
| 💻 GitHub | 5% | نجوم المستودع والنشاط |

**توكن جيد إذا:**
- ✅ الدرجة ≥ 60
- ✅ ليس فخاً
- ✅ الأمان ≥ 40

---

## 📸 الرسوم البيانية المُرسلة

للتوكنات الجيدة، يُرسل البوت 4 رسوم:

| الرسم | الوصف |
|-------|--------|
| 🔐 **مقياس الأمان** | درجة 0-100 مع التحذيرات |
| 🍯 **شارة الفخ** | أخضر (آمن) أو أحمر (فخ) |
| 👥 **توزيع المالكين** | رسم دائري يوضح التوزيع |
| 🔒 **قفل السيولة** | شريط القفل والتواريخ |

---

## 🌐 الخدمات المدمجة

| الخدمة | الـ API | الحد |
|--------|--------|------|
| DexScreener | مجاني | 60 طلب/دقيقة |
| GoPlus | مجاني | 60 طلب/دقيقة |
| Honeypot.is | مجاني | 30 طلب/دقيقة |
| Basescan | مفتاح | 5 طلب/ثانية |
| GitHub | مفتاح | 60 طلب/ساعة |

---

## 🧪 الاختبارات

```bash
# تشغيل جميع الاختبارات
pytest test/ -v

# اختبار ملف واحد
pytest test/test_analyzers.py -v

# قياس التغطية
pytest test/ --cov=. --cov-report=html
```

---

## 📚 التوثيقات التفصيلية

كل وحدة لها توثيق عربي كامل:

- **[📡 الماسح](docs/docs_scanner.md)** - اكتشاف التوكنات
- **[🛡️ المحللات](docs/docs_analyzers.md)** - التحليلات الخمس
- **[📊 الرسوم](docs/docs_charts.md)** - إنشاء الصور
- **[💾 قاعدة البيانات](docs/docs_database.md)** - التخزين
- **[📨 تيليجرام](docs/docs_telegram_bot.md)** - الإرسال
- **[🧪 الاختبارات](docs/docs_test.md)** - الاختبار

---

## ✅ قائمة التحقق النهائية

قبل التشغيل تأكد من:
- [ ] إنشاء بوت في Telegram
- [ ] نسخ التوكن بشكل صحيح
- [ ] إنشاء قناة وإضافة البوت كـ Admin
- [ ] ملء ملف .env
- [ ] تثبيت المكتبات
- [ ] تشغيل الاختبارات: `pytest test/`
- [ ] اختبار البوت: `python main.py test`
- [ ] التحقق من الرسائل بالقناة

---

## 🎯 الخطوات التالية

بعد التثبيت يمكنك:

1. **اختبر البوت:**
   ```bash
   python main.py test
   ```

2. **شغّل فحص يومي:**
   ```bash
   python main.py scan
   ```

3. **جدول التشغيل التلقائي** (يومياً)

4. **راقب النتائج** في قناة Telegram

---

## 🚨 تحذيرات هامة

⚠️ **هذا البوت لأغراض إعلامية فقط**
- لا يُشكل نصيحة مالية
- بحث واحدة (DYOR) قبل الاستثمار
- التقييمات آلية وقد تكون غير كاملة
- لا تعتمد عليه بنسبة 100%

---

## 📞 الدعم والمساعدة

إذا واجهت مشاكل:

1. تحقق من الأخطاء في `base_bot.log`
2. جرّب `python main.py test`
3. تأكد من الإنترنت والـ Firewall
4. تحقق من بيانات `.env`
5. اقرأ التوثيقات في مجلد `docs/`

---