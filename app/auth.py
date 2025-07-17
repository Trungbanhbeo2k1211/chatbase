from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from app.email_sender import send_verification_email
import random
import string
from datetime import timedelta
from flask import current_app
from app.socket_events import online_users

auth_bp = Blueprint("auth", __name__, template_folder='../templates')

def generate_token(length=6):
    return ''.join(random.choices(string.digits, k=length))


import re

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True



@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not username or not email or not password:
            flash("⚠️ Vui lòng nhập đầy đủ thông tin.")
            return redirect(url_for("auth.register"))
        
        # Kiểm tra mật khẩu mạnh
        if not is_strong_password(password):
            flash("⚠️ Mật khẩu yếu. Phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.")
            return redirect(url_for("auth.register"))
        
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("⚠️ Tên đăng nhập hoặc email đã tồn tại.")
            return redirect(url_for("auth.register"))

        verify_token = generate_token()
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            verify_token=verify_token,
            is_verified=False
        )
        db.session.add(user)
        db.session.commit()
        session['email'] = email
        send_verification_email(user.email, verify_token)

        flash("✅ Đăng ký thành công! Vui lòng kiểm tra email để xác nhận.")
        return redirect(url_for("auth.verify_form"))

    return render_template("register.html")



@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        remember = request.form.get("remember")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username

            if remember:
                session.permanent = True  # giữ đăng nhập lâu hơn
                current_app.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent = False  # chỉ trong phiên trình duyệt

            # 🔵 Đánh dấu user đang online
            online_users.add(user.id)

            flash("✅ Đăng nhập thành công!")
            return redirect(url_for("home"))
        else:
            flash("⚠️ Sai tên đăng nhập hoặc mật khẩu.")

    return render_template("login.html")



@auth_bp.route("/verify", methods=["GET", "POST"])
def verify_form():
    if request.method == "POST":
        email = request.form["email"]
        code = request.form["token"]

        user = User.query.filter_by(email=email).first()
        if user and user.verify_token == code:
            user.is_verified = True
            user.verify_token = None
            db.session.commit()
            flash("✅ Tài khoản đã được xác nhận. Bạn có thể đăng nhập.")
            return redirect(url_for("auth.login"))
        else:
            flash("❌ Mã xác nhận không đúng.")

        return render_template("verify.html")
    email = session.get("email", "")
    return render_template("verify.html", email=email)


@auth_bp.route("/logout")
def logout():
    from app.socket_events import online_users  # nếu biến này nằm trong đó
    from flask_socketio import emit

    user_id = session.get("user_id")

    if user_id:
        # ❌ Xóa khỏi danh sách online
        online_users.discard(user_id)

        # 📢 Gửi sự kiện offline đến các client khác
        emit("user_offline", {"user_id": user_id}, broadcast=True, namespace="/")

    session.clear()
    flash("Đã đăng xuất")
    return redirect(url_for("auth.login"))

