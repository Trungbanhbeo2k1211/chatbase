import os
import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, session, redirect
from config import Config
from app.extensions import db, socketio
from app.models import User, Friend
from app.auth import auth_bp
from app.routes_friend import bp_friend
from app.routes_profile import bp_profile
import app.socket_events
from app.routes_send_message import bp_message
from app.socket_events import online_users
import app.socket_events_group
from app.routes_group import group_message_bp
from app.group_routes import group_bp
from app.routes_chat import chat_bp

# Tạo Flask app
app = Flask(__name__, static_folder="static")
app.config.from_object(Config)

# Gắn app vào extensions
db.init_app(app)
socketio.init_app(app, manage_session=False)


# Register blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(bp_friend)
app.register_blueprint(bp_profile)
app.register_blueprint(bp_message)
app.register_blueprint(group_message_bp)
app.register_blueprint(group_bp, url_prefix="/group")
app.register_blueprint(chat_bp)

# Tạo bảng
with app.app_context():
    db.create_all()

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/chat")
def home():
    current_user_id = session.get("user_id")
    if not current_user_id:
        return redirect("/login")
    
    user = User.query.get(current_user_id)

    friends = db.session.query(User).join(
        Friend,
        ((Friend.user_id == current_user_id) & (Friend.friend_id == User.id)) |
        ((Friend.friend_id == current_user_id) & (Friend.user_id == User.id))
    ).filter(Friend.status == "accepted", User.id != current_user_id).all()

    friend_requests = db.session.query(User).join(
        Friend,
        Friend.user_id == User.id
    ).filter(Friend.friend_id == current_user_id, Friend.status == "pending").all()

    groups = []

    return render_template("chat.html",
                           current_user=user,
                           friends=friends,
                           friend_requests=friend_requests,
                           groups=groups,
                           online_ids=list(online_users))

if __name__ == "__main__":
    socketio.run(app, debug=True)
