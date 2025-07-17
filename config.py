import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = "postgresql://trung:coD8KSdcUpFf9dQvHBGhqd52KZazoZRW@dpg-d1shkvbipnbc73e3uhsg-a.oregon-postgres.render.com/chatdb_s5yo"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Thêm cấu hình cho session
    SESSION_PERMANENT = False  # Mặc định session sẽ không permanent
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)  # Nếu chọn "Ghi nhớ", sống 30 ngày
