from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import secrets
from send_email import send_confirmation_email

app = Flask(__name__)
app.secret_key = 'd--385vdi0xgs0^)!j0#n70hcqq+6ik4h5j%mzx5=b!7fda=o3'

DB_NAME = 'app.db'

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                is_confirmed INTEGER DEFAULT 0,
                confirm_token TEXT,
                role TEXT NOT NULL DEFAULT 'employee'
            )
        ''')
        # Тестовый админ
        cursor.execute("INSERT INTO users (email, password, is_confirmed, role) VALUES (?, ?, ?, ?)",
                       ('admin@tdm.local', 'admin', 1, 'admin'))
        conn.commit()
        conn.close()

init_db()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        token = secrets.token_urlsafe(32)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (email, password, confirm_token) VALUES (?, ?, ?)",
                (email, password, token)
            )
            conn.commit()
            send_confirmation_email(email, token)
            success = "Письмо для подтверждения отправлено на вашу почту!"
        except sqlite3.IntegrityError:
            error = "Пользователь с такой почтой уже существует!"
        conn.close()
    return render_template('register.html', error=error, success=success)


@app.route('/confirm/<token>')
def confirm_email(token):
    success = None
    error = None
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE confirm_token=? AND is_confirmed=0", (token,))
    user = cursor.fetchone()
    if user:
        cursor.execute("UPDATE users SET is_confirmed=1, confirm_token=NULL WHERE id=?", (user[0],))
        conn.commit()
        success = "Почта подтверждена! Теперь вы можете войти."
    else:
        error = "Ссылка недействительна или уже использована."
    conn.close()
    return render_template('confirm_result.html', success=success, error=error)


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    success = None
    error = None
    if request.method == 'POST':
        email = request.form['email']
        token = secrets.token_urlsafe(32)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        if user:
            cursor.execute("UPDATE users SET confirm_token=? WHERE id=?", (token, user[0]))
            conn.commit()
            from send_email import send_reset_email
            send_reset_email(email, token)
        conn.close()
        success = "Если этот email зарегистрирован, письмо со ссылкой для сброса отправлено."
    return render_template('reset_password.html', success=success, error=error)


@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    error = None
    success = None
    if request.method == 'POST':
        new_password = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE confirm_token=?", (token,))
        user = cursor.fetchone()
        if user:
            cursor.execute("UPDATE users SET password=?, confirm_token=NULL WHERE id=?", (new_password, user[0]))
            conn.commit()
            conn.close()
            success = "Пароль успешно изменён! Теперь войдите с новым паролем."
        else:
            error = "Ссылка устарела или некорректна."
            conn.close()
        return render_template('reset_with_token.html', success=success, error=error)
    return render_template('reset_with_token.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, role, is_confirmed FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            if not user[2]:
                error = "Сначала подтвердите почту — проверьте e-mail!"
            else:
                session['user_id'] = user[0]
                session['role'] = user[1]
                return redirect(url_for('dashboard'))
        else:
            error = "Неверный email или пароль!"
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
