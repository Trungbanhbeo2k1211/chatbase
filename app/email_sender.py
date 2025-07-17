import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_verification_email(to_email, verify_token):
    subject = "🎯 Xác nhận đăng ký tài khoản ChatBase"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; border-radius: 10px; padding: 30px; border: 1px solid #e0e0e0;">
            <div style="text-align: center; margin-bottom: 25px;">
                <h1 style="color: #6c5ce7; margin-bottom: 10px;">ChatBase</h1>
                <h2 style="color: #2d3436; margin-top: 0;">Xác nhận đăng ký</h2>
            </div>
            
            <div style="background-color: white; border-radius: 8px; padding: 20px; margin-bottom: 25px; border: 1px solid #e0e0e0;">
                <p style="margin-bottom: 15px;">Xin chào,</p>
                <p style="margin-bottom: 15px;">Cảm ơn bạn đã đăng ký tài khoản tại ChatBase.</p>
                
                <div style="background-color: #f5f6fa; padding: 15px; border-radius: 6px; text-align: center; margin: 20px 0; border-left: 4px solid #6c5ce7;">
                    <p style="margin: 0; font-weight: bold; font-size: 18px;">Mã xác nhận của bạn:</p>
                    <p style="margin: 10px 0 0; font-size: 24px; font-weight: bold; color: #6c5ce7; letter-spacing: 2px;">{verify_token}</p>
                </div>
                
                <p style="margin-bottom: 0;">Vui lòng sử dụng mã này để hoàn tất quá trình đăng ký.</p>
            </div>
            
            <div style="text-align: center; color: #7f8c8d; font-size: 14px;">
                <p style="margin: 5px 0;">Nếu không phải bạn đăng ký, vui lòng bỏ qua email này.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Tạo message
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = "Chatbase <apchatonline@gmail.com>"
    message["To"] = to_email
    
    # Thêm cả plain text và HTML version
    text_part = MIMEText(f"""Xin chào,

Cảm ơn bạn đã đăng ký tài khoản Movie Room. 
Mã xác nhận của bạn là: {verify_token}

Vui lòng sử dụng mã này để hoàn tất quá trình đăng ký.
(Nếu không phải bạn đăng ký, vui lòng bỏ qua email này.)
""", "plain", "utf-8")
    
    html_part = MIMEText(html, "html", "utf-8")
    message.attach(text_part)
    message.attach(html_part)
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("apchatonline@gmail.com", "ftuq alfa sgvc xbgi")
            server.send_message(message)
            print("✅ Đã gửi email xác nhận.")
    except Exception as e:
        print("❌ Gửi email thất bại:", e)