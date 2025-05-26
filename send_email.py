import smtplib
from email.mime.text import MIMEText

def send_confirmation_email(to_email, token):
    from_email = "ooo.tdm00@gmail.com"  # или Яндекс
    password = "xgen qxfs kvfv krih"
    confirm_link = f"http://127.0.0.1:5000/confirm/{token}"
    subject = "Подтвердите регистрацию в ООО «ТДМ»"
    body = f"Здравствуйте!\n\nДля завершения регистрации перейдите по ссылке:\n{confirm_link}\n\nЕсли вы не регистрировались — просто проигнорируйте это письмо."
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, password)
        server.send_message(msg)

def send_reset_email(to_email, token):
    from_email = "ooo.tdm00@gmail.com"  # или Яндекс
    password = "xgen qxfs kvfv krih"
    reset_link = f"http://127.0.0.1:5000/reset/{token}"
    subject = "Восстановление пароля в ООО «ТДМ»"
    body = f"Для сброса пароля перейдите по ссылке:\n{reset_link}\n\nЕсли вы не запрашивали сброс пароля — просто проигнорируйте это письмо."
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, password)
        server.send_message(msg)

