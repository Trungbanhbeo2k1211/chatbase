from flask_socketio import emit, join_room, leave_room
from app.extensions import socketio, db
from flask import session
from app.models import Message, User, Attachment, MessageStatus
from datetime import datetime
from datetime import datetime
import pytz
from sqlalchemy import or_, and_
from flask_socketio import join_room, emit
from flask import session
from app.extensions import socketio


online_users = set()

@socketio.on("send_message_private")
def handle_private_message(data):

    sender_id = session.get("user_id")
    receiver_id = data.get("to_id")
    content = data.get("message", "").strip()

    if not sender_id or not receiver_id or not content:
        return

    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

    # 1. Lưu tin nhắn vào database
    msg = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        timestamp=datetime.utcnow()
    )
    db.session.add(msg)
    db.session.commit()

    status = MessageStatus(
        message_id=msg.id,
        user_id=receiver_id,  # người nhận là người cần thấy chưa đọc
        is_read=False
    )
    db.session.add(status)
    db.session.commit()

    local_time = msg.timestamp.replace(tzinfo=pytz.utc).astimezone(vietnam_tz)
    time_str = local_time.strftime("%H:%M %d/%m/%Y")

    sender = User.query.get(sender_id)

    # 2. Tạo payload (chưa có file đính kèm)
    payload = {
        "avatar_url": sender.avatar_url or "default-avatar.png",
        "from_id": sender_id,
        "to_id": receiver_id,
        "username": sender.username,
        "message": content,
        "attachments": [],  # Khác biệt: thêm attachments rỗng
        "timestamp": time_str
    }

    # 3. Gửi về người gửi và người nhận
    emit("receive_message", payload, room=f"user_{sender_id}")
    emit("receive_message", payload, room=f"user_{receiver_id}")




# Tự động join socket room theo user_id
@socketio.on("connect")
def handle_connect():
    user_id = session.get("user_id")
    if user_id:
        join_room(f"user_{user_id}")
        online_users.add(user_id)
        emit("user_online", {"user_id": user_id}, broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    user_id = session.get("user_id")
    if user_id and user_id in online_users:
        online_users.remove(user_id)
        emit("user_offline", {"user_id": user_id}, broadcast=True)


# Hàm API cho client yêu cầu danh sách đang online
@socketio.on("get_online_users")
def get_online():
    emit("online_users", list(online_users))




# Truy vấn lịch sử tin nhắn (new event)
@socketio.on("load_private_history")
def load_private_history(data):
    from app.models import Message, User, Attachment
    from sqlalchemy import and_, or_
    import pytz

    current_user = session.get("user_id")
    target_id = data.get("target_id")
    if not current_user or not target_id:
        return

    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

    # Lấy tất cả tin nhắn giữa hai người
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user, Message.receiver_id == target_id),
            and_(Message.sender_id == target_id, Message.receiver_id == current_user),
        )
    ).order_by(Message.timestamp.asc()).all()

    history = []
    for m in messages:
        sender = User.query.get(m.sender_id)
        attachments = Attachment.query.filter_by(message_id=m.id).all()
        local_time = m.timestamp.replace(tzinfo=pytz.utc).astimezone(vietnam_tz)

        # Chuẩn bị danh sách attachment
        att_data = []
        for att in attachments:
            att_data.append({
                "type": att.file_type,
                "url": f"/static/{att.url}",
                "name": att.filename
            })

        history.append({
            "avatar_url": sender.avatar_url or "default-avatar.png",
            "from_id": m.sender_id,
            "to_id": m.receiver_id,
            "username": sender.username,
            "message": m.content,
            "attachments": att_data,
            "timestamp": local_time.strftime("%H:%M %d/%m/%Y")
        })

    # Kiểm tra xem tin cuối cùng mình gửi đã được đọc chưa
    last_msg = Message.query.filter_by(
        sender_id=current_user,
        receiver_id=target_id
    ).order_by(Message.timestamp.desc()).first()

    last_seen = last_msg.is_read if last_msg else False

    emit("load_history", {
        "messages": history,
        "last_seen": last_seen
    })




from flask_socketio import SocketIO, emit
from app.models import Message, MessageStatus
from app.extensions import db
from flask import session

@socketio.on("mark_as_read")
def handle_mark_as_read(data):
    user_id = session.get("user_id")
    if not user_id:
        return

    if data.get("type") == "user":
        partner_id = data.get("user_id")
        # Lấy tất cả message giữa partner -> current_user
        message_ids = db.session.query(Message.id).filter(
            Message.sender_id == partner_id,
            Message.receiver_id == user_id
        ).subquery()

        # Cập nhật trạng thái chưa đọc → đã đọc
        db.session.query(MessageStatus).filter(
            MessageStatus.message_id.in_(message_ids),
            MessageStatus.user_id == user_id,
            MessageStatus.is_read == False
        ).update({"is_read": True}, synchronize_session=False)

        db.session.commit()





@socketio.on("typing")
def handle_typing(data):
    sender_id = session.get("user_id")
    to_id = data.get("to_id")

    if sender_id and to_id:
        emit("show_typing", {"from_id": sender_id}, room=f"user_{to_id}")

@socketio.on("stop_typing")
def handle_stop_typing(data):
    sender_id = session.get("user_id")
    to_id = data.get("to_id")

    if sender_id and to_id:
        emit("hide_typing", {"from_id": sender_id}, room=f"user_{to_id}")




@socketio.on("start_call")
def handle_start_call(data):
    to_id = data.get("to_id")
    from_id = session.get("user_id")
    user = db.session.get(User, from_id)
    if to_id and user:
        emit("incoming_call", {
            "from_id": from_id,
            "username": user.username,
            "avatar_url": user.avatar_url
        }, room=f"user_{to_id}")

@socketio.on("accept_call")
def handle_accept_call(data):
    from_id = data.get("from_id")
    emit("call_accepted", {}, room=f"user_{from_id}")

@socketio.on("reject_call")
def handle_reject_call(data):
    from_id = data.get("from_id")
    emit("call_rejected", {}, room=f"user_{from_id}")

@socketio.on("webrtc_signal")
def handle_webrtc_signal(data):
    to_id = data.get("to_id")
    signal = data.get("signal")
    emit("webrtc_signal", {"signal": signal}, room=f"user_{to_id}")

@socketio.on("end_call")
def handle_end_call(data):
    to_id = data.get("to_id")
    emit("call_ended", {}, room=f"user_{to_id}")

