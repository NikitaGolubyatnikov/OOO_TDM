from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import secrets
from send_email import send_confirmation_email, send_reset_email

app = Flask(__name__)
app.secret_key = 'd--385vdi0xgs0^)!j0#n70hcqq+6ik4h5j%mzx5=b!7fda=o3'

# Подключение к PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://ooo_tdm_user:rvZtUKexokiupiyU0iYAl45qAwt8uvwd@dpg-d0qu4g6mcj7s73edjv5g-a.oregon-postgres.render.com/ooo_tdm")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    confirm_token = db.Column(db.String(64), nullable=True)
    role = db.Column(db.String(32), default='employee')

# Инициализация БД
with app.app_context():
    db.create_all()

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

if __name__ == '__main__':
    app.run(debug=True)
