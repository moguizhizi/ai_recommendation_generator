# app/services/chat_service.py
from llm.factory import create_llm
from configs import load_config

config = load_config()
llm = create_llm(config)

def chat(prompt):
    return llm.chat(prompt)