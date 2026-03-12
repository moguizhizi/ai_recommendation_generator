"""
app/tasks/data_sync_task.py

定时将 CSV 转换为 Parquet
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

from utils.csv_utils import csv_to_parquet
from utils.logger import get_logger

logger = get_logger(__name__)


async def csv_to_parquet_job(
    csv_path: str,
    parquet_path: str,
    interval_seconds: int = 300,
    config: Dict[str, Any] = None,
):
    """
    定时执行 CSV -> Parquet 转换

    Parameters
    ----------
    csv_path : str
    parquet_path : str
    interval_seconds : int
        执行周期
    """

    csv_path = Path(csv_path)

    while True:
        try:
            if csv_path.exists():
                logger.info("Start converting CSV -> Parquet")

                csv_to_parquet(
                    csv_path=str(csv_path),
                    parquet_path=str(parquet_path),
                    config=config,
                )

                logger.info("CSV converted to Parquet successfully")

        except Exception:
            logger.exception("CSV -> Parquet conversion failed")

        await asyncio.sleep(interval_seconds)
