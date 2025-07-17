from flask import Blueprint, request, session, redirect, url_for, flash
from app.models import User, Friend
from app.extensions import db

bp_friend = Blueprint("friend", __name__)


@bp_friend.route("/add-friend", methods=["POST"])
def add_friend():
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]
    username = request.form.get("username", "").strip()

    if not username or username == session.get("username"):
        flash("Tên người dùng không hợp lệ!", "warning")
        return redirect(url_for("home"))

    # Tìm người dùng theo username
    target = User.query.filter_by(username=username).first()
    if not target:
        flash("Không tìm thấy người dùng.", "danger")
        return redirect(url_for("home"))

    # Kiểm tra đã có mối quan hệ bạn bè chưa (dù chiều nào)
    existing = Friend.query.filter(
        ((Friend.user_id == current_user_id) & (Friend.friend_id == target.id)) |
        ((Friend.user_id == target.id) & (Friend.friend_id == current_user_id))
    ).first()

    if existing:
        if existing.status == "accepted":
            flash("Bạn đã là bạn bè với người này rồi.", "info")
        elif existing.status == "pending":
            if existing.user_id == current_user_id:
                flash("Bạn đã gửi lời mời trước đó.", "info")
            else:
                flash("Người này đã gửi lời mời cho bạn. Hãy chấp nhận!", "info")
        return redirect(url_for("home"))

    # Tạo lời mời mới
    friend = Friend(user_id=current_user_id, friend_id=target.id, status="pending")
    db.session.add(friend)
    db.session.commit()

    flash(f"Đã gửi lời mời kết bạn đến {username}", "success")
    return redirect(url_for("home"))


# Chấp nhận lời mời
@bp_friend.route("/accept-friend/<int:user_id>", methods=["POST"])
def accept_friend(user_id):
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]

    # Tìm mối quan hệ cần xác nhận
    friend_req = Friend.query.filter_by(user_id=user_id, friend_id=current_user_id, status="pending").first()

    if not friend_req:
        flash("Lời mời không tồn tại hoặc đã được xử lý.", "warning")
        return redirect(url_for("home"))

    friend_req.status = "accepted"
    db.session.commit()

    flash("Đã chấp nhận lời mời kết bạn.", "success")
    return redirect(url_for("home"))



@bp_friend.route("/cancel-request/<int:user_id>", methods=["POST"])
def cancel_request(user_id):
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]

    # Tìm lời mời đã gửi
    friend_req = Friend.query.filter_by(user_id=current_user_id, friend_id=user_id, status="pending").first()

    if not friend_req:
        flash("Không tìm thấy lời mời để huỷ.", "warning")
        return redirect(url_for("home"))

    db.session.delete(friend_req)
    db.session.commit()

    flash("Đã huỷ lời mời kết bạn.", "info")
    return redirect(url_for("home"))

@bp_friend.route("/reject-friend/<int:user_id>", methods=["POST"])
def reject_friend(user_id):
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]

    friend_req = Friend.query.filter_by(user_id=user_id, friend_id=current_user_id, status="pending").first()

    if not friend_req:
        flash("Không tìm thấy lời mời để từ chối.", "warning")
        return redirect(url_for("home"))

    db.session.delete(friend_req)
    db.session.commit()

    flash("Đã từ chối lời mời kết bạn.", "info")
    return redirect(url_for("home"))


@bp_friend.route("/block-user/<int:user_id>", methods=["POST"])
def block_user(user_id):
    if "user_id" not in session:
        return redirect("/login")
    current_user_id = session["user_id"]

    # Kiểm tra xem đã có quan hệ gì chưa
    relationship = Friend.query.filter(
        ((Friend.user_id == current_user_id) & (Friend.friend_id == user_id)) |
        ((Friend.user_id == user_id) & (Friend.friend_id == current_user_id))
    ).first()

    if relationship:
        relationship.user_id = current_user_id  # Đảm bảo chiều block đúng
        relationship.friend_id = user_id
        relationship.status = "blocked"
    else:
        # Nếu chưa có quan hệ nào → thêm mới
        relationship = Friend(user_id=current_user_id, friend_id=user_id, status="blocked")
        db.session.add(relationship)

    db.session.commit()
    flash("Đã chặn người dùng.", "info")
    return redirect(url_for("home"))


@bp_friend.route("/unblock-user/<int:user_id>", methods=["POST"])
def unblock_user(user_id):
    if "user_id" not in session:
        return redirect("/login")
    current_user_id = session["user_id"]

    # Tìm quan hệ "block"
    block = Friend.query.filter_by(user_id=current_user_id, friend_id=user_id, status="blocked").first()
    if block:
        db.session.delete(block)
        db.session.commit()
        flash("Đã bỏ chặn người dùng.", "info")
    else:
        flash("Không tìm thấy người dùng bị chặn.", "warning")

    return redirect(url_for("home"))

@bp_friend.route("/unfriend/<int:user_id>", methods=["POST"])
def unfriend(user_id):
    if "user_id" not in session:
        return redirect("/login")

    current_user_id = session["user_id"]

    # Tìm quan hệ bạn bè theo cả hai chiều
    friendship = Friend.query.filter(
        ((Friend.user_id == current_user_id) & (Friend.friend_id == user_id)) |
        ((Friend.user_id == user_id) & (Friend.friend_id == current_user_id))
    ).filter(Friend.status == "accepted").first()

    if not friendship:
        flash("Hai người không phải là bạn bè!", "warning")
        return redirect(url_for("home"))

    db.session.delete(friendship)
    db.session.commit()

    flash("Đã xoá bạn bè.", "info")
    return redirect(url_for("home"))
