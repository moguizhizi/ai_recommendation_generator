# app/core/constants.py
from enum import Enum


class UserType(str, Enum):
    ADVANTAGE = "优势倾向型"
    POTENTIAL = "潜能倾向型"
    SPECIAL = "专项优势型"
    GROWTH = "蓄力成长型"


class ScoreThreshold:
    ADVANTAGE_LINE = 100
    POTENTIAL_LINE = 90