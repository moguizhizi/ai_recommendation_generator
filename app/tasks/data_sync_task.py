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

from app.core import sync_state

logger = get_logger(__name__)


async def csv_to_parquet_job(
    csv_path: str,
    parquet_path: str,
    interval_seconds: int,
    config: dict,
):

    first_run = True

    while True:

        try:

            await asyncio.to_thread(
                csv_to_parquet,
                csv_path=csv_path,
                parquet_path=parquet_path,
                config=config,
            )

            await asyncio.to_thread(
                load_and_preprocess_dataset,
                config=config,
                parquet_name=Path(parquet_path).stem,
            )

            if first_run:

                sync_state.csv_ready_counter += 1

                logger.info(
                    f"CSV initial sync finished "
                    f"({sync_state.csv_ready_counter}/"
                    f"{sync_state.total_csv_jobs})"
                )

                if sync_state.csv_ready_counter == sync_state.total_csv_jobs:

                    logger.info("All CSV ready")

                    sync_state.csv_ready_event.set()

                first_run = False

        except Exception:
            logger.exception("CSV job failed")

        await asyncio.sleep(interval_seconds)


async def task_repository_job(config, interval_seconds):

    logger.info("Waiting for CSV sync...")

    await sync_state.csv_ready_event.wait()

    logger.info("CSV ready. Start building repository")

    while True:

        try:
            await asyncio.to_thread(build_task_repository, config)
        except Exception:
            logger.exception("Repository build failed")

        await asyncio.sleep(interval_seconds)
