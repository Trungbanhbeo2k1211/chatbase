from flask import Blueprint, request, session
from flask import jsonify
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from app.extensions import db
from app.models import GroupMessage, Attachment, Group, GroupMember
from app.extensions import socketio

group_message_bp = Blueprint("group_message", __name__)

UPLOAD_FOLDER = "static/uploads"

@group_message_bp.route("/send-group-message", methods=["POST"])
def send_group_message():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    user_id = session["user_id"]
    username = session["username"]
    avatar_url = session.get("avatar_url", "")

    group_id = request.form.get("group_id")
    message = request.form.get("message", "").strip()
    files = request.files.getlist("files")

    if not group_id:
        return jsonify({"error": "Thiếu group_id"}), 400

    group_id = int(group_id)

    # ✅ Sửa lỗi: dùng 'content' thay vì 'message'
    new_msg = GroupMessage(
        group_id=group_id,
        sender_id=user_id,
        content=message if message else None,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_msg)
    db.session.flush()

    attachments = []

    for file in files:
        filename = secure_filename(file.filename)
        if not filename:
            continue

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        ext = filename.split(".")[-1].lower()
        file_type = "file"
        if ext in ["jpg", "jpeg", "png", "gif"]:
            file_type = "image"
        elif ext in ["mp4", "webm", "mov"]:
            file_type = "video"

        att = Attachment(
            group_message_id=new_msg.id,
            url=save_path.replace("static/", "/static/"),
            file_type=file_type,
            filename=filename
        )
        db.session.add(att)
        attachments.append({
            "file_url": f"/static/uploads/{filename}",                             #Sửa ở đây att.url
            "file_type": att.file_type,
            "filename": att.filename
        })

    db.session.commit()
    
    socketio.emit("receive_group_message", {                                       # Sửa ở đây
        "group_id": group_id,                                                                       
        "username": username,
        "avatar_url": avatar_url,
        "message": message,
        "timestamp": new_msg.timestamp.strftime("%H:%M"),
        "attachments": attachments
    }, room=f"group_{group_id}")

    return jsonify({
        "success": True,
        "message": "Đã gửi",
        "data": {
            "group_id": group_id,
            "username": username,
            "avatar_url": avatar_url,
            "message": message,
            "timestamp": new_msg.timestamp.strftime("%H:%M"),
            "attachments": attachments
        }
    })



@group_message_bp.route("/create-group", methods=["POST"])
def create_group():
    if "user_id" not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    creator_id = session["user_id"]
    group_name = request.form.get("group_name", "").strip()
    selected_ids = request.form.getlist("member_ids")  # Danh sách ID bạn bè được chọn

    if not group_name:
        return jsonify({"error": "Tên nhóm không được để trống"}), 400

    # Chuyển đổi thành int
    try:
        selected_ids = list(map(int, selected_ids))
    except ValueError:
        return jsonify({"error": "Danh sách thành viên không hợp lệ"}), 400

    if len(selected_ids) < 2:
        return jsonify({"error": "Phải chọn ít nhất 2 bạn bè để tạo nhóm"}), 400

    # Tạo nhóm
    new_group = Group(name=group_name, creator_id=creator_id)
    db.session.add(new_group)
    db.session.flush()  # để lấy new_group.id

    # Thêm người tạo vào nhóm
    db.session.add(GroupMember(user_id=creator_id, group_id=new_group.id))

    # Thêm các bạn bè được chọn vào nhóm
    for friend_id in selected_ids:
        db.session.add(GroupMember(user_id=friend_id, group_id=new_group.id))

    db.session.commit()

    return jsonify({"success": True, "message": "Đã tạo nhóm thành công!"})