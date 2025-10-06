import chainlit as cl
from chat_app import ChatApp
from lib.auth_manager import AuthManager

auth_manager = AuthManager()

ChatApp.starters = [
cl.Starter(
    label="Tra cứu trạng thái đơn hàng",
    message="Đơn hàng Oreka của tôi đã thanh toán rồi, bao giờ giao vậy?",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="Kích hoạt tài khoản doanh nghiệp",
    message="Tôi cần hướng dẫn kích hoạt tài khoản Oreka Business cho công ty.",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="Chính sách đổi trả",
    message="Oreka có hỗ trợ đổi trả thiết bị lỗi trong bao nhiêu ngày?",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="Hóa đơn và chứng từ",
    message="Tôi cần xuất hóa đơn VAT cho đơn hàng Oreka, làm sao?",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="Kênh hỗ trợ khẩn",
    message="Có hotline nào để liên hệ khi nền tảng Oreka bị gián đoạn không?",
    icon="/public/chat-bot-svgrepo-com.svg",
)]

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    try:
        user_profile = auth_manager.authenticate_user(username, password)
        if user_profile:
            return cl.User(
                identifier=user_profile.username,
                metadata={
                    "user_id": str(user_profile.id),
                    "store_id": str(user_profile.storeId) if user_profile.storeId else None,
                    "email": user_profile.email,
                    "role": user_profile.role,
                    "full_name": user_profile.full_name,
                    "nickname": user_profile.nickname,
                    "provider": user_profile.provider.value,  # Convert enum to string
                    "isActive": user_profile.isActive,
                    "verified": user_profile.verified,
                    "language": user_profile.language
                }
            )
        else:
            return None
            
    except Exception as e:
        print(f"Authentication error: {e}")
        return None
