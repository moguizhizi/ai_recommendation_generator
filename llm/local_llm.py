# llm/local_llm.py
from .base import BaseLLM

class LocalLLM(BaseLLM):
    def __init__(self, model_path: str):
        self.model_path = model_path
        # 这里加载你的本地模型

    def chat(self, prompt: str) -> str:
        return f"[Local LLM 回复] {prompt}"