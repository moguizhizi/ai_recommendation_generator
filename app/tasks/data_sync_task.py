"""
app/tasks/data_sync_task.py

定时将 CSV 转换为 Parquet
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

from app.data.datasets.cognitive_l1_dataset import load_and_preprocess_dataset
from app.services.task_processor import build_task_repository
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
                logger.debug("Start converting CSV -> Parquet")

                csv_to_parquet(
                    csv_path=str(csv_path),
                    parquet_path=str(parquet_path),
                    config=config,
                )

                logger.debug("CSV converted to Parquet successfully")

                load_and_preprocess_dataset(
                    config=config, parquet_name=Path(parquet_path).stem
                )

        except Exception:
            logger.exception("CSV -> Parquet conversion failed")

        await asyncio.sleep(interval_seconds)


async def wait_for_parquet(config, check_interval: int = 5):
    """
    等待 parquet 文件准备好
    """

    task_config = config.get("csv_to_parquet", {})
    parquet_files = [item["parquet"] for item in task_config.get("raw_files", [])]

    while True:

        missing_files = [p for p in parquet_files if not Path(p).exists()]

        if not missing_files:
            return

        logger.info(
            "Waiting for parquet files: %s",
            ", ".join(missing_files),
        )

        await asyncio.sleep(check_interval)


async def task_repository_job(config, interval_seconds):

    while True:

        # 等待 parquet 文件生成
        await wait_for_parquet(config)

        # 构建 task repository
        build_task_repository(config)

        logger.info("Task repository rebuilt")

        await asyncio.sleep(interval_seconds)
