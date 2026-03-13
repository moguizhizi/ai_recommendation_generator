# app/services/task_processor.py

from typing import Dict, List, Any
from collections import defaultdict
from pathlib import Path

from app.core.cognitive_l1.constants import CognitiveL1DatasetName, TaskColumnName
from app.core.constants import Level1BrainDomain
from app.schemas.common import Task
from utils.dataframe_utils import ColumnAccessor, safe_get
from utils.logger import get_logger
import pandas as pd
import json


logger = get_logger(__name__)


def build_level2_to_level1_map(task_repo: Dict) -> Dict[str, str]:
    return {}


def fetch_task_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 parquet 构建 task 数据结构
    """

    # 1 读取 parquet
    task_path = config["task"]["training_task"]
    df = pd.read_parquet(task_path)

    # 2 读取 column mapping
    with open(
        config["column_mapping"][CognitiveL1DatasetName.TRAINING_TASK.value]
    ) as f:
        COLUMN_MAPPING = json.load(f)

    cols = ColumnAccessor(COLUMN_MAPPING, TaskColumnName)

    tasks = []

    # 3 遍历 dataframe
    for _, row in df.iterrows():

        task = {
            "task_id": safe_get(row, cols.task_id),
            "task_name": safe_get(row, cols.task_name),
            "paradigm": safe_get(row, cols.paradigm),
            "cognitive_domain": safe_get(row, cols.cognitive_domain),
            "difficulty": safe_get(row, cols.difficulty),
            "start_level": safe_get(row, cols.start_level),
            "level_max": safe_get(row, cols.level_max),
            "initial_difficulty": safe_get(row, cols.initial_difficulty),
            "life_interpretation": safe_get(row, cols.life_interpretation),
            "min_duration": safe_get(row, cols.min_duration),
            "max_duration": safe_get(row, cols.max_duration),
            "training_time": safe_get(row, cols.training_time),
        }

        tasks.append(task)

    return {"tasks": tasks}


def _parse_task(t: dict) -> Task | None:
    """安全解析 Task"""
    try:
        return Task(**t)
    except Exception as e:
        logger.warning(f"[TASK_PARSE_ERROR] raw_task={t} error={e}")
        return None


def build_task_repository(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    构建系统级 Task 仓库（与用户无关）
    """

    raw_task_info = fetch_task_info(config=config)
    raw_tasks = raw_task_info.get("tasks", [])

    # 1 解析 Task
    task_list: List[Task] = [
        task for t in raw_tasks if (task := _parse_task(t)) is not None
    ]

    # 2 cognitive_domain 校验
    VALID_DOMAINS = {d.value for d in Level1BrainDomain}

    filtered_tasks: List[Task] = []

    for task in task_list:

        if task.cognitive_domain not in VALID_DOMAINS:
            logger.warning(
                "[TASK_INVALID_DOMAIN] task_id=%s domain=%s",
                task.task_id,
                task.cognitive_domain,
            )
            continue

        filtered_tasks.append(task)

    task_list = filtered_tasks

    # 3 task_id 索引
    task_index: Dict[str, Task] = {t.task_id: t for t in task_list if t.task_id}

    # 4 按一级脑能力分组
    level1_grouped: Dict[str, List[Task]] = defaultdict(list)

    for task in task_list:
        level1_grouped[task.cognitive_domain].append(task)

    repo = {
        "task_list": task_list,
        "task_index": task_index,
        "level1_grouped_tasks": dict(level1_grouped),
    }

    logger.debug(
        "[TASK_REPO_BUILT] total_raw=%s valid_tasks=%s level1_keys=%s",
        len(raw_tasks),
        len(task_list),
        len(level1_grouped),
    )

    # =========================
    # 保存 JSON 文件
    # =========================

    repo_path = Path(config["task"]["repository"])

    # 如果目录不存在则创建
    repo_path.parent.mkdir(parents=True, exist_ok=True)

    # Task 对象需要转换为 dict
    json_repo = {
        "task_list": [t.__dict__ for t in repo["task_list"]],
        "task_index": {k: v.__dict__ for k, v in repo["task_index"].items()},
        "level1_grouped_tasks": {
            k: [t.__dict__ for t in v] for k, v in repo["level1_grouped_tasks"].items()
        },
    }

    with open(repo_path, "w", encoding="utf-8") as f:
        json.dump(json_repo, f, ensure_ascii=False, indent=2)

    logger.info("[TASK_REPO_SAVED] path=%s", repo_path)

    return repo


def get_task_repository(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    读取 Task Repository
    如果不存在则重新构建
    """

    repo_path = Path(config["task"]["repository"])

    # 如果不存在则重新构建
    if not repo_path.exists():
        logger.warning("Task repository not found. Rebuilding...")
        return build_task_repository(config)

    logger.info("Loading task repository from %s", repo_path)

    with open(repo_path, "r", encoding="utf-8") as f:
        repo_json = json.load(f)

    # =========================
    # JSON -> Task 对象
    # =========================

    task_list: List[Task] = [Task(**t) for t in repo_json["task_list"]]

    task_index: Dict[str, Task] = {
        k: Task(**v) for k, v in repo_json["task_index"].items()
    }

    level1_grouped = defaultdict(list)

    for domain, tasks in repo_json["level1_grouped_tasks"].items():
        level1_grouped[domain] = [Task(**t) for t in tasks]

    repo = {
        "task_list": task_list,
        "task_index": task_index,
        "level1_grouped_tasks": dict(level1_grouped),
    }

    return repo
