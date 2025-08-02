import chainlit as cl

from chat_app import ChatApp

ChatApp.starters = [
    cl.Starter(
        label="What is ALT test?",
        message="What is ALT test?",
        icon="/public/chat-bot-svgrepo-com.svg",
    )
]

@cl.password_auth_callback
def auth_callback(username: str, password: str):
        return cl.User(
            identifier=username, metadata={"role": "admin", "provider": "credentials"}
        )
