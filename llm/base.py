# llm/base.py
from abc import ABC, abstractmethod
from typing import Generator


class BaseLLM(ABC):
    @abstractmethod
    def chat(
        self,
        prompt: str,
        temperature: float = 0.7,
    ) -> str:
        pass

    @abstractmethod
    def stream_chat(
        self, prompt: str, temperature: float = 0.7
    ) -> Generator[str, None, None]:
        pass
