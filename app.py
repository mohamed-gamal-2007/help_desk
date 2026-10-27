from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from models import db, User, Product, Category, Ticket, Message, Setting, CategorySuggestion
from datetime import datetime
from flask_babel import Babel, _
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from cache_config import init_cache, cache
from security import (
    hash_password, verify_password, login_required, admin_required, employee_required,
    log_failed_login, is_account_locked, clear_login_attempts, sanitize_input,
    validate_file_upload, get_client_ip
)
import os

# تحميل الإعدادات
from config import config

app = Flask(__name__)

# تحديد البيئة (development أو production)
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

# إعداد قاعدة البيانات
db.init_app(app)

# إعداد SocketIO
socketio = SocketIO(app)

# حماية CSRF
csrf = CSRFProtect(app)

# Rate Limiting - حماية من الهجمات
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('429.html'), 429

# التخزين المؤقت
init_cache(app)

# إعداد مجلد الملفات المرفوعة
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_locale():
    # الأولوية للغة المختارة في الجلسة، الافتراضي هو العربية
    return session.get('lang', 'ar')

babel = Babel(app, locale_selector=get_locale)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@company.com').first():
        admin = User(username='Admin User', email='admin@company.com', role='admin')
        admin.set_password('123')
        db.session.add(admin)
    if not User.query.filter_by(email='agent@company.com').first():
        agent = User(username='Sarah Ahmed', email='agent@company.com', role='employee', status='on_duty')
        agent.set_password('123')
        db.session.add(agent)
    if not User.query.filter_by(email='client@company.com').first():
        client = User(username='Mohamed Ali', email='client@company.com', role='customer')
        client.set_password('123')
        db.session.add(client)
    if not Setting.query.filter_by(key='company_name').first():
        db.session.add(Setting(key='company_name', value='Help Desk Pro'))
        
    db.session.commit()

# --- Helpers ---
def get_setting(key, default=''):
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else default

@app.context_processor
def inject_settings():
    return {
        'company_name': get_setting('company_name', 'Help Desk Pro'),
        'current_lang': session.get('lang', 'ar')
    }

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ['ar', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('chat_ui'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # حد أقصى 5 محاولات في الدقيقة

def login():
    email = sanitize_input(request.form.get('email'))
    password = request.form.get('password')
    
    
    # 1. Check lock first
    if is_account_locked(email):
        log_failed_login(email, get_client_ip())
        return render_template('login.html', error=_("تم قفل الحساب مؤقتاً. حاول مرة أخرى لاحقاً."), error_class="text-red-500")
    
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        if user.is_blocked:
            log_failed_login(email, get_client_ip())
            return render_template('login.html', error=_("عذراً، هذا الحساب محظور حالياً."), error_class="text-red-500")
        
        clear_login_attempts(email)
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session.permanent = True
        
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'employee':
            return redirect(url_for('agent_dashboard'))
        elif user.role == 'customer':
            return redirect(url_for('chat_ui'))
    
    # Failed Login Logic
    log_failed_login(email, get_client_ip())
    
    # Calculate remaining attempts
    # We need to access the store or use a new helper function
    from security import get_failed_attempts
    attempts = get_failed_attempts(email)
    remaining = 3 - attempts
    
    if remaining <= 0:
        msg = _("تم استنفاذ جميع المحاولات. تم قفل الحساب مؤقتاً.")
    else:
        msg = _(f"بيانات خطأ. متبقي لك {remaining} محاولات.")
        
    return render_template('login.html', error=msg, error_class="text-danger")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# PWA Support - Service Worker
@app.route('/service-worker.js')
def service_worker():
    from flask import send_from_directory
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    from flask import send_from_directory
    return send_from_directory('static', 'manifest.json', mimetype='application/json')


@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    # إحصائيات سريعة
    stats = {
        'new': Ticket.query.filter_by(status='new').count(),
        'in_progress': Ticket.query.filter_by(status='in_progress').count(),
        'pending': Ticket.query.filter_by(status='pending').count(),
        'resolved': Ticket.query.filter_by(status='resolved').count(),
    }
    
    # جلب آخر 5 تذاكر نشطة فقط (التي تحتوي على رسائل)
    raw_tickets = Ticket.query.filter(Ticket.status != 'resolved').order_by(Ticket.created_at.desc()).all()
    tickets = [t for t in raw_tickets if len(t.messages) > 0][:5]
    
    return render_template('admin_dashboard.html', user=session, tickets=tickets, stats=stats)

@app.route('/admin/employees')
def admin_employees():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    employees = User.query.filter_by(role='employee').all()
    return render_template('admin_employees.html', user=session, employees=employees)

@app.route('/admin/employees/add', methods=['POST'])
def add_employee():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    job_title = request.form.get('job_title')
    phone = request.form.get('phone')
    
    if User.query.filter_by(email=email).first():
        return redirect(url_for('admin_employees'))
        
    new_emp = User(username=username, email=email, role='employee', job_title=job_title, phone=phone, status='off_duty')
    new_emp.set_password(password)
    db.session.add(new_emp)
    db.session.commit()
    
    return redirect(url_for('admin_employees'))

@app.route('/admin/users/delete/<int:id>')
def delete_user(id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    user = User.query.get(id)
    if user:
        try:
            # 1. حذف جميع الرسائل والتذاكر المرتبطة بالمستخدم
            # البحث عن التذاكر التي يكون فيها المستخدم (عميل أو موظف)
            tickets = Ticket.query.filter((Ticket.customer_id == id) | (Ticket.employee_id == id)).all()
            
            for ticket in tickets:
                # حذف رسائل التذكرة أولاً
                Message.query.filter_by(ticket_id=ticket.id).delete()
                # حذف التذكرة
                db.session.delete(ticket)
            
            # 2. حذف المستخدم
            db.session.delete(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting user: {e}")
        
    # إعادة التوجيه حسب الصفحة السابقة
    return redirect(request.referrer)

@app.route('/admin/users/edit', methods=['POST'])
def edit_user():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    
    if user:
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        
        # تحديث الحقول الخاصة حسب الدور
        if user.role == 'employee':
            user.job_title = request.form.get('job_title')
        elif user.role == 'customer':
            product_id = request.form.get('product_id')
            if product_id and product_id != 'None':
                user.product_id = int(product_id)
            
        if request.form.get('password'): # تحديث الباسورد فقط لو المربع مش فاضي
            user.set_password(request.form.get('password'))
            
        db.session.commit()
        
    return redirect(request.referrer)

@app.route('/admin/users/toggle_block/<int:id>')
def toggle_block(id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    user = User.query.get(id)
    if user:
        user.is_blocked = not user.is_blocked
        db.session.commit()
        
    return redirect(request.referrer)

@app.route('/admin/customers')
def admin_customers():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    customers = User.query.filter_by(role='customer').all()
    employees = User.query.filter_by(role='employee').all() # للموظف الخاص
    products = Product.query.all() # عشان القائمة المنسدلة
    return render_template('admin_customers.html', user=session, customers=customers, employees=employees, products=products)

@app.route('/admin/customers/add', methods=['POST'])
def add_customer():
    if session.get('role') not in ['admin', 'employee']:
        return redirect(url_for('index'))
        
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    phone = request.form.get('phone')
    product_id = request.form.get('product_id')
    
    # معالجة المنتج الجديد
    if product_id == 'other':
        new_product_name = request.form.get('new_product_name')
        if new_product_name:
            # التحقق مما إذا كان المنتج موجوداً مسبقاً
            existing_prod = Product.query.filter_by(name=new_product_name).first()
            if existing_prod:
                product_id = existing_prod.id
            else:
                new_prod = Product(name=new_product_name)
                db.session.add(new_prod)
                db.session.commit()
                product_id = new_prod.id
    
    if User.query.filter_by(email=email).first():
        return redirect(request.referrer)
        
    new_cust = User(username=username, email=email, role='customer', phone=phone, product_id=product_id)
    new_cust.set_password(password)
    db.session.add(new_cust)
    db.session.commit()
    
    return redirect(request.referrer)

@app.route('/admin/tickets')
def admin_tickets():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    # جلب جميع التذاكر مرتبة بالأحدث للمدير
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template('admin_tickets.html', user=session, tickets=tickets)

@app.route('/ticket/close/<int:id>')
def close_ticket(id):
    if session.get('role') not in ['employee', 'admin']:
        return redirect(url_for('index'))
    
    ticket = Ticket.query.get(id)
    if ticket:
        ticket.status = 'resolved'
        ticket.closed_at = datetime.utcnow() # تسجيل وقت الإغلاق
        db.session.commit()
        # إشعار العميل لفتح نافذة التقييم
        socketio.emit('ticket_resolved', {'ticket_id': id}, room=f'ticket_{id}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'fetch' in request.headers.get('User-Agent', '').lower():
        return {'status': 'success'}

    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('agent_dashboard'))

@app.route('/update_work_time', methods=['POST'])
def update_work_time():
    if session.get('role') != 'employee':
        return {'status': 'error'}, 403
        
    user = User.query.get(session['user_id'])
    if user:
        today = datetime.utcnow().date()
        
        # إذا كان أول مرة يعمل اليوم، أو تاريخ آخر عمل يختلف عن اليوم -> تصفير العداد
        if not user.last_work_date or user.last_work_date != today:
            user.total_work_seconds = 0
            user.last_work_date = today
        
        # إضافة دقيقة
        user.total_work_seconds += 60
        user.last_seen = datetime.utcnow()
        db.session.commit()
    return {'status': 'success'}

@app.route('/admin/reports')
def admin_reports():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    stats = {
        'total_tickets': Ticket.query.count(),
        'resolved_tickets': Ticket.query.filter_by(status='resolved').count(),
        'active_tickets': Ticket.query.filter(Ticket.status != 'resolved').count(),
        'total_employees': User.query.filter_by(role='employee').count(),
        'total_customers': User.query.filter_by(role='customer').count(),
    }
    categories_stat = db.session.query(Ticket.category, db.func.count(Ticket.id)).group_by(Ticket.category).all()
    
    # إحصائيات الموظفين بالتفصيل
    # إحصائيات الموظفين والمديرين (كل من يتعامل مع التذاكر)
    users = User.query.filter(User.role.in_(['employee', 'admin'])).all()
    emp_performance = []
    
    for emp in users:
        # 1. التذاكر المحلولة والنشطة
        resolved_tickets = Ticket.query.filter_by(employee_id=emp.id, status='resolved').all()
        # نشمل المحلولة والمغلقة كإنجاز
        resolved_count = Ticket.query.filter(Ticket.employee_id == emp.id, Ticket.status.in_(['resolved', 'closed'])).count()
        active_count = Ticket.query.filter(Ticket.employee_id == emp.id, Ticket.status.in_(['new', 'in_progress', 'pending'])).count()
        
        # 2. متوسط التقييم (من كل التذاكر اللي اتقيمت للموظف ده)
        rated_tickets = Ticket.query.filter(Ticket.employee_id == emp.id, Ticket.rating != None).all()
        ratings = [t.rating for t in rated_tickets]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        emp_performance.append({
            'username': emp.username,
            'resolved': resolved_count,
            'active': active_count,
            'avg_rating': round(avg_rating, 1),
            'rating_count': len(ratings)
        })
    
    return render_template('admin_reports.html', user=session, stats=stats, categories_stat=categories_stat, emp_performance=emp_performance)

@app.route('/admin/settings')
def admin_settings():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    products = Product.query.all()
    admin_user = User.query.get(session['user_id'])
    suggestions = CategorySuggestion.query.filter_by(status='pending').all()
    return render_template('admin_settings.html', user=session, categories=categories, products=products, admin=admin_user, suggestions=suggestions)

@app.route('/admin/settings/suggestion/approve/<int:id>')
def approve_suggestion(id):
    sug = CategorySuggestion.query.get(id)
    if sug:
        if not Category.query.filter_by(name=sug.name).first():
            db.session.add(Category(name=sug.name))
        sug.status = 'approved'
        db.session.commit()
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/suggestion/reject/<int:id>')
def reject_suggestion(id):
    sug = CategorySuggestion.query.get(id)
    if sug:
        sug.status = 'rejected'
        db.session.commit()
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/system', methods=['POST'])
def update_system_settings():
    company_name = request.form.get('company_name')
    if company_name:
        set_val = Setting.query.filter_by(key='company_name').first()
        if not set_val:
            set_val = Setting(key='company_name', value=company_name)
            db.session.add(set_val)
        else:
            set_val.value = company_name
        db.session.commit()
    flash(_('تم تحديث إعدادات النظام بنجاح'))
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/profile', methods=['POST'])
def update_admin_profile():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    
    admin = User.query.get(session['user_id'])
    if admin:
        admin.username = username
        admin.email = email
        if password:
            admin.password = password
        db.session.commit()
        session['username'] = username
        flash(_('تم تحديث الملف الشخصي بنجاح'))
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/category/add', methods=['POST'])
def add_category_setting():
    name = request.form.get('name')
    if name:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
            db.session.commit()
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/category/delete/<int:id>')
def delete_category_setting(id):
    cat = Category.query.get(id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/product/add', methods=['POST'])
def add_product_setting():
    name = request.form.get('name')
    if name:
        if not Product.query.filter_by(name=name).first():
            db.session.add(Product(name=name))
            db.session.commit()
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/product/delete/<int:id>')
def delete_product_setting(id):
    prod = Product.query.get(id)
    if prod:
        db.session.delete(prod)
        db.session.commit()
    return redirect(url_for('admin_settings'))

@app.route('/ticket/update_category', methods=['POST'])
def update_ticket_category():
    data = request.json
    ticket_id = data.get('ticket_id')
    new_category = data.get('category')
    
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        # إذا كان التصنيف يبدأ بـ "أخرى: "، نقوم بإضافته كمقترح للمدير
        if new_category.startswith("أخرى: "):
            suggested_name = new_category.replace("أخرى: ", "").strip()
            # التحقق مما إذا كان موجوداً مسبقاً في التصنيفات أو المقترحات
            if not Category.query.filter_by(name=suggested_name).first():
                existing_suggestion = CategorySuggestion.query.filter_by(name=suggested_name, status='pending').first()
                if not existing_suggestion:
                    suggestion = CategorySuggestion(name=suggested_name, employee_id=session.get('user_id'))
                    db.session.add(suggestion)
            
            ticket.category = suggested_name
        else:
            ticket.category = new_category
            
        db.session.commit()
        return {'status': 'success'}
    return {'status': 'error'}, 404

@app.route('/ticket/save_note', methods=['POST'])
def save_ticket_note():
    data = request.json
    ticket_id = data.get('ticket_id')
    note = data.get('note')
    
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        ticket.internal_note = note
        db.session.commit()
        return {'status': 'success'}
    return {'status': 'error'}, 404

from werkzeug.utils import secure_filename
import os

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/agent/dashboard')
def agent_dashboard():
    if session.get('role') != 'employee':
        return redirect(url_for('index'))
    
    # تصحيح الخطأ: استخدام كائن User المحدث من القاعدة بدلاً من الـ session
    # لضمان قراءة عداد الوقت الصحيح
    current_user = User.query.get(session['user_id'])
    
    # جلب كل التذاكر النشطة (غير المحلولة)
    raw_tickets = Ticket.query.filter(Ticket.status != 'resolved').order_by(Ticket.created_at.desc()).all()
    # إخفاء التذاكر التي لا تحتوي على رسائل
    all_active_tickets = [t for t in raw_tickets if len(t.messages) > 0]
    
    # إحصائيات الموظف
    emp_id = session['user_id']
    stats = {
        'resolved': Ticket.query.filter_by(employee_id=emp_id, status='resolved').count(),
        'active': Ticket.query.filter_by(employee_id=emp_id, status='in_progress').count(),
    }
    
    products = Product.query.all()
    # تمرير current_user بدلاً من user=session
    return render_template('agent_dashboard.html', user=current_user, tickets=all_active_tickets, stats=stats, products=products)

@app.route('/ticket/join/<int:id>')
def join_ticket(id):
    if session.get('role') != 'employee':
        return redirect(url_for('index'))
        
    ticket = Ticket.query.get(id)
    if ticket:
        if not ticket.employee_id:
            ticket.employee_id = session['user_id']
            ticket.status = 'in_progress'
            db.session.commit()
            
            # إشعار لكل الموظفين بتحديث القائمة
            socketio.emit('update_dashboard', {'ticket_id': id, 'action': 'taken'})
    
    return redirect(url_for('chat_ui', ticket_id=id))



@app.route('/chat')
def chat_ui():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    role = session['role']
    ticket_id = request.args.get('ticket_id')
    ticket = None
    force_rating = False
    
    if role == 'customer':
        # التحقق أولاً من وجود تذكرة محلولة لم يتم تقييمها
        unrated_ticket = Ticket.query.filter_by(customer_id=user_id, status='resolved', rating=None).order_by(Ticket.closed_at.desc()).first()
        
        if unrated_ticket:
            ticket = unrated_ticket
            force_rating = True
        else:
            # العميل يذهب لآخر تذكرة نشطة أو ينشئ جديدة
            ticket = Ticket.query.filter_by(customer_id=user_id).filter(Ticket.status != 'resolved').first()
            if not ticket:
                # التحقق من وجود موظف مخصص (VIP)
                customer = User.query.get(user_id)
                assigned_agent = customer.assigned_agent_id if customer else None
                
                ticket = Ticket(customer_id=user_id, status='new')
                if assigned_agent:
                    ticket.employee_id = assigned_agent
                    ticket.status = 'in_progress' # تعيين مباشر
                
                db.session.add(ticket)
                db.session.commit()
            
    elif (role == 'employee' or role == 'admin') and ticket_id:
        ticket = Ticket.query.get(ticket_id)
        # حماية للموظف: التأكد أن التذكرة إما جديدة أو تابعة له
        if role == 'employee' and ticket.employee_id and ticket.employee_id != user_id:
             return redirect(url_for('agent_dashboard'))
    else:
        # لو موظف دخل بدون رقم تذكرة يروح الداشبورد
        return redirect(url_for('agent_dashboard'))
            
    messages = []
    if ticket:
        messages = Message.query.filter_by(ticket_id=ticket.id).all()
        
    categories = Category.query.all()
    # جلب قائمة الموظفين الآخرين للتحويل
    all_employees = User.query.filter_by(role='employee').filter(User.id != user_id).all()
    
    return render_template('chat.html', user=session, ticket=ticket, messages=messages, 
                           categories=categories, force_rating=force_rating, employees=all_employees)

@app.route('/ticket/transfer/<int:id>', methods=['POST'])
def transfer_ticket(id):
    if session.get('role') not in ['admin', 'employee']:
        return redirect(url_for('index'))
    
    new_agent_id = request.form.get('agent_id')
    ticket = Ticket.query.get(id)
    
    if ticket and new_agent_id:
        ticket.employee_id = int(new_agent_id)
        ticket.status = 'in_progress'
        db.session.commit()
        
        # إشعار للموظف الجديد
        socketio.emit('notification', {
            'title': _('تذكرة محولة'),
            'message': _('تم تحويل التذكرة #%(id)s إليك') % {'id': id}
        }, room=f"user_{new_agent_id}")
        
    return redirect(url_for('agent_dashboard'))

# --- SocketIO Events ---

@socketio.on('join')
def on_join(data):
    # دخول غرفة التذكرة (للمحادثة)
    if 'room' in data:
        join_room(data['room'])
        
    # دخول غرفة المستخدم الخاصة (للإشعارات الشخصية)
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")
    
    print(f"User {session.get('username')} joined rooms")

@socketio.on('send_message')
def handle_send_message_event(data):
    content = data['message']
    ticket_id = data['ticket_id']
    user_id = session['user_id']
    reply_to_id = data.get('reply_to_id')
    
    # 1. حفظ الرسالة في قاعدة البيانات
    new_msg = Message(ticket_id=ticket_id, sender_id=user_id, content=content, reply_to_id=reply_to_id)
    db.session.add(new_msg)
    
    ticket = Ticket.query.get(ticket_id)
    msg_count = Message.query.filter_by(ticket_id=ticket_id).count()
    
    # التعامل مع تذاكر العميل المعلقة
    if session.get('role') == 'customer' and ticket.status == 'pending':
        ticket.status = 'in_progress'
        if ticket.employee_id:
            socketio.emit('notification', {
                'title': _('رد على تذكرة معلقة'),
                'message': _('العميل %(customer)s رد على التذكرة #%(ticket_id)s') % {'customer': session["username"], 'ticket_id': ticket.id},
                'ticket_id': ticket.id,
                'customer': session["username"],
                'time': datetime.now().strftime('%I:%M %p')
            }, room=f"user_{ticket.employee_id}")

    # إشعار بوجود تذكرة جديدة للموظفين
    if msg_count == 0:
        socketio.emit('new_ticket', {'id': ticket.id, 'company': _('عام')})
        
    db.session.commit()
    
    # تحضير محتوى الرد للعرض
    reply_content = None
    if reply_to_id:
        original_msg = Message.query.get(reply_to_id)
        if original_msg:
            if '<img' in original_msg.content:
                reply_content = "📷 " + _("صورة")
            else:
                reply_content = original_msg.content[:50] + "..." if len(original_msg.content) > 50 else original_msg.content

    # إرسال الرسالة للجميع في الغرفة
    emit('receive_message', {
        'content': content,
        'sender_id': user_id,
        'is_me': False, # سيتم ضبطه في الفرونت
        'username': session['username'],
        'time': datetime.now().strftime('%I:%M %p'),
        'id': new_msg.id,
        'reply_to': reply_content
    }, room=f'ticket_{ticket_id}')


@app.route('/submit_rating', methods=['POST'])
def submit_rating():
    try:
        data = request.json
        ticket_id = data.get('ticket_id')
        rating = data.get('rating')
        
        if not ticket_id or rating is None:
            return {'status': 'error', 'message': 'Missing data'}, 400
            
        ticket = Ticket.query.get(int(ticket_id))
        if ticket:
            ticket.rating = int(rating)
            db.session.commit()
            return {'status': 'success'}
        
        return {'status': 'error', 'message': 'Ticket not found'}, 404
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting rating: {e}")
        return {'status': 'error', 'message': str(e)}, 500

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
