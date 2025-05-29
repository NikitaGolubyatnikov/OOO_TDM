from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
import secrets
from send_email import send_confirmation_email, send_reset_email
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'd--385vdi0xgs0^)!j0#n70hcqq+6ik4h5j%mzx5=b!7fda=o3'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Подключение к PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://ooo_tdm_user:rvZtUKexokiupiyU0iYAl45qAwt8uvwd@dpg-d0qu4g6mcj7s73edjv5g-a.oregon-postgres.render.com/ooo_tdm")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

'''# Для работы на Render (PostgreSQL):
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://ooo_tdm_user:...")

# Для локальной разработки (SQLite):
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///tdm_local.db"'''


db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    confirm_token = db.Column(db.String(64), nullable=True)
    role = db.Column(db.String(32), default='employee')

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class NewsFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey('news.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)

    news = db.relationship('News', backref=db.backref('files', lazy=True))



# Инициализация БД
with app.app_context():
    db.create_all()
    # Добавляем тестового администратора только если его нет
    if not User.query.filter_by(email='admin@tdm.local').first():
        admin = User(email='admin@tdm.local', password='admin', is_confirmed=True, role='admin')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error, success = None, None
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        token = secrets.token_urlsafe(32)
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = "Пользователь с такой почтой уже существует!"
        else:
            user = User(email=email, password=password, confirm_token=token)
            db.session.add(user)
            db.session.commit()
            send_confirmation_email(email, token)
            success = "Письмо для подтверждения отправлено на вашу почту!"
    return render_template('register.html', error=error, success=success)

@app.route('/confirm/<token>')
def confirm_email(token):
    user = User.query.filter_by(confirm_token=token, is_confirmed=False).first()
    if user:
        user.is_confirmed = True
        user.confirm_token = None
        db.session.commit()
        return render_template('confirm_result.html', success="Почта подтверждена! Теперь вы можете войти.")
    return render_template('confirm_result.html', error="Ссылка недействительна или уже использована.")

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    success, error = None, None
    if request.method == 'POST':
        email = request.form['email']
        token = secrets.token_urlsafe(32)
        user = User.query.filter_by(email=email).first()
        if user:
            user.confirm_token = token
            db.session.commit()
            send_reset_email(email, token)
        success = "Если этот email зарегистрирован, письмо отправлено."
    return render_template('reset_password.html', success=success, error=error)

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    error, success = None, None
    user = User.query.filter_by(confirm_token=token).first()
    if request.method == 'POST':
        if user:
            user.password = request.form['password']
            user.confirm_token = None
            db.session.commit()
            success = "Пароль успешно изменён! Теперь войдите с новым паролем."
        else:
            error = "Ссылка устарела или некорректна."
    return render_template('reset_with_token.html', success=success, error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            if not user.is_confirmed:
                error = "Сначала подтвердите почту!"
            else:
                session['user_id'], session['role'] = user.id, user.role
                return redirect(url_for('dashboard'))
        else:
            error = "Неверный email или пароль!"
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    if role == 'admin':
        return render_template('admin_dashboard.html')
    elif role == 'news_admin':
        return render_template('news_admin_dashboard.html')
    return render_template('employee_dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Панель управления пользователями (для админа)
# --------------------------

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def admin_users():
    users = User.query.order_by(User.id).all()
    error = None
    if request.method == 'POST':
        # Меняем роль пользователя
        if 'set_role' in request.form:
            user_id = int(request.form['user_id'])
            new_role = request.form['role']
            user = User.query.get(user_id)
            if user:
                # Не позволяем лишать себя последнего админа
                if user.role == 'admin' and new_role != 'admin':
                    admins = User.query.filter_by(role='admin').count()
                    if admins <= 1 and user.id == session['user_id']:
                        error = "Нельзя лишить себя роли последнего администратора!"
                    else:
                        user.role = new_role
                        db.session.commit()
                else:
                    user.role = new_role
                    db.session.commit()
        # Удаляем пользователя
        if 'delete_user' in request.form:
            user_id = int(request.form['user_id'])
            user = User.query.get(user_id)
            if user:
                if user.id == session['user_id']:
                    error = "Нельзя удалить самого себя!"
                elif user.role == 'admin':
                    admins = User.query.filter_by(role='admin').count()
                    if admins <= 1:
                        error = "Нельзя удалить последнего администратора!"
                    else:
                        db.session.delete(user)
                        db.session.commit()
                else:
                    db.session.delete(user)
                    db.session.commit()
    users = User.query.order_by(User.id).all()  # Обновляем список
    return render_template('admin_users.html', users=users, error=error)

# Декоратор для новостного админа
def news_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'news_admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Список новостей и управление (news_admin)
@app.route('/news_admin/news')
@news_admin_required
def news_admin_news():
    news = News.query.order_by(News.created_at.desc()).all()
    return render_template('news_admin_news.html', news=news)

# Редактировать новость
@app.route('/news_admin/news/edit/<int:news_id>', methods=['GET', 'POST'])
@news_admin_required
def edit_news(news_id):
    news = News.query.get_or_404(news_id)
    error = None
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if not title or not content:
            error = "Заполни все поля!"
        else:
            news.title = title
            news.content = content
            db.session.commit()
            return redirect(url_for('news_admin_news'))
    return render_template('news_add_edit.html', action="Редактировать", news=news, error=error)

# Удалить новость
@app.route('/news_admin/news/delete/<int:news_id>', methods=['POST'])
@news_admin_required
def delete_news(news_id):
    news = News.query.get_or_404(news_id)
    db.session.delete(news)
    db.session.commit()
    return redirect(url_for('news_admin_news'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Добавить новость

@app.route('/news_admin/news/add', methods=['GET', 'POST'])
@news_admin_required
def add_news():
    error = None
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if not title or not content:
            error = "Заполни все поля!"
        else:
            news = News(title=title, content=content, created_by=session['user_id'])
            db.session.add(news)
            db.session.commit()
            # --- Работа с несколькими файлами ---
            files = request.files.getlist('files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Чтобы имена не дублировались
                    unique_filename = f"{news.id}_{secrets.token_hex(6)}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                    db.session.add(NewsFile(news_id=news.id, file_name=unique_filename))
            db.session.commit()
            return redirect(url_for('news_admin_news'))
    return render_template('news_add_edit.html', action="Добавить", error=error)

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
#удаление файла
@app.route('/news_admin/news/delete_file/<int:file_id>', methods=['POST'])
@news_admin_required
def delete_news_file(file_id):
    file = NewsFile.query.get_or_404(file_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(file)
    db.session.commit()
    # Вернёмся на редактирование новости
    return redirect(url_for('edit_news', news_id=file.news_id))

@app.route('/news_admin/dashboard')
@news_admin_required
def news_admin_dashboard():
    return render_template('news_admin_dashboard.html')




if __name__ == '__main__':
    app.run(debug=True)
