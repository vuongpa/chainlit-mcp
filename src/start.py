import chainlit as cl

from chat_app import ChatApp

ChatApp.starters = [
cl.Starter(
    label="What is the ALT Test?",
    message="What is the ALT test and what does it reveal about liver health?",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="AST:ALT Ratio",
    message="How is the AST:ALT ratio used to distinguish liver disease types?",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="Liver Enzymes",
    message="Which liver enzymes are most helpful for diagnosing different liver conditions?",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="Cirrhosis Risk",
    message="Can enzyme levels or ratios help assess the risk or presence of cirrhosis?",
    icon="/public/chat-bot-svgrepo-com.svg",
),

cl.Starter(
    label="Alcohol vs NAFLD",
    message="How can liver tests help differentiate alcoholic liver disease from NAFLD?",
    icon="/public/chat-bot-svgrepo-com.svg",
)]

@cl.password_auth_callback
def auth_callback(username: str, password: str):
        return cl.User(
            identifier=username, metadata={"role": "admin", "provider": "credentials"}
        )
