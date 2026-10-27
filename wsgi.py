"""
ملف WSGI للنشر على خوادم الإنتاج
يستخدم هذا الملف مع PythonAnywhere أو أي خادم WSGI آخر
"""

import os
from app import app, socketio

# تعيين بيئة الإنتاج
os.environ['FLASK_ENV'] = 'production'

# للنشر على PythonAnywhere، استخدم app مباشرة
# application = app

# للاستخدام مع gunicorn + socketio
if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
