# app/core/constants.py
from enum import Enum

from app.core.cognitive_l1.constants import Level1BrainDomain, ParadigmType


class UserType(str, Enum):
    ADVANTAGE = "优势倾向型"
    POTENTIAL = "潜能倾向型"
    SPECIAL = "专项优势型"
    GROWTH = "蓄力成长型"


class ModuleName(str, Enum):
    ADVANTAGE_EXPAND = "优势能力拓展模块"
    BALANCED_TRAIN = "能力均衡训练模块"

    POTENTIAL_EXPAND = "认知潜能拓展模块"

    CORE_STRENGTHEN = "核心能力强化模块"
    RELATED_ENHANCE = "关联能力提升训练模块"

    BASIC_STABLE = "基础能力稳控模块"
    STEP_UP = "阶梯式提升模块"


class ScoreThreshold:
    ADVANTAGE_LINE = 100
    POTENTIAL_LINE = 90


class L2BlockDefaults:
    TITLE = "下一阶段认知能力训练分布"
    DESCRIPTION = (
        "基于本阶段孩子表现，为您生成专属训练方案，放大孩子的优势、补齐短板，助力认知能力均衡发展"
    )
    HINT = "该占比为AI预测，请以最终训练推送为准"


class ScorePredictionBlockDefaults:
    TITLE = "脑力值AI预测"
    SUMMARY = (
        "按照本方案的训练占比规律坚持训练，预计下一阶段孩子的各项一级脑能力值将获得针对性提升哦~"
    )
    HINT = "脑力值为AI预测，请以孩子实际表现为准"
    LEGENDS = (
        {
            "label": "本阶段分值",
            "description": "本阶段努力成果，也是下一阶段的起跑线",
        },
        {
            "label": "提升参考",
            "description": "持续训练，孩子3个月后预计提升脑能力水平",
        },
        {
            "label": "回落参考",
            "description": "未持续训练，孩子预计3/6个月回落脑能力水平",
        },
    )


LEVEL1_DOMAIN_KEY_MAP = {
    Level1BrainDomain.PERCEPTION: "perception",
    Level1BrainDomain.ATTENTION: "attention",
    Level1BrainDomain.MEMORY: "memory",
    Level1BrainDomain.EXECUTIVE: "executive_function",
}


class ExcludedParadigm(str, Enum):
    """
    不建议在推荐模板中展示的范式
    """

    TWO_BACK = ParadigmType.TWO_BACK.value
    DIRECTION_STROOP_TASK_SWITCH = ParadigmType.DIRECTION_STROOP_TASK_SWITCH.value
    COLOR_STROOP = ParadigmType.COLOR_STROOP.value
    SIZE_STROOP_TASK_SWITCH = ParadigmType.SIZE_STROOP_TASK_SWITCH.value
    DIRECTION_STROOP_BEGINNER = ParadigmType.DIRECTION_STROOP_BEGINNER.value
    N_BACK_TASK = ParadigmType.N_BACK_TASK.value
    UFOV_GO_NO_GO = ParadigmType.UFOV_GO_NO_GO.value


class Level1Score:
    """
    一级脑能力分数体系
    """

    MIN_SCORE = 0
    MAX_SCORE = 160

    @classmethod
    def clamp(cls, score: float) -> float:
        return max(cls.MIN_SCORE, min(cls.MAX_SCORE, score))
