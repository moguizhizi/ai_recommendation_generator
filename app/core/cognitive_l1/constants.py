# app/core/cognitive_l1/constants.py


from enum import Enum


class TaskColumnName(str, Enum):

    TASK_ID = "任务id"
    TASK_NAME = "任务"
    PARADIGM = "范式"
    COGNITIVE_DOMAIN = "一级脑能力"

    DIFFICULTY = "难度"
    START_LEVEL = "起始难度等级"
    LEVEL_MAX = "级别上线"
    INITIAL_DIFFICULTY = "初始难度"

    LIFE_INTERPRETATION = "生活解读"

    MIN_DURATION = "预计最小耗时"
    MAX_DURATION = "预计最大耗时"

    TRAINING_TIME = "训练时间"


class UserTrainingColumnName(str, Enum):

    USER_ID = "用户id"
    PATIENT_CODE = "患者编码"

    AGE = "年龄"
    GENDER = "性别"
    EDUCATION = "学历"
    DISEASE = "疾病"

    LATEST_PERCEPTION = "最新_感知觉"
    LATEST_ATTENTION = "最新_注意力"
    LATEST_MEMORY = "最新_记忆力"
    LATEST_EXECUTIVE = "最新_执行控制"

    WEEK1_PERCEPTION = "倒数一周_感知觉"
    WEEK1_ATTENTION = "倒数一周_注意力"
    WEEK1_MEMORY = "倒数一周_记忆力"
    WEEK1_EXECUTIVE = "倒数一周_执行控制"

    WEEK2_PERCEPTION = "倒数两周_感知觉"
    WEEK2_ATTENTION = "倒数两周_注意力"
    WEEK2_MEMORY = "倒数两周_记忆力"
    WEEK2_EXECUTIVE = "倒数两周_执行控制"

    EPISODIC_MEMORY = "情景记忆"
    INTERFERENCE_CONTROL = "干扰控制"
    RESPONSE_INHIBITION = "反应抑制"
    SPATIAL_WORKING_MEMORY = "空间工作记忆"

    FOCUSED_ATTENTION = "集中性注意"
    PROCESSING_SPEED = "加工速度"
    TIME_PERCEPTION = "时间知觉"
    SELECTIVE_ATTENTION = "选择注意"

    SPATIAL_PERCEPTION = "空间知觉"
    COGNITIVE_FLEXIBILITY = "认知灵活性"
    MOTOR_PERCEPTION = "运动知觉"
    ALERT_ATTENTION = "警觉性注意"

    SPATIAL_MEMORY = "空间记忆"
    SUSTAINED_ATTENTION = "持续注意"
    MEMORY_SPAN = "记忆广度"
    CONFLICT_INHIBITION = "冲突抑制"

    WORKING_MEMORY = "工作记忆"
    NUMBER_SENSE = "数感"
    ATTENTION_CONTROL = "注意控制"

    LAST_DAY_TASK = "最后一天训练任务"
    LAST_7_DAYS_NO_TASK = "最近七天未训练任务"


class CognitiveL1DatasetName(str, Enum):
    USER_BRAIN_SCORE = "alg_cogtrain_brainscore_task_child"
    TRAINING_TASK = "alg_training_task_child"
