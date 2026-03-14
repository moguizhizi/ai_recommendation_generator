# app/core/errors/exceptions.py

from typing import Any

from .error_codes import ErrorCode
from .error_messages import ERROR_MESSAGES


class BizError(Exception):
    """
    业务异常
    """

    def __init__(self, code: ErrorCode, **kwargs: Any):

        self.code = code

        self.message = ERROR_MESSAGES.get(code, "系统错误")

        self.detail = kwargs

        detail_str = " ".join(f"{k}={v}" for k, v in kwargs.items())

        super().__init__(f"[{code}] {self.message} | {detail_str}")
