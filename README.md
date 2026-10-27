# 🎫 Help Desk Pro - نظام إدارة خدمة العملاء

نظام متقدم لإدارة طلبات خدمة العملاء مع دعم المحادثة الفورية ولوحات تحكم شاملة.

## 🌟 المميزات

- ✅ دعم كامل للغة العربية والإنجليزية
- ✅ محادثة فورية باستخدام WebSocket
- ✅ لوحات تحكم للمدير والموظفين والعملاء
- ✅ إدارة التذاكر والتصنيفات
- ✅ تقارير وإحصائيات شاملة
- ✅ إشعارات فورية للموظفين
- ✅ تصميم عصري ومتجاوب

## 🚀 التثبيت المحلي

### المتطلبات
- Python 3.8 أو أحدث
- pip (مدير الحزم)

### خطوات التثبيت

1. **استنساخ المشروع**
```bash
cd your-project-folder
```

2. **إنشاء بيئة افتراضية**
```bash
python -m venv venv
```

3. **تفعيل البيئة الافتراضية**
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. **تثبيت المتطلبات**
```bash
pip install -r requirements.txt
```

5. **إعداد المتغيرات البيئية**
```bash
cp .env.example .env
# ثم عدّل ملف .env وضع قيمك الخاصة
```

6. **تشغيل التطبيق**
```bash
python app.py
```

7. **افتح المتصفح**
```
http://127.0.0.1:5000
```

## 👥 حسابات التجربة

### المدير (Admin)
- Email: `admin@company.com`
- Password: `123`

### موظف الدعم (Agent)
- Email: `agent@company.com`
- Password: `123`

### العميل (Customer)
- Email: `client@company.com`
- Password: `123`

## 🌍 النشر على PythonAnywhere

### الخطوات:

1. **رفع الملفات**
   - ارفع جميع ملفات المشروع على PythonAnywhere

2. **تثبيت المتطلبات**
```bash
pip install -r requirements.txt
```

3. **إعداد قاعدة البيانات**
```bash
python
>>> from app import app, db
>>> with app.app_context():
>>>     db.create_all()
>>> exit()
```

4. **إعداد WSGI**
   - في لوحة تحكم PythonAnywhere، اذهب إلى Web tab
   - اضبط WSGI configuration file على `wsgi.py`
   - تأكد من مسار المشروع صحيح

5. **تفعيل HTTPS**
   - في إعدادات الـ Web app، فعّل Force HTTPS

6. **إعادة تحميل التطبيق**
   - اضغط على Reload

## 🔒 ملاحظات أمنية مهمة

⚠️ **قبل النشر للإنتاج:**

1. غيّر `SECRET_KEY` في ملف `.env`
2. غيّر كلمات مرور الحسابات الافتراضية
3. استخدم قاعدة بيانات PostgreSQL أو MySQL بدلاً من SQLite للإنتاج
4. فعّل HTTPS
5. راجع إعدادات الأمان في `config.py`

## 📁 هيكل المشروع

```
help-desk/
├── app.py              # التطبيق الرئيسي
├── models.py           # نماذج قاعدة البيانات
├── config.py           # إعدادات التطبيق
├── wsgi.py            # نقطة دخول WSGI
├── requirements.txt    # المتطلبات
├── babel.cfg          # إعدادات الترجمة
├── static/            # الملفات الثابتة (CSS, JS, صور)
├── templates/         # قوالب HTML
├── translations/      # ملفات الترجمة
└── uploads/          # الملفات المرفوعة

```

## 🛠️ التقنيات المستخدمة

- **Backend**: Flask, Flask-SocketIO
- **Database**: SQLAlchemy (SQLite/PostgreSQL/MySQL)
- **Frontend**: HTML5, CSS3, JavaScript
- **Real-time**: Socket.IO
- **i18n**: Flask-Babel

## 📝 الترخيص

هذا المشروع مفتوح المصدر.

## 👨‍💻 المطور

تم التطوير بواسطة فريق Help Desk Pro

---

**للدعم والاستفسارات**: support@yourcompany.com
