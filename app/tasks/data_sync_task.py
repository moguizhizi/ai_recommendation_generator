"""
app/tasks/data_sync_task.py

定时将 CSV 转换为 Parquet
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

from app.data.datasets.cognitive_l1_dataset import load_and_preprocess_dataset
from app.services.task_processor import (
    build_task_repository_assets,
    build_train_eval_dataset,
)
from utils.csv_utils import csv_to_parquet
from utils.io_utils import copy_file
from utils.logger import get_logger

logger = get_logger(__name__)

async def raw_data_copy_job(config):

    raw_config = config.get("raw_data_sync", {})
    files = raw_config.get("files", [])

    try:

        for item in files:

            src = Path(item["source"])
            dst = Path(item["target"])

            if not src.exists():
                logger.warning(f"Raw source not found: {src}")
                continue

            copy_file(src, dst)

            logger.info(f"Raw data copied: {src} -> {dst}")

        logger.info("Raw data sync finished")
        return True

    except Exception:
        logger.exception("Raw data sync failed")
        return False


async def csv_to_parquet_once(
    csv_path: str,
    parquet_path: str,
    config: dict,
):

    try:

        logger.info(f"Starting CSV to Parquet sync: {csv_path} -> {parquet_path}")
        await asyncio.to_thread(
            csv_to_parquet,
            csv_path=csv_path,
            parquet_path=parquet_path,
            config=config,
        )
        logger.info(f"Finished CSV to Parquet sync: {csv_path} -> {parquet_path}")

        parquet_name = Path(parquet_path).stem
        logger.info(f"Starting dataset preprocess: {parquet_name}")
        await asyncio.to_thread(
            load_and_preprocess_dataset,
            config=config,
            parquet_name=parquet_name,
        )
        logger.info(f"Finished dataset preprocess: {parquet_name}")

        return True

    except Exception:
        logger.exception("CSV job failed")
        return False


async def task_repository_once(config):

    try:
        await asyncio.to_thread(build_task_repository_assets, config)
    except Exception:
        logger.exception("Repository build failed")


async def build_train_eval_dataset_once(config):

    try:
        await asyncio.to_thread(build_train_eval_dataset, config)
    except Exception:
        logger.exception("Train/eval dataset build failed")


async def run_sync_pipeline(config: Dict[str, Any]):

    task_config = config.get("csv_to_parquet", {})
    raw_files = task_config.get("raw_files", [])

    logger.info("Starting scheduled sync pipeline")

    raw_data_ready = await raw_data_copy_job(config)
    if not raw_data_ready:
        logger.warning("Skip scheduled sync pipeline because raw data sync failed")
        return

    csv_results = await asyncio.gather(
        *(
            csv_to_parquet_once(
                csv_path=item["csv"],
                parquet_path=item["parquet"],
                config=config,
            )
            for item in raw_files
        )
    )

    if not all(csv_results):
        logger.warning("Skip downstream builds because at least one CSV job failed")
        return

    await asyncio.gather(
        task_repository_once(config),
        build_train_eval_dataset_once(config),
    )

    logger.info("Scheduled sync pipeline finished")
