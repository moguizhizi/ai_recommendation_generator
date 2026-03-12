import time
import requests
import json
from typing import Optional, Generator

from utils.logging import get_logger
from llm.base import BaseLLM

logger = get_logger(__name__)


class LLMError(Exception):
    """
    自定义 LLM 异常

    Attributes:
        message: 错误信息
        code: 错误码（如 TIMEOUT / HTTP_ERROR / INVALID_RESPONSE）
        status_code: HTTP 状态码（可选）
        retryable: 是否可重试
        original_error: 原始异常对象
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        retryable: bool = False,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.original_error = original_error

    def __str__(self):
        base = f"[{self.code}] {self.message}" if self.code else self.message
        if self.status_code:
            base += f" (status={self.status_code})"
        return base


class ApiLLM(BaseLLM):
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self.session = requests.Session()

    def _build_headers(self):
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(self, payload: dict) -> dict:
        url = f"{self.base_url}/v1/chat/completions"

        last_error: LLMError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                start_time = time.time()

                resp = self.session.post(
                    url,
                    headers=self._build_headers(),
                    json=payload,
                    timeout=self.timeout,
                )

                duration = time.time() - start_time

                # HTTP 错误单独处理
                if resp.status_code >= 400:
                    raise LLMError(
                        message=f"HTTP error from LLM",
                        code="HTTP_ERROR",
                        status_code=resp.status_code,
                        retryable=resp.status_code >= 500,
                    )

                try:
                    data = resp.json()
                except Exception as e:
                    raise LLMError(
                        message="Invalid JSON response",
                        code="INVALID_JSON",
                        retryable=False,
                        original_error=e,
                    )

                logger.debug(
                    f"LLM call success | model={self.model} "
                    f"| attempt={attempt} | time={duration:.3f}s"
                )

                return data

            except requests.Timeout as e:
                last_error = LLMError(
                    message="LLM request timeout",
                    code="TIMEOUT",
                    retryable=True,
                    original_error=e,
                )

            except requests.RequestException as e:
                last_error = LLMError(
                    message="Network error when calling LLM",
                    code="NETWORK_ERROR",
                    retryable=True,
                    original_error=e,
                )

            except LLMError as e:
                last_error = e

            # 如果不可重试，直接抛
            if last_error and not last_error.retryable:
                logger.error(f"Non-retryable error: {last_error}")
                raise last_error

            # 可重试
            if attempt < self.max_retries:
                sleep_time = self.backoff_factor**attempt
                logger.warning(
                    f"Retryable error (attempt {attempt}): {last_error} "
                    f"| retrying in {sleep_time:.2f}s"
                )
                time.sleep(sleep_time)
            else:
                break

        logger.error(f"LLM failed after {self.max_retries} attempts")
        raise last_error or LLMError("Unknown LLM failure")

    def chat(self, prompt: str, temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": False,
        }

        data = self._post(payload)

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(
                message="Invalid LLM response format",
                code="INVALID_RESPONSE",
                retryable=False,
                original_error=e,
            )

        usage = data.get("usage")
        if usage:
            logger.debug(
                f"Token usage | prompt={usage.get('prompt_tokens')} "
                f"| completion={usage.get('completion_tokens')} "
                f"| total={usage.get('total_tokens')}"
            )

        return content

    def stream_chat(
        self, prompt: str, temperature: float = 0.7
    ) -> Generator[str, None, None]:

        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": True,
        }

        try:
            with self.session.post(
                url,
                headers=self._build_headers(),
                json=payload,
                timeout=self.timeout,
                stream=True,
            ) as resp:

                if resp.status_code >= 400:
                    raise LLMError(
                        message="Stream HTTP error",
                        code="HTTP_ERROR",
                        status_code=resp.status_code,
                        retryable=resp.status_code >= 500,
                    )

                for line in resp.iter_lines():
                    if not line:
                        continue

                    line = line.decode("utf-8")

                    if not line.startswith("data: "):
                        continue

                    chunk = line[6:]

                    if chunk == "[DONE]":
                        break

                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0].get("delta", {}).get("content")
                        if delta:
                            yield delta
                    except Exception:
                        continue

        except Exception as e:
            logger.exception("Stream request failed")
            raise LLMError(
                message="Stream request failed",
                code="STREAM_ERROR",
                retryable=False,
                original_error=e,
            )
