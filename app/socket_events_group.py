import os
from flask import request, session, Blueprint
from flask_socketio import emit, join_room
from werkzeug.utils import secure_filename
from datetime import datetime
from app.extensions import socketio, db
from app.models import User, Group, GroupMember, GroupMessage, Attachment

UPLOAD_FOLDER = "static/uploads"

# ----------------------------
# 1. WebSocket: Tham gia phòng
# ----------------------------
@socketio.on("join_room")
def handle_join_group(data):
    room = data.get("room")
    if room:
        join_room(room)
        emit("system_message", {"message": f"Bạn đã tham gia {room}"}, room=room)





# --------------------------------
# 2. WebSocket: Gửi tin nhắn nhóm
# --------------------------------
@socketio.on("send_message")
def handle_group_message(data):
    from app.models import GroupMember, MessageStatus

    room = data.get("room")
    content = data.get("message", "").strip()
    username = data.get("username")
    avatar_url = data.get("avatar_url")

    if not room or not username:
        return

    group_id = int(room.replace("group_", ""))
    sender_id = session.get("user_id")

    if not sender_id:
        return

    # 1. Lưu tin nhắn
    new_msg = GroupMessage(
        group_id=group_id,
        sender_id=sender_id,
        content=content if content else None,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_msg)
    db.session.flush()  # để lấy new_msg.id mà chưa commit vội

    # 2. Tạo MessageStatus cho các thành viên trong nhóm (trừ người gửi)
    members = GroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        if member.user_id == sender_id:
            continue
        status = MessageStatus(
            group_message_id=new_msg.id,
            user_id=member.user_id,
            is_read=False,
            timestamp=datetime.utcnow()
        )
        db.session.add(status)

    db.session.commit()

    # 3. Gửi emit về frontend
    emit_data = {
        "group_id": group_id,
        "username": username,
        "avatar_url": avatar_url,
        "message": content,
        "timestamp": new_msg.timestamp.strftime("%H:%M"),
        "attachments": []
    }

    emit("receive_group_message", emit_data, room=room)




# -------------------------------
# 3. HTTP: Gửi tin nhắn kèm file
# -------------------------------
group_message_bp = Blueprint("group_message", __name__)

@group_message_bp.route("/send-group-message", methods=["POST"])
def send_group_message():
    from app.models import GroupMember, MessageStatus  # đảm bảo đã import
    if "user_id" not in session:
        return {"error": "Unauthorized"}, 403

    user_id = session["user_id"]
    username = session["username"]
    avatar_url = session.get("avatar_url", "")

    group_id = request.form.get("group_id")
    content = request.form.get("message", "").strip()
    files = request.files.getlist("files")

    if not group_id:
        return {"error": "Thiếu group_id"}, 400

    group_id = int(group_id)

    # 1. Tạo GroupMessage
    new_msg = GroupMessage(
        group_id=group_id,
        sender_id=user_id,
        content=content if content else None,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_msg)
    db.session.flush()  # lấy new_msg.id

    attachments = []

    # 2. Lưu các file đính kèm
    for file in files:
        filename = secure_filename(file.filename)
        if filename == "":
            continue

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        ext = filename.split(".")[-1].lower()
        file_type = "file"
        if ext in ["jpg", "jpeg", "png", "gif"]:
            file_type = "image"
        elif ext in ["mp4", "webm", "mov"]:
            file_type = "video"

        attachment = Attachment(
            message_id=None,
            group_message_id=new_msg.id,
            file_url=save_path.replace("static/", "/static/"),
            file_type=file_type,
            filename=filename
        )
        db.session.add(attachment)

        attachments.append({
            "file_url": attachment.file_url,
            "file_type": file_type,
            "filename": filename
        })

    # 3. Lưu MessageStatus cho các thành viên trong nhóm (trừ người gửi)
    members = GroupMember.query.filter_by(group_id=group_id).all()
    for member in members:
        if member.user_id == user_id:
            continue
        status = MessageStatus(
            group_message_id=new_msg.id,
            user_id=member.user_id,
            is_read=False,
            timestamp=datetime.utcnow()
        )
        db.session.add(status)

    db.session.commit()

    # 4. Emit đến các thành viên
    emit_data = {
        "group_id": group_id,
        "username": username,
        "avatar_url": avatar_url,
        "message": content,
        "timestamp": new_msg.timestamp.strftime("%H:%M"),
        "attachments": attachments
    }

    socketio.emit("receive_group_message", emit_data, room=f"group_{group_id}")
    return {"success": True}



# -----------------------------------------
# 4. WebSocket: Load lịch sử tin nhắn nhóm
# -----------------------------------------
@socketio.on("load_group_history")
def handle_load_group_history(data):
    group_id = data.get("group_id")
    user_id = session.get("user_id")
    if not group_id or not user_id:
        return

    group = db.session.get(Group, group_id)
    if not group:
        return

    messages = GroupMessage.query.filter_by(group_id=group_id).order_by(GroupMessage.timestamp).all()
    result = []

    for msg in messages:
        sender = User.query.get(msg.sender_id)
        attachments = [
            {
                "file_url": att.url,
                "file_type": att.file_type,
                "filename": att.filename
            } for att in msg.attachments
        ]

        result.append({
            "username": sender.username if sender else "Người dùng",
            "avatar_url": sender.avatar_url if sender else None,
            "message": msg.content,
            "timestamp": msg.timestamp.strftime("%H:%M %d/%m"),
            "attachments": attachments
        })

    emit("load_group_history", {"messages": result})





from app.models import MessageStatus, GroupMember
@socketio.on("mark_group_as_read")
def handle_mark_group_as_read(data):
    if "user_id" not in session:
        return

    user_id = session["user_id"]
    group_id = data.get("group_id")

    if not group_id:
        return

    # Tìm tất cả các MessageStatus chưa đọc thuộc group này
    unread_statuses = (
        db.session.query(MessageStatus)
        .join(GroupMessage, MessageStatus.group_message_id == GroupMessage.id)
        .filter(
            MessageStatus.user_id == user_id,
            MessageStatus.is_read == False,
            GroupMessage.group_id == group_id
        )
        .all()
    )

    # Đánh dấu đã đọc
    for status in unread_statuses:
        status.is_read = True

    db.session.commit()


@socketio.on("typing_group")
def handle_typing_group(data):
    group_id = data.get("group_id")
    username = session.get("username")
    if not group_id or not username:
        return
    emit("show_typing_group", {"group_id": group_id, "username": username}, room=f"group_{group_id}", include_self=False)

@socketio.on("stop_typing_group")
def handle_stop_typing_group(data):
    group_id = data.get("group_id")
    if not group_id:
        return
    emit("hide_typing_group", {"group_id": group_id}, room=f"group_{group_id}")
