from flask import Blueprint, render_template, session, redirect, url_for
from sqlalchemy import func
from app.models import User, Friend, Group, GroupMember, Message, MessageStatus, GroupMessage
from app.extensions import db
from sqlalchemy.orm import aliased

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat")
def chat_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    current_user = User.query.get(user_id)

    # 1. Danh sách bạn bè đã chấp nhận
    friends = (
        db.session.query(User)
        .join(Friend, ((Friend.user_id == user_id) & (Friend.friend_id == User.id)) | 
                        ((Friend.friend_id == user_id) & (Friend.user_id == User.id)))
        .filter(Friend.status == "accepted", User.id != user_id)
        .all()
    )

    # 2. Lấy số lượng tin nhắn chưa đọc từ từng người bạn
    unread_counts = (
        db.session.query(Message.sender_id, func.count().label("unread"))
        .join(MessageStatus, Message.id == MessageStatus.message_id)
        .filter(
            MessageStatus.user_id == user_id,
            MessageStatus.is_read == False
        )
        .group_by(Message.sender_id)
        .all()
    )

    # 3. Tạo map {sender_id: số lượng chưa đọc}
    unread_map = {sid: count for sid, count in unread_counts}

    # 4. Gắn số chưa đọc vào từng bạn
    friend_list = []
    for friend in friends:
        friend_list.append({
            "id": friend.id,
            "username": friend.username,
            "avatar_url": friend.avatar_url,
            "unread_count": unread_map.get(friend.id, 0)
        })

    # 5. Danh sách lời mời kết bạn
    friend_requests = (
        db.session.query(User)
        .join(Friend, Friend.user_id == User.id)
        .filter(Friend.friend_id == user_id, Friend.status == "pending")
        .all()
    )

    # 6. Danh sách nhóm
    groups = (
        db.session.query(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .filter(GroupMember.user_id == user_id)
        .all()
    )

    # 6.1 Đếm số lượng tin nhắn chưa đọc cho mỗi nhóm
    unread_group_counts = (
        db.session.query(GroupMessage.group_id, func.count().label("unread"))
        .select_from(MessageStatus)
        .join(GroupMessage, MessageStatus.group_message_id == GroupMessage.id)
        .filter(
            MessageStatus.user_id == user_id,
            MessageStatus.is_read == False,
            MessageStatus.group_message_id != None
        )
        .group_by(GroupMessage.group_id)
        .all()
    )


    # Map group_id -> số lượng chưa đọc
    unread_group_map = {gid: count for gid, count in unread_group_counts}

    
    # 6.2 Gắn thêm unread_count vào mỗi group
    group_list = []
    for group in groups:
        group_list.append({
            "id": group.id,
            "name": group.name,
            "unread_count": unread_group_map.get(group.id, 0)
        })


    # 7. Online (tạm thời để rỗng)
    online_ids = []
    group_ids = [g.id for g in groups]

    return render_template(
        "chat.html",
        current_user=current_user,
        friends=friend_list,  # 👈 đã gắn unread_count
        friend_requests=friend_requests,
        groups=group_list,                                                              # Sửa
        online_ids=online_ids,
        group_ids=group_ids
    )
