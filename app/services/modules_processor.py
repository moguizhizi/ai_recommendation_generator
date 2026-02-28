from typing import List, Dict
from app.schemas.chat import TrainingItem, TrainingModule
from app.core.constants import ModuleName, ABILITY_NAME_MAP


def fetch_tasks_by_ability(ability_key: str) -> List[str]:
    """
    本地接口：根据能力类型获取训练任务
    """
    TASK_MAP = {
        "memory": ["长度知觉任务（小马过河、测距打鼠）", "多感官协同匹配"],
        "exec": ["冲突抑制任务", "规则切换游戏"],
        "attention": ["持续注意追踪", "警觉性反应任务"],
        "perception": ["空间知觉训练", "图形匹配任务"],
    }
    return TASK_MAP.get(ability_key, [])


def calc_difficulty(ability_key: str, score: int) -> str:
    """
    本地规则：计算训练难度
    """
    return "当前能力层级+0.5~1级"


def fetch_frequency() -> str:
    """
    本地接口：获取训练频次
    """
    return "每日1次，每次4-8分钟"


def generate_goal_by_llm(ability_name_cn: str) -> str:
    """
    调用大模型生成训练目标
    """
    return f"强化{ability_name_cn}能力，提升整体认知灵活性与稳定性。"
