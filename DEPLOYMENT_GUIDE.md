# 📘 دليل النشر على PythonAnywhere

## خطوة بخطوة 🚀

### 1️⃣ التحضير المسبق

#### أ. تأكد من ملف requirements.txt
```bash
pip freeze > requirements.txt
```

#### ب. اختبر التطبيق محلياً
```bash
python app.py
```
تأكد أن كل شيء يعمل بشكل صحيح!

#### ج. غيّر إعدادات الأمان
1. افتح ملف `.env`
2. غيّر `SECRET_KEY` إلى قيمة عشوائية قوية
3. غيّر كلمات المرور الافتراضية

### 2️⃣ إنشاء حساب على PythonAnywhere

1. اذهب إلى: https://www.pythonanywhere.com
2. سجّل حساب جديد (يمكنك البدء بالحساب المجاني)
3. اختر اسم مستخدم (سيكون جزء من رابط موقعك)

### 3️⃣ رفع الملفات

#### الطريقة الأولى: Git (موصى بها)
```bash
# في جهازك المحلي
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

ثم في PythonAnywhere Console:
```bash
git clone YOUR_GITHUB_REPO_URL
cd help-desk
```

#### الطريقة الثانية: رفع يدوي
- استخدم Files tab في PythonAnywhere
- ارفع كل الملفات ما عدا:
  - `__pycache__/`
  - `*.pyc`
  - `.env` (ستنشئه يدوياً)
  - `venv/`

### 4️⃣ إعداد البيئة الافتراضية

في PythonAnywhere Console:
```bash
cd ~/help-desk
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5️⃣ إعداد المتغيرات البيئية

```bash
nano .env
```

أضف المحتوى التالي:
```
SECRET_KEY=your-super-secret-random-key-here
FLASK_ENV=production
FLASK_DEBUG=False
SESSION_COOKIE_SECURE=True
```

احفظ بـ Ctrl+O ثم Enter، واخرج بـ Ctrl+X

### 6️⃣ إنشاء قاعدة البيانات

```bash
python3
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 7️⃣ إعداد Web App

1. اذهب إلى **Web** tab
2. اضغط **Add a new web app**
3. اختر **Manual Configuration**
4. اختر **Python 3.10**

### 8️⃣ تكوين WSGI

1. في Web tab، اضغط على ملف WSGI configuration
2. **امسح** كل المحتوى الموجود
3. أضف الكود التالي:

```python
import sys
import os

# مسار مجلد المشروع
project_home = '/home/YOUR_USERNAME/help-desk'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# تحميل المتغيرات البيئية
from dotenv import load_dotenv
project_folder = os.path.expanduser(project_home)
load_dotenv(os.path.join(project_folder, '.env'))

# استيراد التطبيق
from app import app as application
```

**⚠️ مهم**: غيّر `YOUR_USERNAME` باسم المستخدم الخاص بك!

### 9️⃣ إعداد Static Files

في Web tab:
1. اذهب لقسم **Static files**
2. أضف:
   - URL: `/static/`
   - Directory: `/home/YOUR_USERNAME/help-desk/static/`

### 🔟 إعداد Virtualenv

في Web tab:
1. اذهب لقسم **Virtualenv**
2. أضف المسار: `/home/YOUR_USERNAME/help-desk/venv`

### 1️⃣1️⃣ إعادة التحميل والاختبار

1. اضغط على الزر الأخضر **Reload**
2. افتح رابط موقعك: `https://YOUR_USERNAME.pythonanywhere.com`

### 1️⃣2️⃣ تفعيل HTTPS (موصى به)

في Web tab:
- فعّل خيار **Force HTTPS** ✅

---

## ⚠️ مشاكل شائعة وحلولها

### المشكلة: "Internal Server Error"
**الحل:**
1. افتح Error log في Web tab
2. اقرأ الخطأ الأخير
3. غالباً بسبب:
   - مسار خاطئ في WSGI
   - مكتبة ناقصة (راجع requirements.txt)
   - خطأ في الكود

### المشكلة: Static files لا تعمل
**الحل:**
- تأكد من إعدادات Static files صحيحة
- تأكد من المسار الكامل: `/home/YOUR_USERNAME/help-desk/static/`

### المشكلة: قاعدة البيانات فارغة
**الحل:**
```bash
python3
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### المشكلة: SocketIO لا يعمل
**ملحوظة:** PythonAnywhere المجاني لا يدعم WebSockets!
- ستحتاج حساب مدفوع
- أو استخدم بديل مثل polling

---

## 🎯 نصائح للأداء

1. **استخدم PostgreSQL في الإنتاج**
   ```python
   # في config.py
   SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@host/dbname'
   ```

2. **فعّل Gzip compression**
   ```python
   from flask_compress import Compress
   Compress(app)
   ```

3. **احذف السجلات القديمة دورياً**

4. **راقب حجم قاعدة البيانات**

---

## 📞 الدعم

إذا واجهت مشكلة:
1. راجع Error logs في PythonAnywhere
2. تأكد من اتباع الخطوات بالترتيب
3. راجع documentation الخاص بـ PythonAnywhere

---

**بالتوفيق! 🚀**
