# 🔔 توثيق نظام التنبيهات (Alerts)

## نظرة عامة

مدير التنبيهات المركزي يستقبل الأحداث من جميع المراقبين ويوزعها عبر Telegram و WebSocket.

## هيكل الملفات

```
alerts/
├── __init__.py           # تصدير المكونات
└── alert_manager.py      # مدير التنبيهات
```

---

## أنواع التنبيهات

| النوع | الرمز | الأولوية | الوصف |
|-------|-------|---------|-------|
| `new_pair` | 🚀 | 3 (منخفضة) | اكتشاف زوج جديد |
| `liquidity_added` | 💧 | 5 (متوسطة) | إضافة سيولة |
| `liquidity_removed` | 🚨 | 10 (حرجة) | سحب سيولة |
| `risk_scan` | 🛡️ | 5 (متوسطة) | اكتمال تحليل المخاطر |
| `early_gem` | 💎 | 10 (حرجة) | اكتشاف جوهرة مبكرة |
| `watch` | 👀 | 5 (متوسطة) | رمز للمراقبة |
| `whale_detected` | 🐋 | 7 (عالية) | اكتشاف حوت |
| `smart_money` | 🧠 | 8 (عالية) | دخول Smart Money |
| `sniper` | 🎯 | 6 (متوسطة) | اكتشاف سنابر |
| `whale_exit` | 📤 | 9 (حرجة) | خروج الحيتان |
| `rug_pull` | 💀 | 10 (حرجة) | سحب بساط محتمل |

---

## تنسيق Telegram

### 🚀 زوج جديد
```
🚀 New Pair Detected

Token: ABC
Pair: WETH/ABC
DEX: Aerodrome
Type: volatile
Contract: 0x...
Pair: 0x...

View on DexScreener
```

### 💎 جوهرة مبكرة
```
💎 EARLY GEM: ABC/WETH

Age: 6 min
Buyers: 42 | Sells: 7
Volume: $31,000
Liquidity: $15,000
Score: 87/100
🧠 Smart Money: Yes
━━━━━━━━━━━━━━━
0x...
DexScreener
```

### 🚨 سحب سيولة
```
🚨 LIQUIDITY REMOVED: ABC

Before: $40,000
After: $3,000
Change: -92.5%
⚠️ POSSIBLE RUG PULL
```

### 🐋 اكتشاف حوت
```
🐋 Whale Detected: ABC

Wallet 0x... bought 15%
Wallet 0x... bought 10%
⚠️ High concentration risk
```

---

## الاشتراك في التنبيهات

### Python
```python
from alerts.alert_manager import AlertManager, Alert, AlertType

manager = AlertManager()

def on_alert(alert_data: dict):
    print(f"{alert_data['emoji']} {alert_data['title']}")

manager.subscribe(on_alert)
```

### API (REST)
```bash
GET /api/v1/alerts?limit=50&alert_type=early_gem
```

### API (WebSocket)
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/live");
ws.onmessage = (event) => {
  const alert = JSON.parse(event.data);
  // alert.type, alert.emoji, alert.title, alert.data
};
```

---

## تنسيق Alert object

```python
@dataclass
class Alert:
    alert_type: AlertType    # نوع التنبيه
    title: str               # العنوان
    body: str                # النص
    data: dict               # بيانات إضافية
    priority: int            # 0=منخفض, 5=متوسط, 10=حرج
    timestamp: float         # وقت التنبيه
```

---

## إحصائيات التنبيهات

```python
stats = manager.get_stats()
# {
#   "total_alerts": 85,
#   "by_type": {
#     "new_pair": 42,
#     "early_gem": 3,
#     "whale_detected": 5
#   }
# }

# آخر 50 تنبيه
recent = manager.get_recent_alerts(limit=50)

# تصفية بنوع معين
gems = manager.get_recent_alerts(alert_type="early_gem")