# 🐙 دليل ربط المشروع بـ GitHub

## 📋 محتويات الدليل
1. إنشاء حساب GitHub
2. إنشاء مستودع جديد
3. ربط المشروع المحلي
4. رفع الكود
5. دعوة المتعاونين

---

# 📝 **خطوة 1: إنشاء حساب GitHub**

### إذا لم يكن لديك حساب:

```
1. اذهب: https://github.com
2. اضغط "Sign up"
3. أدخل بريد إلكتروني
4. أنشئ كلمة مرور قوية
5. اختر اسم مستخدم فريد
6. اكمل التحقق
```

### إذا كان لديك حساب:
```
اذهب مباشرة إلى الخطوة الثانية
```

---

# 🏗️ **خطوة 2: إنشاء مستودع GitHub**

### طريقة 1: من الموقع (سهل)

```
1. اذهب: https://github.com/new

2. ملء المعلومات:
   • Repository name: base_bot
   • Description: Base Chain Token Scanner Bot
   • Public/Private: Public (أم Private حسب التفضيل)
   
3. اختر README: No (لننا بالفعل لدينا واحد)

4. اضغط "Create repository"
```

### الصفحة التي تظهر:

```
ستجد أكواد Git للاستخدام:

…or push an existing repository from the command line

git remote add origin https://github.com/username/base_bot.git
git branch -M main
git push -u origin main
```

---

# 🔗 **خطوة 3: ربط المشروع المحلي**

### في PowerShell:

```powershell
# الدخول للمجلد
cd e:\base_bot\project\sr

# التحقق من المستودع المحلي
git remote -v
# إذا لم يظهر شيء، لا مشكلة. سنعيّن الآن
```

### ربط GitHub مع المشروع:

```powershell
# الطريقة الأول: HTTPS (أسهل في البداية)
git remote add origin https://github.com/YOUR_USERNAME/base_bot.git

# أو الطريقة الثانية: SSH (أكثر أماناً)
git remote add origin git@github.com:YOUR_USERNAME/base_bot.git

# تحقق من الربط
git remote -v

# يجب أن ترى مثل هذا:
# origin  https://github.com/YOUR_USERNAME/base_bot.git (fetch)
# origin  https://github.com/YOUR_USERNAME/base_bot.git (push)
```

---

# 📤 **خطوة 4: رفع الكود**

### رفع الفرع الرئيسي:

```powershell
# 1. إعادة تسمية main (إن لزم، عادة تم بالفعل)
git branch -M main

# 2. رفع الفرع الرئيسي
git push -u origin main

# 3. رفع فرع develop
git push -u origin develop

# 4. رفع جميع الفروع الأخرى
git push -u origin feature/scanner
git push -u origin feature/analyzers
git push -u origin feature/charts
git push -u origin feature/database
git push -u origin feature/telegram_bot
git push -u origin feature/tests

# أو دفعة واحدة
git push -u origin --all
```

### التحقق من الرفع:

```
اذهب: https://github.com/YOUR_USERNAME/base_bot

ستجد:
✅ main branch
✅ develop branch
✅ جميع الفروع الأخرى
✅ جميع الملفات
```

---

# 👥 **خطوة 5: دعوة المتعاونين**

### إضافة أشخاص للمشروع:

```
1. على صفحة المستودع
2. اذهب: Settings → Collaborators
3. اضغط "Add people"
4. أدخل اسم المستخدم
5. اختر الصلاحيات:
   • Pull access (عرض فقط)
   • Triage access (تقييم)
   • Push access (تعديل)
   • Admin access (كامل)
6. اضغط "Send invitation"
```

---

# 🔑 **المصادقة (Authentication)**

## طريقة 1: HTTPS (بسيط)

```powershell
# المرة الأولى، سيطلب منك:
Username: your_github_username
Password: your_password  # أو Personal Access Token

# لتجنب إعادة الإدخال كل مرة:
git config --global credential.helper wincred
```

## طريقة 2: SSH (آمن أكثر)

### إنشاء SSH Key:

```powershell
# 1. إنشاء المفتاح
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. اضغط Enter لحفظ في المكان الافتراضي
# 3. أدخل passphrase (كلمة مرور قوية)
# 4. أكد الـ passphrase

# المفاتيح الآن في:
# c:\Users\YOUR_USER\.ssh\
```

### إضافة للـ GitHub:

```
1. اذهب: https://github.com/settings/keys
2. اضغط "New SSH key"
3. Title: My Dev Machine
4. Key Type: Authentication Key
5. نسخ محتوى الملف: ~/.ssh/id_ed25519.pub
6. الصق في "Key"
7. اضغط "Add SSH key"
```

### التحقق:

```powershell
ssh -T git@github.com
# يجب أن ترى: Hi YOUR_USERNAME! ...
```

---

# 📊 **مثال عملي كامل**

### من الصفر إلى الرفع:

```powershell
# 1. الدخول للمجلد
cd e:\base_bot\project\sr

# 2. التحقق من المستودع
git status

# 3. إضافة الملفات (إن لم تضف قبلاً)
git add -A

# 4. إنشاء commit أولي
git commit -m "chore: Initial commit"

# 5. الربط مع GitHub
git remote add origin https://github.com/YOUR_USERNAME/base_bot.git

# 6. إعادة التسمية
git branch -M main

# 7. الرفع!
git push -u origin main
git push -u origin --all

# 8. تحقق على GitHub
# https://github.com/YOUR_USERNAME/base_bot
```

---

# 🎯 **بعد الرفع الأول**

### التحديثات اليومية:

```powershell
# التعديل على ملف
nano main.py

# إضافة وتسجيل
git add main.py
git commit -m "feat: تحسين الميزة"

# الرفع
git push origin develop

# أو إذا كنت على فرع ميزة
git push origin feature/analyzers
```

### جلب التحديثات من GitHub:

```powershell
# تحديث الفرع الحالي
git pull

# أو
git pull origin develop
```

---

# ⚙️ **الإعدادات المهمة**

### إعدادات الأمان:

```
1. اذهب: Settings → Security
2. Enable two-factor authentication (2FA)
3. Review SSH keys
4. Review collaborator access
```

### إعدادات الفروع:

```
1. اذهب: Settings → Branches
2. Protect main branch:
   ✅ Require a pull request review
   ✅ Require status checks to pass
   ✅ Include administrators
3. اضغط "Save"
```

---

# 🚀 **أدوات إضافية**

### GitHub Desktop (بديل بصري):

```
بدل سطر الأوامر:
https://desktop.github.com/

مميزات:
✅ واجهة بصرية
✅ سهلة جداً
✅ إدارة الفروع بسهولة
```

### GitHub CLI (سطر أوامر متقدم):

```powershell
# التثبيت
winget install GitHub.cli

# المصادقة
gh auth login

# إنشاء مستودع
gh repo create base_bot

# إنشاء PR
gh pr create --title "الميزة الجديدة"
```

---

# ❓ **الأسئلة الشائعة**

### س: هل يمكنني غير اسم المستودع؟
```
ج: نعم، في Settings → Repository → Rename
يجب بعدها تحديث الربط المحلي
```

### س: هل يمكنني حذف فرع من GitHub webui؟
```
ج: نعم، في الفرع مباشرة أم من الإعدادات
```

### س: ماذا إذا نسيت الـ push؟
```
ج: لا مشكلة، الملفات آمنة محلياً
git push origin branch-name
وكل شيء يرتفع
```

### س: هل الـ Private repo آمنة؟
```
ج: نعم، لا أحد يرى إلا من تعطيه الصلاحية
```

---

# 📌 **قائمة تحقق نهائية**

☑️ إنشاء حساب GitHub  
☑️ إنشاء مستودع جديد  
☑️ ربط المشروع المحلي  
☑️ أول push (main)  
☑️ الفروع من الرابط  
☑️ التحقق من الملفات على GitHub  
☑️ دعوة المتعاونين (اختياري)  
☑️ فعّل 2FA (اختياري لكن موصى)  
☑️ حمِ الفرع main (اختياري)  

---

مبروك! المشروع الآن على GitHub! 🎉
