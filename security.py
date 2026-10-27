"""
وحدة الأمان - Security Module
تحتوي على دوال الأمان والحماية
"""

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from datetime import datetime, timedelta
import logging

# إعداد تسجيل الأحداث
logging.basicConfig(
    filename='security.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# تخزين محاولات الدخول الفاشلة
failed_login_attempts = {}

def hash_password(password):
    """تشفير كلمة المرور"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(password_hash, password):
    """التحقق من كلمة المرور"""
    return check_password_hash(password_hash, password)

def login_required(f):
    """
    Decorator للتأكد من تسجيل الدخول
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator للتأكد من صلاحيات المدير
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def employee_required(f):
    """
    Decorator للتأكد من صلاحيات الموظف
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') not in ['admin', 'employee']:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def log_failed_login(email, ip_address):
    """
    تسجيل محاولات الدخول الفاشلة
    """
    logging.warning(f'Failed login attempt - Email: {email}, IP: {ip_address}')
    
    # تتبع محاولات الدخول الفاشلة
    if email not in failed_login_attempts:
        failed_login_attempts[email] = []
    
    failed_login_attempts[email].append({
        'ip': ip_address,
        'time': datetime.now()
    })
    
    # حذف المحاولات القديمة (أكثر من ساعة)
    cutoff_time = datetime.now() - timedelta(hours=1)
    failed_login_attempts[email] = [
        attempt for attempt in failed_login_attempts[email]
        if attempt['time'] > cutoff_time
    ]

def get_failed_attempts(email):
    """
    الحصول على عدد المحاولات الفاشلة الحالية
    """
    if email in failed_login_attempts:
        return len(failed_login_attempts[email])
    return 0

def is_account_locked(email):
    """
    التحقق من قفل الحساب بعد محاولات فاشلة متكررة
    """
    if email not in failed_login_attempts:
        return False
    
    # تعديل: 3 محاولات فقط حسب طلب المستخدم
    recent_attempts = len(failed_login_attempts[email])
    if recent_attempts >= 3:
        return True
    
    return False

def clear_login_attempts(email):
    """
    مسح محاولات الدخول الفاشلة بعد نجاح الدخول
    """
    if email in failed_login_attempts:
        del failed_login_attempts[email]

def sanitize_input(text):
    """
    تنظيف المدخلات من HTML/JavaScript الضار
    """
    if not text:
        return text
    
    # إزالة العلامات الخطرة
    dangerous_patterns = ['<script', '</script>', 'javascript:', 'onerror=', 'onclick=']
    for pattern in dangerous_patterns:
        text = text.replace(pattern, '')
    
    return text.strip()

def validate_file_upload(filename, allowed_extensions={'png', 'jpg', 'jpeg', 'gif'}):
    """
    التحقق من امتداد الملف المرفوع
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions

def get_client_ip():
    """
    الحصول على IP الحقيقي للمستخدم
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr
