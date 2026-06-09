# 🌐 توثيق واجهة API

## نظرة عامة

خادم FastAPI يوفر REST endpoints و WebSocket للبث المباشر.

## هيكل الملفات

```
api/
├── __init__.py    # تصدير المكونات
└── server.py      # خادم FastAPI + WebSocket
```

---

## التشغيل

```bash
# تلقائياً مع main_monitor.py
python main_monitor.py

# يدوياً (للتطوير)
python -c "from api.server import APIServer; import asyncio; asyncio.run(APIServer().run())"
```

### الإعدادات
```env
API_ENABLED=true
API_HOST=0.0.0.0
API_PORT=8000
```

---

## REST Endpoints

### `GET /api/v1/health`
التحقق من صحة النظام.

**Response:**
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "monitors": {
    "pair_monitor": {
      "running": true,
      "pairs_detected": 42,
      "uptime_seconds": 3600,
      "listeners": {
        "aerodrome": true,
        "uniswap_v3": true
      }
    },
    "liquidity_monitor": {
      "watched_pairs": 35,
      "liquidity_events": 120,
      "pairs_with_liquidity": 28
    }
  }
}
```

---

### `GET /api/v1/stats`
إحصائيات شاملة.

**Response:**
```json
{
  "timestamp": 1234567890.0,
  "pair_monitor": {...},
  "liquidity_monitor": {...},
  "momentum_engine": {
    "tracked_tokens": 15
  },
  "alerts": {
    "total_alerts": 85,
    "by_type": {
      "new_pair": 42,
      "liquidity_added": 28,
      "early_gem": 3,
      "whale_detected": 5,
      "smart_money": 2
    }
  },
  "tokens_tracked": 42,
  "analyses_completed": 15
}
```

---

### `GET /api/v1/tokens`
قائمة بأحدث الرموز.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | عدد النتائج (1-200) |
| `dex` | string | - | تصفية بالمنصة (`aerodrome`/`uniswap_v3`) |
| `min_liquidity` | float | - | الحد الأدنى للسيولة بالدولار |

**Response:**
```json
{
  "count": 25,
  "total": 42,
  "tokens": [
    {
      "token_address": "0x...",
      "pair_address": "0x...",
      "dex": "aerodrome",
      "base_token": "WETH",
      "pair_type": "volatile",
      "created_at": 1234567890.0,
      "age_seconds": 120
    }
  ]
}
```

---

### `GET /api/v1/tokens/{address}`
تفاصيل رمز محدد.

**Response:**
```json
{
  "token": {
    "token_address": "0x...",
    "dex": "aerodrome",
    "base_token": "WETH"
  },
  "analysis": {
    "security_score": 85,
    "is_honeypot": false,
    "holders_concentration": "low",
    "overall_risk_score": 78
  },
  "decision": {
    "decision": "early_gem",
    "momentum_score": 87,
    "confidence": 0.83
  }
}
```

---

### `GET /api/v1/tokens/{address}/analysis`
نتائج التحليل فقط.

**Response:**
```json
{
  "token_address": "0x...",
  "security_score": 85,
  "has_proxy": false,
  "is_mintable": false,
  "is_blacklisted": false,
  "is_honeypot": false,
  "buy_tax": 0,
  "sell_tax": 0,
  "holders_concentration": "low",
  "locked_percentage": 100.0,
  "overall_risk_score": 78
}
```

---

### `GET /api/v1/gems`
قائمة الرموز المصنفة كـ EARLY GEM.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | عدد النتائج (1-50) |

**Response:**
```json
{
  "count": 3,
  "gems": [
    {
      "token_address": "0x...",
      "token_symbol": "ABC",
      "decision": "early_gem",
      "momentum_score": 87,
      "confidence": 0.83,
      "positive_signals": ["Security score: 85/100", "Liquidity: $25,000"]
    }
  ]
}
```

---

### `GET /api/v1/alerts`
آخر التنبيهات.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | عدد النتائج (1-200) |
| `alert_type` | string | - | تصفية بنوع التنبيه |

**Response:**
```json
{
  "count": 85,
  "alerts": [
    {
      "type": "early_gem",
      "emoji": "💎",
      "title": "EARLY GEM: ABC/WETH",
      "body": "Score: 87/100 | Momentum: Strong",
      "priority": 10,
      "timestamp": 1234567890.0,
      "data": {
        "momentum_score": 87,
        "liquidity_usd": 25000,
        "buy_count_5m": 42
      }
    }
  ]
}
```

---

## WebSocket: `/ws/live`

بث مباشر لجميع الأحداث.

### الاتصال
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/live");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.type}: ${data.data}`);
};
```

### أنواع الرسائل

#### `connected` - تأكيد الاتصال
```json
{
  "type": "connected",
  "data": {
    "tokens_tracked": 42,
    "analyses_completed": 15
  }
}
```

#### `new_pair` - زوج جديد
```json
{
  "type": "new_pair",
  "title": "New Pair: WETH/0x...",
  "data": {
    "token_address": "0x...",
    "pair_address": "0x...",
    "dex": "aerodrome"
  }
}
```

#### `early_gem` - جوهرة مبكرة
```json
{
  "type": "early_gem",
  "title": "EARLY GEM: ABC/WETH",
  "body": "Score: 87/100",
  "priority": 10,
  "data": {
    "momentum_score": 87,
    "liquidity_usd": 25000
  }
}