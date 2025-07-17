import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:123456@localhost:5432/chatdb"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Thêm cấu hình cho session
    SESSION_PERMANENT = False  # Mặc định session sẽ không permanent
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)  # Nếu chọn "Ghi nhớ", sống 30 ngày
