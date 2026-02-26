# llm/api_llm.py
from .base import BaseLLM

class ApiLLM(BaseLLM):
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, prompt: str) -> str:
        return f"[API LLM 回复] {prompt}"