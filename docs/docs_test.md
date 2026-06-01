# 🧪 Testing Documentation

## Overview
Test suite for the Base Chain Token Scanner Bot. Uses `pytest` with `pytest-asyncio` for async tests.

## Files
- [`test/test_scanner.py`](../test/test_scanner.py) — Scanner module tests
- [`test/test_analyzers.py`](../test/test_analyzers.py) — Analyzer tests with mocks
- [`test/test_charts.py`](../test/test_charts.py) — Chart generation tests
- [`test/test_database.py`](../test/test_database.py) — Database CRUD tests
- [`test/test_base_bote_main_all.py`](../test/test_base_bote_main_all.py) — Integration & end-to-end tests

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run all tests
pytest test/ -v

# Run specific file
pytest test/test_analyzers.py -v

# Run with verbose output
pytest test/ -v -s

# Run with coverage
pip install pytest-cov
pytest test/ --cov=. --cov-report=html
```

## Test Strategy

### Unit Tests
Each module is tested in isolation using mock APIs:

- **Scanner**: Mock DexScreener responses
- **Analyzers**: Mock analyzers return deterministic results
- **Charts**: Verify chart output is valid PNG bytes
- **Database**: SQLite in-memory or temp file

### Integration Tests
- Full pipeline test: scanner → analysis → classification → chart generation
- Database: token CRUD + daily scan flow
- Telegram: message formatting (no actual send)

## Test Data
Mock token addresses used in tests:
- `0xPositiveToken0000000000000000000000000000001` — Always returns SAFE
- `0xNegativeToken0000000000000000000000000000002` — Always returns DANGER

## Coverage Targets
| Module | Target |
|--------|--------|
| scanner | 80%+ |
| analyzers | 90%+ |
| charts | 85%+ |
| database | 90%+ |
| telegram_bot | 70%+ |
| main | 80%+ |

## Writing New Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.asyncio
async def test_security_check():
    """Test security score analysis."""
    from analyzers import MockSecurityScoreChecker
    
    checker = MockSecurityScoreChecker()
    result = await checker.check("0xTest...", "TestToken", "TEST")
    
    assert result.success is True
    assert result.score >= 80
    assert result.is_safe is True
```

---

# 🧪 توثيق الاختبارات (النسخة العربية)

## 📖 نظرة عامة
**مجموعة اختبارات شاملة** تتحقق من كل أجزاء البوت

---

## 🚀 تشغيل الاختبارات

```bash
# تثبيت
pip install pytest pytest-asyncio pytest-mock pytest-cov

# تشغيل الكل
pytest test/ -v

# تشغيل ملف واحد
pytest test/test_analyzers.py -v

# قياس التغطية
pytest test/ --cov=. --cov-report=html
```

---

## 🎯 أنواع الاختبارات

### اختبارات الوحدة (Unit Tests):
```python
@pytest.mark.asyncio
async def test_security_checker():
    checker = MockSecurityScoreChecker()
    result = await checker.check("0x123", "Token", "TKN")
    assert result.score >= 80
```

### اختبارات التكامل (Integration):
```python
@pytest.mark.asyncio
async def test_full_pipeline():
    bot = BaseBotOrchestrator()
    result = await bot.run_single_token_check(...)
    assert result.overall_score > 0
```

---

## 📊 أهداف التغطية:
- scanner: 80%+
- analyzers: 90%+  
- charts: 85%+
- database: 90%+

---