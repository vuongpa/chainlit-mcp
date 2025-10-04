import chainlit as cl

from chat_app import ChatApp

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
        return cl.User(
            identifier=username, metadata={"role": "admin", "provider": "credentials"}
        )
