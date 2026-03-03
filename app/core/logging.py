import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv(find_dotenv())


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

LOG_LEVEL = logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO


def setup_logging():
    log_format = (
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(filename)s:%(lineno)d | %(message)s"
    )

    formatter = logging.Formatter(log_format)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """
    获取模块级 logger
    """
    return logging.getLogger(name)