# services/sync_tasks.py

import asyncio
from app.core import sync_state
from app.tasks.data_sync_task import (
    build_train_eval_dataset_job,
    csv_to_parquet_job,
    raw_data_copy_job,
    task_repository_job,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def start_sync_tasks(config):

    task_config = config.get("csv_to_parquet", {})
    interval = task_config.get("interval_seconds", 300)
    raw_files = task_config.get("raw_files", [])

    sync_state.total_csv_jobs = len(raw_files)

    logger.info(f"Total CSV sync jobs: {sync_state.total_csv_jobs}")

    # 1️⃣ raw 数据复制
    asyncio.create_task(raw_data_copy_job(config))

    # 2️⃣ csv pipeline
    for item in raw_files:

        asyncio.create_task(
            csv_to_parquet_job(
                csv_path=item["csv"],
                parquet_path=item["parquet"],
                interval_seconds=interval,
                config=config,
            )
        )

    # 3️⃣ repository
    asyncio.create_task(
        task_repository_job(
            config=config,
            interval_seconds=interval,
        )
    )

    # train_eval_dataset
    asyncio.create_task(
        build_train_eval_dataset_job(
            config=config,
            interval_seconds=interval,
        )
    )
