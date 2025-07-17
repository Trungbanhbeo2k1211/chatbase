# from flask import Flask
# from config import Config
# from app.extensions import db, socketio
# from app.auth import auth_bp
# from app.routes_friend import bp_friend
# from app.routes_profile import bp_profile

# def create_app():
#     app = Flask(__name__, static_folder="static")
#     app.config.from_object(Config)

#     db.init_app(app)
#     socketio.init_app(app)

#     app.register_blueprint(auth_bp)
#     app.register_blueprint(bp_friend)
#     app.register_blueprint(bp_profile)

#     return app
