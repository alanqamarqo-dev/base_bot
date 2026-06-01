# 📨 Telegram Bot Module Documentation

## Overview
Handles formatting and sending analysis results to a Telegram channel. Supports rich HTML messages, media groups with chart images, and both positive (detailed) and negative (warning) report formats.

## File
- [`telegram_bot/sender.py`](../telegram_bot/sender.py)

## Setup

### 1. Create a Telegram Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token (e.g., `123456:ABC-DEF1234ghikl`)

### 2. Get Channel ID
- For public channels: use `@channel_name`
- For private channels: use the numeric ID (e.g., `-1001234567890`)
- Add your bot as an **admin** to the channel

### 3. Configure
```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghikl
TELEGRAM_CHANNEL_ID=@your_channel
```

## Usage

### Initialize
```python
from telegram_bot import TelegramSender
from charts import ChartGenerator

sender = TelegramSender(
    bot_token="your_token",
    channel_id="@your_channel",
    chart_generator=ChartGenerator(style="dark"),
)
```

### Send Positive Token (with charts)
```python
await sender.send_positive_token(
    token_data={"name": "MyToken", "symbol": "MTK", "address": "0x...", ...},
    security_result=security_score_result,
    honeypot_result=honeypot_result,
    holders_result=holders_result,
    liquidity_result=liquidity_result,
    github_result=github_result,
    overall_score=85,
)
```

This sends a **media group** of 4 images:
1. 🔐 Security Score Gauge
2. 🍯 Honeypot Badge
3. 👥 Holders Pie Chart
4. 🔒 Liquidity Lock Chart

With a detailed HTML caption on the first image.

### Send Negative Token (text only)
```python
await sender.send_negative_token(
    token_data={...},
    security_result=...,
    honeypot_result=...,
    holders_result=...,
    liquidity_result=...,
    github_result=...,
)
```

Sends a concise **text-only warning** with risk summary.

### Daily Summary
```python
await sender.send_daily_summary(
    date_str="2026-05-31",
    total_tokens=25,
    positive_count=5,
    negative_count=20,
    positive_tokens=[...],
)
```

### Simple Messages
```python
await sender.send_text("Hello, world!")
await sender.send_photo(png_bytes, caption="Chart")
```

## Message Formats

### Positive Token Message
```
🚀 TokenName ($SYMBOL) 🚀
🟢 OVERALL SCORE: 85/100 — SAFE

0xAddress...

💰 Market Data:
  💰 Liquidity: $150,000
  📈 Market Cap: $500,000

🛡️ 1. Security Score: 90/100
  ✅ No flags triggered
  • Buy Tax: 0.5% | Sell Tax: 1.0%

🍯 2. Honeypot Check:
  ✅ SAFE – Does not seem to be a honeypot
  • Buy Tax: 0.5% | Sell Tax: 1.0%

👥 3. Holder Distribution:
  ✅ Well distributed
  • Total Holders: 2500
  • Top Holder: 8.5%
  • Top 10: 55.0%

🔒 4. Liquidity Lock:
  🟢 LOCKED 98% – Safe
  • Total Liquidity: $150,000
  • Locked: 98.0% ($147,000)
  • UNCX: 730d remaining

💻 5. GitHub Repository:
  🟢 Active & legitimate repository
  • Stars: 42 | Forks: 12
  • Score: 85/100

🔗 View on DexScreener
```

### Negative Token Warning
```
💀 TokenName ($SYMBOL) 💀
🔴 WARNING: Suspicious Token Detected

0xAddress...

⚠ Risk Summary:
🔴 Security Score: 15/100
  ⚠ Honeypot detected
  ⚠ Contract not open-source
🔴 HONEYPOT DETECTED: Cannot sell!
🔴 Liquidity: NOT SAFELY LOCKED (0%)
🔴 No GitHub repository found

❌ Verdict: HIGH RISK — Avoid this token
```

---

# 📨 توثيق وحدة بوت تيليجرام (النسخة العربية)

## 📖 نظرة عامة
تتعامل هذه الوحدة مع **صياغة وإرسال نتائج التحليل** إلى قنوات تيليجرام. تدعم:
- رسائل **HTML غنية** بالصيغ المتقدمة
- مجموعات **صور وملفات بيانية**
- تنسيقات مختلفة للـ tokens الجيدة والسيئة

---

## 🔧 الإعداد الكامل للربط بـ Telegram

### المرحلة الأولى: إنشاء بوت Telegram

#### الخطوة 1: فتح BotFather
```
1. افتح تطبيق Telegram على الهاتف أو الويب
2. ابحث عن: @BotFather (روبوت رسمي من Telegram)
3. اضغط "ابدأ" أو ارسل /start
```

#### الخطوة 2: إنشاء بوت جديد
```
1. اكتب: /newbot
2. سيطلب اسم البوت (مثال: "Token Scanner Bot")
3. سيطلب username فريد (مثال: "token_scanner_base_bot")
   ⚠️ يجب أن ينتهي بـ _bot
4. سيعطيك رسالة بفيها:
   
   "Done! Congratulations on your new bot. 
    You will find it at t.me/token_scanner_base_bot. 
    You can now add a description, about section and profile picture 
    for your bot, see /help for a list of commands."
```

#### الخطوة 3: نسخ الـ Token
```
سيظهر لك سطر مثل:
"Use this token to access the HTTP API:
 123456789:ABCdefGHIjklmnoPQRstuvWXYZabcdef_ghijk"

⭐ هذا هو TELEGRAM_BOT_TOKEN
احفظه في مكان آمن!
```

---

### المرحلة الثانية: إنشاء القناة وإضافة البوت

#### الخطوة 1: إنشاء قناة Telegram
```
1. في Telegram اضغط الـ Menu (☰ أو ≡)
2. اختر "إنشاء مجموعة أو قناة"
3. اختر "قناة" (Channel)
4. اسم القناة (مثال: "Token Scanner Results")
5. وصف القناة (اختياري)
6. اختر "ربط واحد أم متعدد":
   - اختر واحد فقط للإرسال
7. اضغط "إنشاء"
```

#### الخطوة 2: الحصول على Channel ID

**للقنوات العامة (Public):**
```
1. توجه للقناة
2. استخدم الـ channel name مباشرة
   مثال: @token_scanner_results
   
# في .env ضع:
TELEGRAM_CHANNEL_ID=@token_scanner_results
```

**للقنوات الخاصة (Private):**
```
1. توجه للقناة
2. اضغط على اسم القناة أعلى الشاشة
3. اضغط "معلومات القناة"
4. ستجد الرقم الفريد (ID) مثل: -1001234567890

# في .env ضع:
TELEGRAM_CHANNEL_ID=-1001234567890
```

#### الخطوة 3: إضافة البوت كـ Admin
```
1. افتح القناة
2. اضغط على اسمها للدخول للإعدادات
3. اختر "الأعضاء" أو "Members"
4. اختر "إضافة عضو"
5. ابحث عن اسم بوتك (token_scanner_base_bot)
6. اختره
7. اختر "قدم إذن المسؤول" (Make Admin)
8. تأكد أنه لديه صلاحيات:
   ✅ إرسال الرسائل (Send Messages)
   ✅ تحرير الرسائل (Edit Messages)
   ✅ حذف الرسائل (Delete Messages)
   ✅ إضافة أعضاء جدد (Invite Users)
```

---

### المرحلة الثالثة: التكوين في البرنامج

#### الخطوة 1: إنشاء ملف .env
```bash
# في مجلد project/sr
cp .env.example .env
```

#### الخطوة 2: ملء البيانات
```env
# ==================== Telegram Configuration ====================
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmnoPQRstuvWXYZabcdef_ghijk
TELEGRAM_CHANNEL_ID=@token_scanner_results

# أو للقناة الخاصة:
# TELEGRAM_CHANNEL_ID=-1001234567890

# ==================== API Keys ====================
# اختياري — للحصول على معلومات أفضل
BASESCAN_API_KEY=your_basescan_api_key_here
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# ==================== Settings ====================
MAX_TOKENS_PER_SCAN=30
MIN_LIQUIDITY_USD=1000
ENABLE_CHARTS=true
LOG_LEVEL=INFO
```

---

## 💬 أنواع الرسائل التي يرسلها البوت

### النوع الأول: رسالة Token إيجابي ✅

```
🚀 MyToken ($MTK) 🚀
🟢 الدرجة الإجمالية: 85/100 — آمن

العنوان: 0x1234567890abcdef...

💰 بيانات السوق:
  💰 السيولة: 150,000 دولار
  📈 رأس المال السوقي: 500,000 دولار

🛡️ 1. درجة الأمان: 90/100
  ✅ لا توجد علامات تحذير
  • رسوم الشراء: 0.5% | رسوم البيع: 1.0%

🍯 2. فحص الفخ:
  ✅ آمن — ليس فخ عسل
  • رسوم الشراء: 0.5% | رسوم البيع: 1.0%

👥 3. توزيع المالكين:
  ✅ موزع بشكل جيد
  • إجمالي المالكين: 2500 محفظة
  • أكبر مالك: 8.5%
  • أكبر 10: 55.0%

🔒 4. قفل السيولة:
  🟢 مقفول 98% — آمن
  • إجمالي السيولة: 150,000 دولار
  • المقفول: 98.0% (147,000 دولار)
  • فترة القفل: 730 يوم متبقية

💻 5. مستودع GitHub:
  🟢 مستودع نشط وموثوق
  • ⭐ نجوم: 42 | Forks: 12
  • درجة المستودع: 85/100

🔗 اعرض على DexScreener

📊 مرفقة 4 رسوم بيانية أسفله!
```

### النوع الثاني: رسالة Token سيء ⚠️

```
💀 BadToken ($BAD) 💀
🔴 تحذير: تم اكتشاف Token مريب!

العنوان: 0xabcdef1234567890...

⚠️ ملخص المخاطر:
🔴 درجة الأمان: 15/100
  • لا يوجد كود مفتوح المصدر
  • مالك مخفي (Hidden Owner)
  
🔴 فخ عسل مكتشف: لا يمكن البيع!
🔴 السيولة: غير آمنة (0% مقفول)
🔴 لا يوجد مستودع GitHub

❌ الحكم النهائي: خطر جداً — تجنب هذا التوكن!
```

### النوع الثالث: ملخص يومي 📊

```
📊 ملخص الفحص اليومي — 2026-06-01

إجمالي التوكنات المكتشفة: 25 توكن
✅ توكنات آمنة: 5 توكنات
⚠️ توكنات مريبة: 20 توكن

📈 التوكنات الآمنة:
1. TokenA ($TKA) — درجة: 88/100
2. TokenB ($TKB) — درجة: 82/100
3. TokenC ($TKC) — درجة: 79/100
4. TokenD ($TKD) — درجة: 76/100
5. TokenE ($TKE) — درجة: 74/100

🔗 تفاصيل على DexScreener...
```

---

## 🚀 كيفية تشغيل البوت

### على الكمبيوتر الشخصي (للاختبار):

```bash
# 1. توجه للمجلد
cd e:\base_bot\project\sr

# 2. تفعيل البيئة الافتراضية
venv\Scripts\activate

# 3. تثبيت المكتبات إن لم تُثبت
pip install -r requirements.txt

# 4. تشغيل فحص واحد للاختبار
python main.py check 0xTokenAddress --name "Token" --symbol "TKN"

# 5. أو تشغيل فحص يومي كامل
python main.py scan
```

### على سيرفر (24/7):

#### الخيار الأول: Ubuntu/Linux (باستخدام Cron):
```bash
# تحرير crontab
crontab -e

# أضف هذا السطر لتشغيل البوت يومياً في الساعة 6 صباحاً UTC:
0 6 * * * cd /path/to/project/sr && /path/to/venv/bin/python main.py scan >> scan.log 2>&1

# لحفظ الملف: Ctrl+X ثم Y ثم Enter
```

#### الخيار الثاني: Windows (باستخدام Task Scheduler):
```
1. افتح Windows Task Scheduler
2. اختر "Create Basic Task"
3. اسم المهمة: "Token Scanner Daily"
4. الجدولة: يومياً في الساعة 6 صباحاً
5. الإجراء: تشغيل برنامج
6. البرنامج: python.exe
7. الحجج: C:\path\to\main.py scan
8. ابدأ من: C:\path\to\project\sr
9. حفظ
```

---

## 🔍 استكشاف الأخطاء

### المشكلة: البوت لا يرسل الرسائل

**الحل:**
```
1. تحقق من الـ Token صحيح:
   - نسخه من BotFather مجدداً
   - تأكد من عدم وجود مسافات

2. تحقق من الـ Channel ID:
   - جرب اسم القناة @channel_name
   - أو الـ numeric ID: -100xxxxx

3. تحقق أن البوت admin:
   - اذهب للقناة → الإعدادات → الأعضاء
   - ابحث عن اسم البوت
   - تأكد أن له صلاحيات كاملة

4. تحقق من ملف .env:
   - لا توجد مسافات زائدة
   - لا توجد علامات اقتباس إضافية
```

### المشكلة: الرسوم البيانية لا تظهر

```
1. تحقق ENABLE_CHARTS=true في .env
2. تثبيت matplotlib:
   pip install matplotlib>=3.8.0
3. تحقق من مساحة التخزين (قد يحتاج 500MB)
```

### المشكلة: خطأ في الاتصال بـ APIs

```
1. تحقق من الإنترنت
2. تحقق من الـ firewall
3. اعرض الأخطاء:
   LOG_LEVEL=DEBUG في .env
```

---

## 📚 ملخص البيانات المرسلة

| البيان | المصدر | الوصف |
|-------|-------|-------|
| **Security Score** | GoPlus API | درجة أمان 0-100 |
| **Honeypot Check** | Honeypot.is API | هل يمكن البيع؟ |
| **Holders** | Basescan API | توزيع المحافظ |
| **Liquidity** | DexScreener API | نسبة القفل |
| **GitHub** | GitHub API | نشاط المستودع |
| **Charts** | Matplotlib | رسوم بيانية |

---

## ✅ قائمة التحقق النهائية

قبل تشغيل البوت تأكد من:
- [ ] إنشاء بوت عبر @BotFather
- [ ] نسخ الـ Token بشكل صحيح
- [ ] إنشاء قناة Telegram
- [ ] إضافة البوت كـ Admin
- [ ] ملء ملف .env بالبيانات الصحيحة
- [ ] تثبيت جميع المكتبات
- [ ] اختبار البوت بـ `python main.py test`
- [ ] التحقق من الرسائل في القناة
- [ ] جدولة للتشغيل اليومي (اختياري)

## Rate Limiting
- The orchestrator adds 1s delay between positive sends, 0.5s between negative
- Telegram limit: ~30 messages/second for bots
- Media groups: max 10 items per group

## Fallback Behavior
If media group sending fails, the bot falls back to **text-only** HTML message.