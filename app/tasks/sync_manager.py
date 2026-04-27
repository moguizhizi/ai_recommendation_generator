# services/sync_tasks.py

import asyncio

from app.tasks.data_sync_task import run_sync_pipeline
from utils.logger import get_logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = get_logger(__name__)

_sync_pipeline_lock = asyncio.Lock()


async def _run_sync_pipeline_locked(config):
    if _sync_pipeline_lock.locked():
        logger.warning("Sync pipeline is already running; skip this trigger")
        return

    async with _sync_pipeline_lock:
        await run_sync_pipeline(config)


def start_sync_tasks(config):

    schedule_config = config.get("sync_tasks", {}).get("schedule", {})
    hour = schedule_config.get("hour", 2)
    minute = schedule_config.get("minute", 0)
    timezone = schedule_config.get("timezone", "Asia/Shanghai")
    run_on_startup = schedule_config.get("run_on_startup", True)

    scheduler = AsyncIOScheduler(timezone=timezone)
    trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)

    scheduler.add_job(
        _run_sync_pipeline_locked,
        trigger=trigger,
        args=[config],
        id="sync_pipeline",
        name="sync_pipeline",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
    scheduler.start()

    logger.info(
        f"Sync pipeline scheduled with CronTrigger(hour={hour}, "
        f"minute={minute}, timezone={timezone})"
    )

    if run_on_startup:
        logger.info("Starting initial sync pipeline")
        asyncio.create_task(_run_sync_pipeline_locked(config))

    return scheduler
