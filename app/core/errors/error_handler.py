# app/core/errors/error_handler.py


from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import BizError
from .error_messages import ERROR_MESSAGES
from .error_codes import ErrorCode
from utils.logger import get_logger

logger = get_logger(__name__)


async def biz_error_handler(request: Request, exc: BizError):

    logger.exception(str(exc))

    return JSONResponse(
        status_code=400,
        content={"message": exc.message},
    )


async def generic_error_handler(request: Request, exc: Exception):

    logger.exception("[INTERNAL_ERROR] %s", str(exc))

    return JSONResponse(
        status_code=500,
        content={"message": ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR]},
    )
