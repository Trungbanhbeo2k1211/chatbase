from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, Group, GroupMember, Friend
from app.extensions import db
from sqlalchemy import or_

group_bp = Blueprint("group", __name__)

@group_bp.route("/create-group", methods=["GET", "POST"])
def create_group():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    # Lấy danh sách bạn bè
    friends = (
        db.session.query(User)
        .join(Friend, or_(
            (Friend.user_id == user_id) & (Friend.friend_id == User.id),
            (Friend.friend_id == user_id) & (Friend.user_id == User.id)
        ))
        .filter(Friend.status == "accepted")
        .distinct()
        .all()
    )

    if request.method == "POST":
        name = request.form.get("name")
        selected_ids = request.form.getlist("members")  # list of user_id (string)

        if not name:
            flash("Vui lòng nhập tên nhóm.", "danger")
            return redirect(url_for("group.create_group"))

        selected_ids = list(set(selected_ids))  # loại trùng
        if len(selected_ids) < 2:  # 2 bạn + người tạo là 3
            flash("Phải chọn ít nhất 2 người bạn để tạo nhóm (tổng cộng 3 người).", "danger")
            return redirect(url_for("group.create_group"))

        # Tạo nhóm
        group = Group(name=name, creator_id=user_id)
        db.session.add(group)
        db.session.commit()

        # Thêm người tạo vào thành viên
        db.session.add(GroupMember(user_id=user_id, group_id=group.id, is_admin=True))

        # Thêm thành viên được chọn
        for uid in selected_ids:
            db.session.add(GroupMember(user_id=int(uid), group_id=group.id))

        db.session.commit()
        flash("Tạo nhóm thành công!", "success")
        return redirect(url_for("chat.chat_page"))

    return render_template("group_create.html", friends=friends)
