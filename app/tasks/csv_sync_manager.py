import asyncio

from app.tasks.data_sync_task import csv_to_parquet_job
from utils.logger import get_logger

logger = get_logger(__name__)


def start_csv_sync_tasks(config):

    task_config = config.get("csv_to_parquet", {})

    interval = task_config.get("interval_seconds", 300)

    for item in task_config.get("files", []):

        asyncio.create_task(
            csv_to_parquet_job(
                csv_path=item["csv"],
                parquet_path=item["parquet"],
                interval_seconds=interval,
                config=config,
            )
        )

        logger.info(f"CSV sync task started: {item['csv']}")
