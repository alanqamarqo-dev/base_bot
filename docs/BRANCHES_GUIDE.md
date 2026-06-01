# 🌿 دليل إدارة الفروع في Git و GitHub

## 📋 محتويات الدليل
1. هيكل الفروع
2. طريقة العمل مع الفروع
3. رفع المشروع إلى GitHub
4. Pull Requests والدمج
5. أفضل الممارسات

---

# 🔀 **هيكل الفروع**

## الفروع الرئيسية:

```
main (الإصدار النهائي المستقر)
├── develop (فرع التطوير الرئيسي)
└── feature/* (الميزات الجديدة)
    ├── feature/scanner (وحدة الماسح)
    ├── feature/analyzers (وحدة المحللات)
    ├── feature/charts (وحدة الرسوم البيانية)
    ├── feature/database (وحدة قاعدة البيانات)
    ├── feature/telegram_bot (وحدة تيليجرام)
    └── feature/tests (وحدة الاختبارات)
```

---

## 📊 شرح الفروع:

### **1️⃣ main (الإنتاج)**
```
الفرع: main
الحالة: ملك مستقر وآمن
من يعمل عليه: المشرفون فقط
متى يُستخدم: إصدارات نهائية فقط
```

### **2️⃣ develop (التطوير)**
```
الفرع: develop
الحالة: فرع تطوير رئيسي
من يعمل عليه: فريق التطوير
متى يُستخدم: دمج الميزات الجديدة
```

### **3️⃣ feature/* (الميزات)**
```
الفروع:
• feature/scanner - تطوير وحدة اكتشاف التوكنات
• feature/analyzers - تطوير المحللات الخمسة
• feature/charts - تطوير الرسوم البيانية
• feature/database - تطوير قاعدة البيانات
• feature/telegram_bot - تطوير وحدة التيليجرام
• feature/tests - تطوير الاختبارات

من يعمل عليه: أي مطور
متى يُستخدم: عند العمل على ميزة محددة
```

---

# 🚀 **طريقة العمل مع الفروع**

## **الخطوة 1: الفحص (Clone)**

### من GitHub (أول مرة):
```bash
# استنساخ المشروع
git clone https://github.com/username/base_bot.git

# الدخول للمجلد
cd base_bot/project/sr

# عرض جميع الفروع
git branch -a
```

---

## **الخطوة 2: الانتقال إلى فرع**

### الانتقال إلى فرع موجود:
```bash
# الانتقال إلى فرع develop
git checkout develop

# الانتقال إلى فرع ميزة
git checkout feature/analyzers

# التحقق من الفرع الحالي
git branch
```

### إنشاء فرع جديد:
```bash
# إنشاء فرع جديد من develop
git checkout develop
git checkout -b feature/new-feature

# أو بأمر واحد
git checkout -b feature/new-feature develop
```

---

## **الخطوة 3: تعديل الملفات**

### في الفرع المختار:

```bash
# 1. قم بالتعديلات على الملفات
nano main.py  # أو أي محرر

# 2. تحقق من التغييرات
git status

# 3. أضف الملفات المعدلة
git add .
# أو ملف محدد
git add main.py

# 4. أنشئ commit
git commit -m "feat: إضافة ميزة جديدة"

# 5. عرض commits
git log --oneline
```

---

## **الخطوة 4: دفع التغييرات (Push)**

### رفع الفرع إلى GitHub:
```bash
# رفع الفرع الحالي
git push origin feature/analyzers

# رفع وتعيين tracking
git push -u origin feature/analyzers

# رفع جميع الفروع
git push origin --all
```

---

## **الخطوة 5: دمج الفروع (Merge)**

### دمج ميزة في develop:

```bash
# 1. الانتقال إلى develop
git checkout develop

# 2. تحديث develop من GitHub
git pull origin develop

# 3. دمج الميزة
git merge feature/analyzers

# 4. رفع النتيجة
git push origin develop
```

### دمج develop في main (إصدار):

```bash
# 1. الانتقال إلى main
git checkout main

# 2. تحديث main
git pull origin main

# 3. دمج develop
git merge develop

# 4. إضافة tag للإصدار
git tag v1.0.0

# 5. رفع الكل
git push origin main
git push origin --tags
```

---

# 🐙 **رفع المشروع إلى GitHub**

## **الخطوة 1: إنشاء المستودع على GitHub**

```
1. اذهب: https://github.com/new
2. اسم المستودع: base_bot
3. الوصف: Base Chain Token Scanner Bot
4. اختر Public (عام) أو Private (خاص)
5. اضغط "Create repository"
```

---

## **الخطوة 2: ربط المستودع المحلي**

### طريقة HTTPS:
```bash
cd e:\base_bot\project\sr

# ربط المستودع البعيد
git remote add origin https://github.com/username/base_bot.git

# إعادة تسمية الفرع (إن لزم)
git branch -M main

# رفع جميع الفروع
git push -u origin main
git push -u origin develop
git push -u origin --all
```

### طريقة SSH (آمن أكثر):
```bash
# إعادة الربط بـ SSH
git remote set-url origin git@github.com:username/base_bot.git

# رفع الفروع
git push -u origin main
git push -u origin develop
```

---

## **الخطوة 3: التحقق من الربط**

```bash
# عرض المستودعات المرتبطة
git remote -v

# يجب أن ترى:
# origin  https://github.com/username/base_bot.git (fetch)
# origin  https://github.com/username/base_bot.git (push)
```

---

# 🔄 **سير عمل يومي**

## **صباح كل يوم:**

```bash
# 1. تحديث develop من GitHub
git fetch origin
git checkout develop
git pull origin develop

# 2. إنشاء فرع ميزة جديدة
git checkout -b feature/my-new-feature develop
```

## **أثناء العمل:**

```bash
# 1. التعديل على الملفات
# ... تعديل main.py, analyzers.py, إلخ ...

# 2. commit المنتظم
git add .
git commit -m "feat: تحسين وحدة التحليل"

# 3. push المنتظم
git push origin feature/my-new-feature
```

## **نهاية اليوم:**

```bash
# 1. آخر commit
git add .
git commit -m "chore: انتهاء العمل على الميزة"

# 2. آخر push
git push origin feature/my-new-feature

# 3. إنشاء Pull Request على GitHub
# (سيكون هناك زر "Compare & pull request" على GitHub)
```

---

# 📝 **Pull Requests (طلبات الدمج)**

## **إنشاء PR:**

```
على GitHub:

1. اذهب إلى المستودع
2. ستجد "Compare & pull request" للفرع الجديد
3. اضغط عليه
4. أضف وصف المتغييرات
5. اختر "develop" كـ base branch
6. اضغط "Create pull request"
```

## **طلب المراجعة:**

```
في الـ PR:

1. اطلب مراجعة من Reviewers
2. أضف Labels (مثل: feature, bug, documentation)
3. اربطه بـ Issues (إن وجدت)
4. اجمع التعليقات
5. أجرِ التحسينات المطلوبة
```

## **دمج PR:**

```
بعد الموافقة:

1. اضغط "Merge pull request"
2. اختر نمط الدمج:
   • Create a merge commit (الافتراضي)
   • Squash and merge (دمج أنظف)
   • Rebase and merge (سجل أنظف)
3. احذف الفرع (اختياري)
```

---

# 🎯 **أفضل الممارسات**

## **تسمية الفروع:**

```
✅ صحيح:
feature/user-authentication
bugfix/login-error
docs/update-readme
test/add-unit-tests

❌ خطأ:
my-branch
fix
new-feature
test123
```

## **كتابة Commits:**

```bash
✅ صحيح:
git commit -m "feat: قسم أمان جديد في المحللات"
git commit -m "fix: إصلاح خطأ في إرسال Telegram"
git commit -m "docs: تحديث توثيق قاعدة البيانات"
git commit -m "test: إضافة اختبارات للماسح"

❌ خطأ:
git commit -m "update"
git commit -m "fixed"
git commit -m "asdf"
```

## **حجم الـ Commits:**

```
✅ جيد:
• كل commit واحد = ميزة واحدة صغيرة

❌ سيء:
• commit كبير يحتوي على 5 ميزات
• commits كثيرة جداً لتعديل واحد
```

---

# 📊 **الأوامر المهمة**

```bash
# عرض السجل
git log --oneline -10

# عرض الفروع المندمجة
git branch --merged

# حذف فرع محلي
git branch -d feature/old-feature

# حذف فرع بعيد
git push origin --delete feature/old-feature

# إعادة تعيين ملف
git checkout -- main.py

# إرجاع آخر commit
git reset --hard HEAD~1

# البحث عن من كتب السطر
git blame main.py
```

---

# 🔒 **الأمان والحماية**

## **قوانين الفروع على GitHub:**

```
على GitHub Settings:

1. اذهب: Settings → Branches
2. أضف "Protect main branch"
3. تطلب:
   ✅ Pull Request review قبل الدمج
   ✅ فحوصات CI/CD ناجحة
   ✅ الموافقة من 2 مطورين
```

---

# 📚 **مراجع مفيدة**

| الموضوع | الأمر |
|---------|-------|
| إنشاء فرع | `git checkout -b feature/name` |
| حذف فرع | `git branch -d feature/name` |
| دمج فرع | `git merge feature/name` |
| رفع فرع | `git push origin feature/name` |
| سحب فرع | `git pull origin feature/name` |
| عرض الفروع | `git branch -a` |
| إعادة تسمية | `git branch -m old new` |

---

# ✅ **قائمة تحقق**

قبل الرفع إلى GitHub:

- [ ] كل الملفات مضافة (`git add .`)
- [ ] الـ commits مكتوبة بشكل واضح
- [ ] الفرع محدث من main (`git pull origin main`)
- [ ] لا توجد conflicts
- [ ] الاختبارات تعمل (`pytest test/`)
- [ ] الكود منسق (`black`, `autopep8`)
- [ ] لا توجد ملفات حساسة (مفاتيح API)
- [ ] الملف `.gitignore` محدّث

---

نهاية الدليل! استمتع بـ Git! 🚀
