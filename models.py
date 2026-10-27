from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# جدول المستخدمين (مدير، موظف، عميل)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'employee', 'customer'
    
    # حقول خاصة للموظف
    job_title = db.Column(db.String(100))
    status = db.Column(db.String(20), default='off_duty')  # 'on_duty', 'break', 'off_duty', 'busy'
    is_online = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # حقول خاصة للعميل
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # الموظف المسؤول (VIP)
    
    # حقول التتبع
    total_work_seconds = db.Column(db.Integer, default=0) # إجمالي ثواني العمل
    last_seen = db.Column(db.DateTime, default=datetime.utcnow) # آخر ظهور
    last_work_date = db.Column(db.Date) # تاريخ آخر يوم عمل لتصفير العداد
    
    # العلاقات
    tickets_created = db.relationship('Ticket', foreign_keys='Ticket.customer_id', backref='customer', lazy=True)
    tickets_assigned = db.relationship('Ticket', foreign_keys='Ticket.employee_id', backref='employee', lazy=True)
    
    def set_password(self, password):
        """تشفير وحفظ كلمة المرور"""
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """التحقق من صحة كلمة المرور"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)

# جدول المنتجات (البرامج اللي الشركة بتبيعها)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

# جدول التذاكر
class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    
    status = db.Column(db.String(20), default='new')  # new, in_progress, pending_user, resolved, closed
    category = db.Column(db.String(50))  # التصنيف
    internal_note = db.Column(db.Text, nullable=True) # ملاحظات الموظف الداخلية
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rating = db.Column(db.Integer, nullable=True)  # التقييم من 1 لـ 5
    rating_comment = db.Column(db.Text, nullable=True)
    closed_at = db.Column(db.DateTime) # وقت الإغلاق الفعلي لحساب السرعة

    messages = db.relationship('Message', backref='ticket', lazy=True)

# جدول الرسائل
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True) # الرد على رسالة محددة
    
    # علاقة للوصول للرسالة الأصلية
    reply_to = db.relationship('Message', remote_side=[id], backref='replies')
    
    content = db.Column(db.Text, nullable=False)
    msg_type = db.Column(db.String(10), default='text')  # text, image
    
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# جدول التصنيفات (التي يضيفها المدير)
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
# جدول الإعدادات العامة
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)

# جدول مقترحات التصنيفات (من الموظفين للمدير)
class CategorySuggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[employee_id])
