# 🧪 توثيق الاختبارات (النسخة العربية)

## 📖 نظرة عامة
**مجموعة اختبارات شاملة** تتحقق من:
- ✅ كل وحدة بمفردها (Unit Tests)
- ✅ التكامل بينها (Integration Tests)
- ✅ النتيجة النهائية (End-to-End)

---

## 🚀 تشغيل الاختبارات

### تثبيت أدوات الاختبارات:

```bash
pip install pytest pytest-asyncio pytest-mock
```

### تشغيل جميع الاختبارات:

```bash
# تشغيل بسيط
pytest test/ -v

# مع تفاصيل مخرجات
pytest test/ -v -s

# اختبار ملف واحد
pytest test/test_analyzers.py -v

# اختبار دالة واحدة فقط
pytest test/test_analyzers.py::TestSecurityScoreResult::test_safe_score -v
```

### قياس التغطية (Coverage):

```bash
# تثبيت أداة Coverage
pip install pytest-cov

# قياس التغطية
pytest test/ --cov=. --cov-report=html

# سيُنشئ مجلد htmlcov بنسبة التغطية
```

---

## 📋 ملفات الاختبارات

### 1. `test_scanner.py` — اختبارات الماسح

```python
# ✅ اختبار: هل يجد التوكنات؟
# ✅ اختبار: هل ينطبق المرشح على السيولة؟
# ✅ اختبار: هل يرجع بيانات صحيحة؟
```

### 2. `test_analyzers.py` — اختبارات المحللات

```python
# ✅ اختبارات الأمان (Security Score)
# ✅ اختبارات الفخ (Honeypot)
# ✅ اختبارات التوزيع (Holders)
# ✅ اختبارات القفل (Liquidity)
# ✅ اختبارات GitHub
```

### 3. `test_charts.py` — اختبارات الرسوم البيانية

```python
# ✅ اختبار: هل الرسم صورة PNG صحيحة؟
# ✅ اختبار: هل الحجم معقول؟
# ✅ اختبار: جميع أنواع الرسوم
```

### 4. `test_database.py` — اختبارات قاعدة البيانات

```python
# ✅ إضافة توكن
# ✅ استرجاع توكن
# ✅ تحديث البيانات
# ✅ حذف البيانات
# ✅ فحوصات يومية
```

### 5. `test_base_bote_main_all.py` — اختبارات شاملة

```python
# ✅ فحص كامل: scanner → analysis → charts
# ✅ إرسال إلى Telegram (بدون فعلي)
# ✅ تخزين في قاعدة البيانات
```

---

## 🎯 استراتيجية الاختبارات

### اختبارات الوحدة (Unit Tests):

كل محلل له **نسخة وهمية (Mock)** تُرجع نتائج ثابتة ومتوقعة:

```python
from analyzers import (
    MockSecurityScoreChecker,   # يرجع دائماً score > 80
    MockHoneypotChecker,        # يرجع دائماً is_safe=True
    MockHoldersChecker,         # يرجع توزيع "منخفض"
    MockLiquidityChecker,       # يرجع locked > 80%
    MockGitHubChecker,          # يرجع repo نشط
)
```

**أمثلة:**

```python
@pytest.mark.asyncio
async def test_mock_security_checker():
    """اختبار محلل الأمان الوهمي"""
    checker = MockSecurityScoreChecker()
    result = await checker.check("0xTest", "Token", "TKN")
    
    assert result.success == True
    assert result.score >= 80
    assert result.is_safe == True
    print("✅ محلل الأمان يعمل")

@pytest.mark.asyncio
async def test_mock_honeypot_checker():
    """اختبار كشف الفخ الوهمي"""
    checker = MockHoneypotChecker()
    result = await checker.check("0xTest", "Token", "TKN")
    
    assert result.is_honeypot == False
    assert result.is_safe == True
    print("✅ كاشف الفخ يعمل")
```

### اختبارات التكامل (Integration Tests):

```python
@pytest.mark.asyncio
async def test_full_analysis_pipeline():
    """اختبار خط أنابيب التحليل الكامل"""
    from main import BaseBotOrchestrator
    
    bot = BaseBotOrchestrator()
    
    # تحليل توكن واحد
    result = await bot.run_single_token_check(
        "0xPositiveToken111...",
        token_name="TestToken",
        token_symbol="TEST"
    )
    
    # التحقق من النتيجة
    assert result.overall_score > 0
    assert result.security.score >= 0
    assert result.honeypot is not None
    
    await bot.close()
    print("✅ خط الأنابيب يعمل بسلاسة")
```

---

## 📊 أهداف التغطية:

| الوحدة | الهدف | الحالة |
|--------|-------|--------|
| **scanner** | 80%+ | ✅ محقق |
| **analyzers** | 90%+ | ✅ محقق |
| **charts** | 85%+ | ✅ محقق |
| **database** | 90%+ | ✅ محقق |
| **telegram_bot** | 70%+ | ✅ محقق |
| **main** | 80%+ | ✅ محقق |

---

## 🧪 كتابة اختبار جديد:

### مثال 1: اختبار بسيط

```python
import pytest

def test_simple_math():
    """اختبار عملية حسابية"""
    assert 2 + 2 == 4
    assert 5 * 3 == 15
    print("✅ الاختبار نجح")
```

### مثال 2: اختبار Async

```python
@pytest.mark.asyncio
async def test_async_operation():
    """اختبار عملية غير متزامنة"""
    import asyncio
    
    result = await asyncio.sleep(0.1)
    assert result is None
    print("✅ العملية المتزامنة نجحت")
```

### مثال 3: اختبار مع Mock

```python
@pytest.mark.asyncio
async def test_with_mock(mocker):
    """اختبار مع محاكاة"""
    from scanner import BaseScanner
    
    # محاكاة الـ API
    mock_response = [
        {"address": "0x123", "name": "Token1", "liquidity_usd": 5000},
    ]
    
    # Patch الدالة
    mocker.patch(
        'scanner.BaseScanner.fetch_latest_tokens',
        return_value=mock_response
    )
    
    scanner = BaseScanner()
    tokens = await scanner.fetch_latest_tokens()
    
    assert len(tokens) == 1
    print("✅ Mock اشتغل")
```

---

## 📝 قائمة الاختبارات الموجودة:

### Security Analyzer:
- ✅ اختبار درجة آمنة (Safe Score)
- ✅ اختبار درجة تحذير (Caution Score)
- ✅ اختبار درجة خطر (Danger Score)
- ✅ اختبار to_dict()
- ✅ اختبار score_color و score_label

### Honeypot Checker:
- ✅ توكن آمن
- ✅ فخ مكتشف
- ✅ فشل الـ API

### Holders Checker:
- ✅ توزيع منخفض
- ✅ توزيع مرتفع
- ✅ توزيع أقصى

### Liquidity Checker:
- ✅ سيولة مقفولة
- ✅ سيولة غير مقفولة
- ✅ فقد الأقفال

### GitHub Checker:
- ✅ مستودع نشط
- ✅ مستودع غير موجود
- ✅ مستودع مؤرشف

### Database:
- ✅ CRUD operations
- ✅ الفحوصات اليومية
- ✅ الإحصائيات

### Charts:
- ✅ إنشاء جميع الرسوم
- ✅ PNG output صحيح

### Main:
- ✅ التصنيف (positive/negative)
- ✅ الدرجات الموزونة
- ✅ تخزين النتائج

---

## 🎯 مثال عملي: إضافة اختبار جديد

```python
# في test_analyzers.py
@pytest.mark.asyncio
async def test_my_new_analyzer():
    """اختبار محلل جديد"""
    from analyzers import MyNewAnalyzer
    
    # الإعداد (Setup)
    analyzer = MyNewAnalyzer()
    token_address = "0xTest123"
    
    # التنفيذ (Act)
    result = await analyzer.check(token_address)
    
    # التحقق (Assert)
    assert result.success == True
    assert hasattr(result, 'score')
    assert 0 <= result.score <= 100
    
    print("✅ الاختبار نجح!")
```

---

## 🚀 سير العمل:

```
1. كتابة الاختبار
      ↓
2. تشغيل: pytest test/ -v
      ↓
3. يفشل الاختبار في البداية (Red)
      ↓
4. كتابة الكود الذي يجعله ينجح (Green)
      ↓
5. تحسين الكود (Refactor)
      ↓
6. اختبار يمر ✅
```

---

## 📌 أفضل الممارسات:

✅ كل اختبار يختبر **واحد فقط**  
✅ الاختبارات مستقلة عن بعضها  
✅ استخدم **أسماء واضحة**: `test_security_check_safe_token`  
✅ استخدم **assertions واضحة**: `assert result.is_safe == True`  
✅ **وثّق** ماذا يختبر الاختبار  
✅ **سرّع** الاختبارات باستخدام Mocks  

