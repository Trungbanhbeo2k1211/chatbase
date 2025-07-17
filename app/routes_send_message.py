from flask import Blueprint, request, session, jsonify
from app.models import Message, Attachment, User, MessageStatus
from app.extensions import db, socketio
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import regex

bp_message = Blueprint("message", __name__)
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_emoji_only(text):
    return bool(regex.fullmatch(r"[\p{Emoji}\s]+", text))

@bp_message.route("/send-message", methods=["POST"])
def send_message():
    sender_id = session.get("user_id")
    to_id = request.form.get("to_id")
    msg_type = request.form.get("type")  # "user" hoặc "group"
    message = request.form.get("message", "").strip()

    if not sender_id or not to_id:
        return "Unauthorized", 401

    # 1. Xác định loại tin nhắn
    if message:
        if is_emoji_only(message):
            message_type = "emoji"
        else:
            message_type = "text"
    else:
        message_type = "file"  # fallback nếu chỉ gửi file

    # 2. Lưu tin nhắn
    msg = Message(
        sender_id=sender_id,
        receiver_id=to_id,
        content=message,
        msg_type=message_type
    )
    db.session.add(msg)
    db.session.commit()

    if msg_type == "user":
        status = MessageStatus(
            message_id=msg.id,
            user_id=int(to_id),  # chỉ người nhận
            is_read=False
        )
        db.session.add(status)
        db.session.commit()
    print("DEBUG msg_type:", msg_type)
    print("DEBUG to_id:", to_id)

    # 3. Xử lý file đính kèm
    attachments = []
    files = request.files.getlist("files")

    for f in files:
        if not f or not f.filename:
            continue
        filename = secure_filename(f.filename)
        ext = filename.rsplit(".", 1)[-1].lower()

        if ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
            file_type = "image"
        elif ext in ["mp4", "mov", "avi", "webm", "mkv"]:
            file_type = "video"
        else:
            file_type = "file"

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(save_path)

        attachment = Attachment(
            filename=filename,
            file_type=file_type,
            url=f"uploads/{filename}",
            message_id=msg.id
        )
        db.session.add(attachment)

        attachments.append({
            "file_type": file_type,
            "file_url": f"/static/uploads/{filename}",
            "filename": filename
        })

    db.session.commit()

    # 4. Emit qua Socket.IO
    sender = User.query.get(sender_id)

    payload = {
        "username": sender.username,
        "avatar_url": sender.avatar_url,
        "message": message,
        "message_type": message_type,  # 👈 GỬI KÈM ĐỂ HIỂN THỊ
        "attachments": attachments,
        "timestamp": datetime.utcnow().strftime("%H:%M"),
        "from_id": sender_id,
        "to_id": int(to_id),
    }

    if msg_type == "group":
        socketio.emit("receive_message", payload, room=f"group_{to_id}")
    else:
        for uid in [sender_id, int(to_id)]:
            socketio.emit("receive_message", payload, room=f"user_{uid}")

    return jsonify(success=True)

