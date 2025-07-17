from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.models import User
from app.extensions import db
from werkzeug.utils import secure_filename
import os
from app.models import Friend

bp_profile = Blueprint("profile", __name__, url_prefix="/profile")


UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@bp_profile.route("/", methods=["GET", "POST"])
def view():
    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    # Lấy danh sách người bị bạn chặn
    from app.models import Friend
    blocked_users = db.session.query(User).join(
        Friend,
        (Friend.friend_id == User.id) &
        (Friend.user_id == user.id) &
        (Friend.status == "blocked")
    ).all()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()

        if not email:
            flash("Email không được để trống!", "danger")
            return redirect(url_for("profile.view"))

        avatar = request.files.get("avatar")
        if avatar and avatar.filename:
            filename = secure_filename(avatar.filename)
            avatar_path = os.path.join(UPLOAD_FOLDER, filename)
            avatar.save(avatar_path)
            user.avatar_url = f"uploads/{filename}"

        user.full_name = full_name
        user.email = email
        db.session.commit()

        flash("Cập nhật hồ sơ thành công!", "success")
        return redirect(url_for("profile.view"))

    return render_template("profile.html", user=user, blocked_users=blocked_users)




@bp_profile.route("/view/<int:user_id>")
def view_profile(user_id):
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]
    user = User.query.get_or_404(user_id)

    # Quan hệ giữa current_user và người đang xem
    relationship = Friend.query.filter(
        ((Friend.user_id == current_user_id) & (Friend.friend_id == user_id)) |
        ((Friend.user_id == user_id) & (Friend.friend_id == current_user_id))
    ).first()

    # Phân tích trạng thái
    status = "self" if current_user_id == user_id else (
        relationship.status if relationship else "none"
    )

    blocked_by_you = (relationship and relationship.status == "blocked" and relationship.user_id == current_user_id)
    blocked_you = (relationship and relationship.status == "blocked" and relationship.user_id == user_id)

    return render_template("user_profile.html", user=user, status=status,
                           blocked_by_you=blocked_by_you, blocked_you=blocked_you)
