# app/core/constants.py
from enum import Enum


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
