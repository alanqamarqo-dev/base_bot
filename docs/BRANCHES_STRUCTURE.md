# 📂 وصف الفروع والمجلدات

## 🌳 هيكل الفروع الكامل

```
main (الإصدار النهائي)
│
└─→ develop (التطوير الرئيسي)
    │
    ├─→ feature/scanner (الماسح)
    ├─→ feature/analyzers (المحللات)
    ├─→ feature/charts (الرسوم البيانية)
    ├─→ feature/database (قاعدة البيانات)
    ├─→ feature/telegram_bot (تيليجرام)
    └─→ feature/tests (الاختبارات)
```

---

# 📋 **تفصيل كل فرع**

## 🔍 **feature/scanner**

### المحتوى:
```
scanner/
├── base_scanner.py      # الماسح الأساسي
├── dex_scanner.py       # استعلامات DexScreener
└── __init__.py
```

### المسؤولية:
- ✅ اكتشاف التوكنات الجديدة
- ✅ جلب البيانات من DexScreener
- ✅ تطبيق المرشحات (السيولة، الـ chain)

### متى تعمل عليه:
```
• إضافة مصادر جديدة للاكتشاف
• تحسين الأداء
• دعم chains جديدة
• تحسين المرشحات
```

### أمثلة commits:
```
feat: دعم Uniswap v3 كمصدر
fix: إصلاح تصفية السيولة
perf: تحسين سرعة الفحص
```

---

## 🛡️ **feature/analyzers**

### المحتوى:
```
analyzers/
├── security_score.py      # فحص الأمان (GoPlus)
├── honeypot_checker.py    # كشف الفخ
├── holders_checker.py     # توزيع المالكين
├── liquidity_checker.py   # فحص القفل
├── github_checker.py      # تحليل GitHub
└── __init__.py
```

### المسؤولية:
- ✅ تنفيذ 5 محللات أساسية
- ✅ جلب البيانات من APIs
- ✅ حساب الدرجات
- ✅ معالجة الأخطاء

### متى تعمل عليه:
```
• إضافة محلل جديد
• تحسين حساب الدرجات
• دعم APIs جديدة
• تحسين دقة التحليل
```

### أمثلة commits:
```
feat: إضافة محلل الرسوم (Tagging)
fix: إصلاح حساب درجة الأمان
test: إضافة اختبارات للـ Honeypot
```

---

## 📊 **feature/charts**

### المحتوى:
```
charts/
├── chart_generator.py     # مولد الرسوم البيانية
└── __init__.py
```

### المسؤولية:
- ✅ إنشاء رسوم بيانية جميلة
- ✅ صيغة PNG جاهزة
- ✅ ألوان موحدة واحترافية

### متى تعمل عليه:
```
• إضافة أنواع رسوم جديدة
• تحسين التصميم
• دعم سمات مختلفة
• تحسين الأداء
```

### أمثلة commits:
```
feat: رسم بياني جديد للمخاطر
design: تحسين الألوان والخطوط
perf: تحسين وقت الإنشاء
```

---

## 💾 **feature/database**

### المحتوى:
```
database/
├── storage.py             # كل العمليات
└── __init__.py
```

### المسؤولية:
- ✅ إدارة SQLite
- ✅ CRUD operations
- ✅ الفحوصات اليومية
- ✅ الإحصائيات

### متى تعمل عليه:
```
• إضافة جداول جديدة
• تحسين الاستعلامات
• دعم نسخ احتياطي
• تحسين الأداء
```

### أمثلة commits:
```
feat: جدول جديد للتنبيهات
perf: فهرسة أفضل
docs: توثيق schema
```

---

## 📨 **feature/telegram_bot**

### المحتوى:
```
telegram_bot/
├── sender.py              # إرسال الرسائل
└── __init__.py
```

### المسؤولية:
- ✅ إنشاء الرسائل
- ✅ أرسلال الرسائل
- ✅ صيغ مختلفة
- ✅ معالجة الأخطاء

### متى تعمل عليه:
```
• تحسين نسق الرسائل
• إضافة ميزات تفاعلية
• دعم مجموعات
• إضافة buttons/keyboards
```

### أمثلة commits:
```
feat: إضافة buttons تفاعلية
design: تحسين نسق الرسالة
fix: إصلاح الأيموجي
```

---

## 🧪 **feature/tests**

### المحتوى:
```
test/
├── test_scanner.py
├── test_analyzers.py
├── test_charts.py
├── test_database.py
├── test_telegram_bot.py
├── test_base_bote_main_all.py
└── __init__.py
```

### المسؤولية:
- ✅ اختبارات الوحدات
- ✅ اختبارات التكامل
- ✅ تغطية الكود
- ✅ Mock APIs

### متى تعمل عليه:
```
• إضافة اختبارات جديدة
• زيادة التغطية
• إصلاح الاختبارات الفاشلة
• تحسين الأداء
```

### أمثلة commits:
```
test: إضافة اختبارات للماسح
ci: تحسين تكوين CI/CD
test: محاكاة API متقدمة
```

---

# 📁 **الملفات المشتركة**

هذه الملفات في جميع الفروع:

```
main.py                   # الـ orchestrator الرئيسي
requirements.txt          # المكتبات
.env.example             # إعدادات المثال
README.md                # التوثيق الرئيسي
docs/                    # جميع التوثيقات
```

---

# 🔄 **سير العمل على الفروع**

### اليوم الأول:

```bash
# 1. اختيار الفرع
git checkout feature/analyzers

# 2. التحديث
git pull origin feature/analyzers

# 3. التعديل
nano analyzers/security_score.py

# 4. الـ commit
git add .
git commit -m "feat: تحسين دقة الأمان"

# 5. الـ push
git push origin feature/analyzers
```

### إنهاء الميزة (PR):

```bash
# على GitHub:
1. اذهب للفرع
2. اضغط "Compare & pull request"
3. صف التغييرات
4. اختر develop كـ base
5. اطلب المراجعة
6. اجمع التعليقات
7. اضغط "Merge pull request"
```

---

# 🎯 **أفضل الممارسات**

## التسمية:
```
✅ feature/scanner-optimization
✅ bugfix/incorrect-scoring
✅ docs/database-schema

❌ feature/new-stuff
❌ fix/bug
❌ update
```

## الـ Commits:
```
✅ feat: إضافة محلل جديد للأمان
✅ fix: إصلاح خطأ في الدرجة
✅ test: اختبارات المحللات

❌ updated
❌ fixed stuff
❌ works now
```

## الـ PR:
```
✅ عنوان واضح
✅ وصف مفصل للتغييرات
✅ لقطات الشاشة (إن وجدت)
✅ ربط الـ issues

❌ [no description]
❌ "fixes bugs"
```

---

# 📊 **الإحصائيات**

عند الانتهاء من كل فرع:

```bash
# عدد الـ commits
git shortlog -sn feature/analyzers

# عدد الأسطر المعدلة
git diff --stat main..feature/analyzers

# من الذي ساهم
git log --oneline feature/analyzers | wc -l
```

---

# ✅ **قائمة تحقق قبل الـ PR**

- [ ] الفرع محدث من develop
- [ ] الاختبارات تمر ✅
- [ ] لا conflicts
- [ ] الكود منسق
- [ ] التوثيق محدث
- [ ] الـ commits واضحة
- [ ] لا ملفات حساسة
- [ ] قراءة الكود ذاتياً

---

# 🚀 **الخطوة التالية**

بعد دراسة هذا الملف:

1. اختر الفرع الذي تريد العمل عليه
2. اتبع `BRANCHES_GUIDE.md` للخطوات
3. اتبع `GIT_QUICK_COMMANDS.md` للأوامر
4. اتبع `GITHUB_SETUP.md` لرفع المشروع
5. ابدأ التطوير! 🚀

---

استمتع بـ Git و GitHub! 🎉
