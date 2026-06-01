# 💾 Database Module Documentation

## Overview
SQLite-based persistent storage for token tracking, analysis history, and daily scan records.

## File
- [`database/storage.py`](../database/storage.py)

## Schema

### `tokens` Table
Stores all discovered token information.

| Column | Type | Description |
|--------|------|-------------|
| `address` | TEXT PK | Contract address |
| `name` | TEXT | Token name |
| `symbol` | TEXT | Ticker symbol |
| `chain` | TEXT | "base" |
| `description` | TEXT | Project description |
| `website` | TEXT | Official website |
| `twitter` | TEXT | Twitter/X URL |
| `telegram` | TEXT | Telegram group |
| `discord` | TEXT | Discord invite |
| `github_url` | TEXT | GitHub repo URL |
| `market_cap` | REAL | Market cap (USD) |
| `price_usd` | REAL | Current price (USD) |
| `liquidity_usd` | REAL | Liquidity (USD) |
| `volume_24h` | REAL | 24h volume (USD) |
| `price_change_24h` | REAL | 24h price change (%) |
| `pair_address` | TEXT | Main pair contract |
| `dex_url` | TEXT | DexScreener link |
| `first_seen` | TIMESTAMP | First discovery |
| `last_seen` | TIMESTAMP | Last update |
| `is_positive` | INTEGER | 1 = positive token |

### `analyses` Table
Stores individual analysis results (JSON).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `token_address` | TEXT FK | → tokens.address |
| `analysis_type` | TEXT | "security", "honeypot", "holders", "liquidity", "github" |
| `result_json` | TEXT | Full analysis result as JSON |
| `is_safe` | INTEGER | 1 = this check passed |
| `score` | INTEGER | Score for this check |
| `created_at` | TIMESTAMP | When analyzed |

### `daily_scans` Table
Tracks each daily scan run.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `scan_date` | TEXT | Date string (YYYY-MM-DD) |
| `tokens_found` | INTEGER | Total tokens discovered |
| `positive_count` | INTEGER | Positive classifications |
| `negative_count` | INTEGER | Negative classifications |
| `status` | TEXT | "running" or "completed" |
| `created_at` | TIMESTAMP | When scan started |

### `scan_tokens` Table
Join table linking scans to tokens.

| Column | Type | Description |
|--------|------|-------------|
| `scan_id` | INTEGER PK FK | → daily_scans.id |
| `token_address` | TEXT PK FK | → tokens.address |
| `is_positive` | INTEGER | Classification |
| `overall_score` | INTEGER | 0-100 overall score |

## Usage

### Basic Operations
```python
from database import Database

db = Database("base_bot.db")

# Store a token
db.upsert_token({
    "address": "0x...",
    "name": "MyToken",
    "symbol": "MTK",
    # ... other fields
})

# Retrieve a token
token = db.get_token("0x...")

# Get recent tokens (last 24h)
recent = db.get_recent_tokens(days=1)

# Check if token was seen today
was_seen = db.was_token_seen_today("0x...")
```

### Analysis Storage
```python
# Save analysis result
db.save_analysis(
    token_address="0x...",
    analysis_type="security",
    result_data={"score": 85, "is_safe": True},
    is_safe=True,
    score=85,
)

# Get latest analyses for a token
analyses = db.get_latest_analyses("0x...")
# Returns: {"security": {...}, "honeypot": {...}, ...}
```

### Daily Scans
```python
# Start a scan
scan_id = db.create_daily_scan("2026-05-31")

# Add tokens to scan
db.add_scan_token(scan_id, "0x...", is_positive=True, overall_score=85)

# Complete scan
db.complete_daily_scan(scan_id, positive=5, negative=3, total=8)

# Get scan summary
summary = db.get_daily_scan_summary("2026-05-31")

# Get positive tokens from a scan
positive_tokens = db.get_scan_tokens(scan_id, positive_only=True)
```

### Statistics
```python
stats = db.get_statistics()
# Returns:
# {
#     "total_tokens": 150,
#     "total_analyses": 750,
#     "total_scans": 10,
#     "total_positive": 35,
#     "total_negative": 115,
# }
```

## Notes
- All connections are managed per-operation (context manager)
- No connection pooling needed for SQLite
- JSON analysis results stored as text, parsed on retrieval
- Database file: `base_bot.db` (configurable via `DB_PATH` env var)

---

# 💾 توثيق وحدة قاعدة البيانات (النسخة العربية)

## 📖 نظرة عامة
**SQLite** هي قاعدة بيانات **خفيفة وسريعة** تُخزن:
- **معلومات التوكنات** المكتشفة
- **نتائج التحليلات** من كل محلل
- **سجل الفحوصات اليومية** مع النتائج

---

## 🗂️ جداول قاعدة البيانات

### 1️⃣ جدول `tokens` — معلومات التوكن

| العمود | النوع | الوصف |
|--------|-------|--------|
| `address` | TEXT | 🔑 عنوان العقد (مفتاح أساسي) |
| `name` | TEXT | اسم التوكن |
| `symbol` | TEXT | الاختصار (مثال: MTK) |
| `chain` | TEXT | السلسلة ("base") |
| `description` | TEXT | وصف المشروع |
| `website` | TEXT | الموقع الرسمي |
| `twitter` | TEXT | رابط تويتر/إكس |
| `telegram` | TEXT | مجموعة تيليجرام |
| `discord` | TEXT | سيرفر ديسكورد |
| `github_url` | TEXT | رابط مستودع GitHub |
| `market_cap` | REAL | القيمة السوقية (دولار) |
| `price_usd` | REAL | السعر الحالي (دولار) |
| `liquidity_usd` | REAL | السيولة (دولار) |
| `volume_24h` | REAL | حجم التداول 24 ساعة |
| `price_change_24h` | REAL | تغير السعر % |
| `pair_address` | TEXT | عنوان الزوج الرئيسي |
| `dex_url` | TEXT | رابط DexScreener |
| `first_seen` | TIMESTAMP | تاريخ اكتشافه |
| `last_seen` | TIMESTAMP | آخر تحديث |
| `is_positive` | INTEGER | 1 = توكن جيد، 0 = سيء |

### 2️⃣ جدول `analyses` — نتائج التحليل

| العمود | النوع | الوصف |
|--------|-------|--------|
| `id` | INTEGER | 🔑 معرّف فريد |
| `token_address` | TEXT | 🔗 رابط خارجي → tokens.address |
| `analysis_type` | TEXT | نوع المحلل: "security", "honeypot", ... |
| `result_json` | TEXT | النتيجة الكاملة بصيغة JSON |
| `is_safe` | INTEGER | 1 = آمن، 0 = خطر |
| `score` | INTEGER | درجة هذا المحلل (0-100) |
| `created_at` | TIMESTAMP | متى تم التحليل |

### 3️⃣ جدول `daily_scans` — سجل الفحوصات اليومية

| العمود | النوع | الوصف |
|--------|-------|--------|
| `id` | INTEGER | 🔑 معرّف الفحص |
| `scan_date` | TEXT | التاريخ (YYYY-MM-DD) |
| `tokens_found` | INTEGER | عدد التوكنات المكتشفة |
| `positive_count` | INTEGER | عدد الجيدة |
| `negative_count` | INTEGER | عدد السيئة |
| `status` | TEXT | "جارٍ" أو "مكتمل" |
| `created_at` | TIMESTAMP | وقت بداية الفحص |

### 4️⃣ جدول `scan_tokens` — ربط الفحوصات بالتوكنات

| العمود | النوع | الوصف |
|--------|-------|--------|
| `scan_id` | INTEGER | 🔗 رابط للفحص |
| `token_address` | TEXT | 🔗 رابط للتوكن |
| `is_positive` | INTEGER | التصنيف (جيد/سيء) |
| `overall_score` | INTEGER | الدرجة الكلية 0-100 |

---

## 🚀 طرق الاستخدام

### البيانات الأساسية:

#### 1. إنشاء أو تحديث توكن:
```python
from database import Database

db = Database("base_bot.db")

db.upsert_token({
    "address": "0x123...",
    "name": "MyToken",
    "symbol": "MTK",
    "market_cap": 500000,
    "liquidity_usd": 150000,
    "website": "https://mytoken.com",
    # ... حقول أخرى
})
```

#### 2. البحث عن توكن:
```python
# الحصول على معلومات توكن بالعنوان
token = db.get_token("0x123...")

# التوكنات المكتشفة في آخر 24 ساعة
recent = db.get_recent_tokens(days=1)

# معرفة إذا شُفحص اليوم
was_seen = db.was_token_seen_today("0x123...")
```

---

### حفظ و استرجاع التحليلات:

#### 1. حفظ نتيجة تحليل:
```python
db.save_analysis(
    token_address="0x123...",
    analysis_type="security",  # security, honeypot, holders, liquidity, github
    result_data={
        "score": 85,
        "is_safe": True,
        "risk_flags": ["High tax"],
    },
    is_safe=True,
    score=85,
)
```

#### 2. الحصول على أحدث تحليلات:
```python
# جميع التحليلات الأخيرة لتوكن
analyses = db.get_latest_analyses("0x123...")

# النتيجة:
{
    "security": {...},      # نتيجة الأمان
    "honeypot": {...},      # نتيجة الفخ
    "holders": {...},       # التوزيع
    "liquidity": {...},     # القفل
    "github": {...},        # المستودع
}
```

---

### الفحوصات اليومية:

#### 1. بدء فحص يومي:
```python
scan_id = db.create_daily_scan("2026-06-01")
# يُرجع معرّف الفحص لاستخدامه لاحقاً
```

#### 2. إضافة توكنات للفحص:
```python
db.add_scan_token(
    scan_id=scan_id,
    token_address="0x123...",
    is_positive=True,        # جيد أم سيء؟
    overall_score=85,        # الدرجة الكلية
)
```

#### 3. إكمال الفحص:
```python
db.complete_daily_scan(
    scan_id=scan_id,
    positive=5,   # عدد الجيدة
    negative=3,   # عدد السيئة
    total=8,      # الإجمالي
)
```

#### 4. الحصول على ملخص يومي:
```python
summary = db.get_daily_scan_summary("2026-06-01")

# النتيجة:
{
    "scan_id": 1,
    "scan_date": "2026-06-01",
    "tokens_found": 8,
    "positive_count": 5,
    "negative_count": 3,
    "status": "مكتمل",
}
```

#### 5. التوكنات الجيدة من فحص:
```python
positive_tokens = db.get_scan_tokens(scan_id, positive_only=True)

# يرجع قائمة التوكنات الجيدة من هذا الفحص
```

---

### الإحصائيات:

```python
stats = db.get_statistics()

# النتيجة:
{
    "total_tokens": 150,           # إجمالي التوكنات
    "total_analyses": 750,         # إجمالي التحليلات
    "total_scans": 10,             # إجمالي الفحوصات
    "total_positive": 35,          # إجمالي الجيدة
    "total_negative": 115,         # إجمالي السيئة
}
```

---

## 📋 مثال عملي شامل:

```python
import asyncio
from database import Database
from datetime import datetime

async def daily_workflow():
    db = Database("base_bot.db")
    
    # 1️⃣ إنشاء فحص جديد
    today = datetime.now().strftime("%Y-%m-%d")
    scan_id = db.create_daily_scan(today)
    print(f"🔍 بدء فحص: {today} (ID: {scan_id})")
    
    # 2️⃣ إضافة توكنات
    tokens_to_add = [
        {"address": "0x111...", "name": "SafeToken", "symbol": "SAFE", "liquidity_usd": 150000},
        {"address": "0x222...", "name": "DangerToken", "symbol": "DANGER", "liquidity_usd": 5000},
    ]
    
    for token in tokens_to_add:
        db.upsert_token(token)
    
    # 3️⃣ حفظ نتائج التحليل
    db.save_analysis(
        token_address="0x111...",
        analysis_type="security",
        result_data={"score": 90, "is_safe": True},
        is_safe=True,
        score=90,
    )
    
    # 4️⃣ تصنيف التوكنات
    db.add_scan_token(scan_id, "0x111...", is_positive=True, overall_score=85)
    db.add_scan_token(scan_id, "0x222...", is_positive=False, overall_score=25)
    
    # 5️⃣ إكمال الفحص
    db.complete_daily_scan(scan_id, positive=1, negative=1, total=2)
    print("✅ اكتمل الفحص")
    
    # 6️⃣ الحصول على الإحصائيات
    stats = db.get_statistics()
    print(f"📊 الإحصائيات: {stats['total_positive']} جيدة، {stats['total_negative']} سيئة")

asyncio.run(daily_workflow())
```

---

## 🔍 استعلامات مفيدة:

### الحصول على أفضل التوكنات:
```python
# أكثر الاستخدامات الآمنة
safe_tokens = db.db_execute(
    "SELECT * FROM tokens WHERE is_positive = 1 ORDER BY market_cap DESC LIMIT 5"
)
```

### عدد الفحوصات:
```python
stats = db.get_statistics()
print(f"تم فحص {stats['total_scans']} أيام")
```

### آخر 10 فحوصات:
```python
recent_scans = db.db_execute(
    "SELECT * FROM daily_scans ORDER BY created_at DESC LIMIT 10"
)
```

---

## ⚙️ النقاط المهمة:

✅ **المرونة**: SQLite لا يحتاج سيرفر منفصل  
✅ **الأمان**: البيانات محفوظة محلياً  
✅ **السرعة**: استعلامات سريعة جداً  
✅ **النسخ الاحتياطي**: نسخ واحدة من ملف DB_PATH

---