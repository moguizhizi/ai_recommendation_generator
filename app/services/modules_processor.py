from typing import Dict, List, Optional
from collections import defaultdict
import random

from app.core.cognitive_l1.constants import ParadigmType
from app.core.constants import ExcludedParadigm
from app.schemas.common import Task
from llm.base import BaseLLM
from app.prompts.plan_prompt import GoalSummaryPrompt


def get_recommended_tasks_grouped_by_paradigm(
    l1_recommended_tasks: List[Task],
) -> Dict[str, List[Task]]:
    """
    按范式分组漏训任务
    - level1_key: 一级脑能力 key
    - level2_keys: 可选
    """

    filtered_tasks: List[Task] = []

    for task in l1_recommended_tasks:
        if not task.paradigm:
            continue

        filtered_tasks.append(task)

    grouped = defaultdict(list)
    for task in filtered_tasks:
        grouped[task.paradigm].append(task)

    return dict(grouped)


def fetch_tasks_by_ability(paradigm_tasks: Dict[str, List[Task]]) -> str:
    """
    将 paradigm_tasks 组装为展示字符串

    规则：
    1. 优先选择 task >=2 的范式
    2. 若不存在，则从 task <2 的范式中随机选
    3. task 数量目标为 2~3，不够则降级
    """

    # --- 收集所有范式 ---
    paradigms_ge2 = []
    paradigms_lt2 = []

    for paradigm, tasks in paradigm_tasks.items():
        if paradigm == ParadigmType.NO_PARADIGM.value or not tasks:
            continue

        if len(tasks) >= 2:
            paradigms_ge2.append((paradigm, tasks))
        else:
            paradigms_lt2.append((paradigm, tasks))

    # --- 优先选择 >=2 的范式 ---
    if paradigms_ge2:
        paradigm, tasks = random.choice(paradigms_ge2)
    elif paradigms_lt2:
        paradigm, tasks = random.choice(paradigms_lt2)
    else:
        paradigm, tasks = None, None

    if tasks:

        # 目标 task 数
        target_count = random.randint(2, 3)

        # 实际取值
        task_count = min(len(tasks), target_count)

        # 随机取 task
        picked_tasks = random.sample(tasks, task_count)

        task_names = [t.task_name for t in picked_tasks if t.task_name]

        if task_names:

            task_str = "、".join(task_names)

            # 如果 paradigm 在 ExcludedParadigm 中，则只显示 task_str
            if paradigm in ExcludedParadigm._value2member_map_:
                return task_str

            return f"{paradigm}（{task_str}）"

    # --- fallback ---
    no_paradigm_tasks = paradigm_tasks.get(ParadigmType.NO_PARADIGM.value, [])

    if no_paradigm_tasks:

        task_count = min(len(no_paradigm_tasks), random.randint(2, 3))
        picked_tasks = random.sample(no_paradigm_tasks, task_count)

        task_names = [t.task_name for t in picked_tasks if t.task_name]

        if task_names:
            return f"{'、'.join(task_names)}等任务"

    return ""


def calc_difficulty(
    last_day_task_info: Optional[Task], paradigm_tasks: Dict[str, List[Task]]
) -> str:
    """
    本地规则：根据历史任务难度 + 本次推荐任务难度区间，生成训练难度文案

    规则：
    1. 从 paradigm_tasks 中筛选 difficulty > last_task.difficulty 的任务
    2. 计算难度差值区间（min_diff ~ max_diff）
    3. 映射为：当前能力层级 + min_diff ~ max_diff 级
    4. 若 last_task 或 difficulty 缺失 → 使用默认兜底文案
    """

    DEFAULT = "当前能力层级+0.5~1级"

    if not last_day_task_info or not isinstance(
        last_day_task_info.difficulty, (int, float)
    ):
        return DEFAULT

    base = float(last_day_task_info.difficulty)

    diffs: List[float] = []

    for tasks in paradigm_tasks.values():
        for task in tasks:
            if isinstance(task.difficulty, (int, float)) and task.difficulty > base:
                diffs.append(round(task.difficulty - base, 1))

    # --- 没有比上一次更高的难度，兜底 ---
    if not diffs:
        return DEFAULT

    diffs.sort()
    min_diff, max_diff = diffs[0], diffs[-1]

    # --- 只提升一个等级 ---
    if min_diff == max_diff:
        return f"当前能力层级+{min_diff}级"

    return f"当前能力层级+{min_diff}~{max_diff}级"


def fetch_frequency(paradigm_tasks: Dict[str, List[Task]]) -> str:
    """
    本地接口：根据已匹配的任务列表，生成训练频次文案

    规则：
    - 从 paradigm_tasks 中提取所有 Task.max_duration
    - 过滤无效 / 非正数时长
    - 去重 + 升序排序
    - 组装为：
        - 1 个值 → 每日1次，每次 X 分钟
        - 多个值 → 每日1次，每次 X-Y 分钟
    - 若无有效时长 → 使用默认兜底文案
    """

    durations: List[int] = []

    for tasks in paradigm_tasks.values():
        for task in tasks:
            if isinstance(task.max_duration, (int, float)) and task.max_duration > 0:
                durations.append(int(task.max_duration))

    # --- 无有效时长兜底 ---
    if not durations:
        return "每日1次，每次4-8分钟"

    # --- 去重 + 排序 ---
    durations = sorted(set(durations))

    # --- 只有一个时长 ---
    if len(durations) == 1:
        return f"每日1次，每次{durations[0]}分钟"

    # --- 多个时长区间 ---
    return f"每日1次，每次{durations[0]}-{durations[-1]}分钟"


def generate_goal_by_llm(paradigm_tasks: Dict[str, List[Task]], llm: BaseLLM) -> str:
    """
    根据不同训练范式下的任务 life_desc，总结生成整体训练目标
    """

    # 1️⃣ 收集 life_desc
    life_desc_list = []

    for paradigm, tasks in paradigm_tasks.items():
        for task in tasks:
            if task.life_interpretation:
                life_desc_list.append(
                    f"- [{paradigm}] {task.task_name}: {task.life_interpretation}"
                )

    # 如果没有可用描述，直接返回默认值
    if not life_desc_list:
        return "提升综合认知能力与生活应用能力"

    life_desc_text = "\n".join(life_desc_list)

    # 2️⃣ 构建 Prompt
    prompt = GoalSummaryPrompt.render(life_desc_text=life_desc_text)

    # 3️⃣ 直接调用传入的 llm
    try:
        response = llm.chat(prompt)
    except Exception:
        # 如果 LLM 调用失败，返回默认目标
        return "提升综合认知能力与生活应用能力"

    if not response:
        return "提升综合认知能力与生活应用能力"

    return response.strip()
