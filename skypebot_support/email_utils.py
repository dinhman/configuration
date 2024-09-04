import smtplib
from email.mime.text import MIMEText
import re

def is_valid_email(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def extract_email(html):
    # Tìm kiếm địa chỉ email trong chuỗi HTML
    match = re.search(r'mailto:(.*?)"', html)
    return match.group(1) if match else None

def send_email(subject, body, to_email):
    from_email = "notification@longangroup.vn"
    password = "77CtiNAnDELLio"

    # Trích xuất địa chỉ email nếu nó có định dạng HTML
    if '<a href="mailto:' in to_email:
        to_email = extract_email(to_email)

    if not is_valid_email(to_email):
        print(f"Địa chỉ email không hợp lệ: {to_email}")
        return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP('mail.longangroup.vn', 587) as server:
            server.starttls()
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        print("Email đã được gửi thành công!")
    except Exception as e:
        print(f"Đã xảy ra lỗi khi gửi email: {e}")
