# 🚀 قائمة أوامر Git السريعة

## الإعداد الأولي

```bash
# تهيئة المستودع
git init

# ربط مع GitHub
git remote add origin https://github.com/username/base_bot.git

# تحديث الفروع من GitHub
git fetch origin
```

---

## الفروع الموجودة

| الفرع | الاستخدام |
|-------|----------|
| `main` | الإصدار النهائي المستقر |
| `develop` | فرع التطوير الرئيسي |
| `feature/scanner` | تطوير وحدة الماسح |
| `feature/analyzers` | تطوير المحللات |
| `feature/charts` | تطوير الرسوم البيانية |
| `feature/database` | تطوير قاعدة البيانات |
| `feature/telegram_bot` | تطوير تيليجرام |
| `feature/tests` | تطوير الاختبارات |

---

## أوامر يومية

### 1. الانتقال إلى فرع
```bash
git checkout develop
git checkout feature/analyzers
```

### 2. التحديث من GitHub
```bash
git pull origin develop
```

### 3. إضافة التعديلات
```bash
git add .
git add main.py     # ملف محدد فقط
```

### 4. إنشاء Commit
```bash
git commit -m "feat: وصف الميزة"
git commit -m "fix: إصلاح الخطأ"
git commit -m "docs: تحديث التوثيق"
```

### 5. رفع التغييرات
```bash
git push origin feature/analyzers
git push -u origin branch-name  # أول مرة
```

---

## العمل على ميزة جديدة

```bash
# 1. تحديث develop
git checkout develop
git pull origin develop

# 2. إنشاء فرع ميزة
git checkout -b feature/my-feature develop

# 3. التعديل والـ commit
git add .
git commit -m "feat: وصف الميزة"

# 4. الرفع
git push -u origin feature/my-feature

# 5. إنشاء Pull Request على GitHub
```

---

## دمج فروع

### دمج في develop
```bash
git checkout develop
git pull origin develop
git merge feature/analyzers
git push origin develop
```

### دمج في main (إصدار)
```bash
git checkout main
git pull origin main
git merge develop
git tag v1.0.0
git push origin main
git push origin --tags
```

---

## عرض المعلومات

```bash
# الفروع المتاحة
git branch          # محليًا
git branch -a       # كل الفروع

# السجل
git log --oneline -10
git log --graph --oneline --all

# حالة المستودع
git status

# الفروع المندمجة
git branch --merged
```

---

## حذف الفروع

```bash
# حذف محلي
git branch -d feature/old-feature

# حذف بعيد
git push origin --delete feature/old-feature

# حذف جميع الفروع المحذوفة محليًا
git prune
```

---

## الأخطاء الشائعة والحل

### نسيان commit قبل الـ push
```bash
git add .
git commit --amend
git push origin branch-name
```

### أردت الانتقال لفرع آخر قبل الـ commit
```bash
git stash              # حفظ التغييرات مؤقتًا
git checkout other-branch
git checkout original-branch
git stash pop          # استرجاع التغييرات
```

### رغبت في إلغاء آخر commit
```bash
git reset --soft HEAD~1    # مع حفظ التغييرات
git reset --hard HEAD~1    # حذف كل شيء
```

### conflict أثناء الدمج
```bash
# عرض الـ conflicts
git status

# حل يدويًا ثم
git add .
git commit -m "Merge: حل التنارضات"
git push origin branch-name
```

---

## الناشرون (Tags)

```bash
# إنشاء tag
git tag v1.0.0
git tag -a v1.0.0 -m "الإصدار 1.0.0"

# رفع tags
git push origin --tags

# عرض tags
git tag -l
```

---

## الإعدادات الشخصية

```bash
# اسم المستخدم
git config --global user.name "اسمك"

# البريد
git config --global user.email "email@example.com"

# المحرر الافتراضي
git config --global core.editor "nano"

# عرض الإعدادات
git config --list
```

---

## الأوامر المتقدمة

```bash
# إعادة تعيين (Rebase)
git rebase main

# Cherry-pick (نقل commit)
git cherry-pick <commit-hash>

# Squash (دمج commits)
git rebase -i HEAD~3

# البحث في السجل
git log -S "البحث"
git log --author="الاسم"

# انظر من الذي كتب هذا السطر
git blame main.py
```

---

## الربط مع GitHub Desktop

```
بدل سطر الأوامر يمكنك استخدام:
https://desktop.github.com/

وهي أداة بصرية سهلة جداً!
```

---

استمتع بـ Git! 🚀
