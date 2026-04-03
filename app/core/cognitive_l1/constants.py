# app/core/cognitive_l1/constants.py


from enum import Enum


class TaskColumnName(str, Enum):

    TASK_ID = "任务id"
    TASK_NAME = "任务"
    AGE_GROUP = "年龄段"
    PARADIGM = "范式"
    COGNITIVE_DOMAIN = "一级脑能力"
    SUB_COGNITIVE_DOMAIN = "二级脑能力"

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

    WEEK3_PERCEPTION = "倒数三周_感知觉"
    WEEK3_ATTENTION = "倒数三周_注意力"
    WEEK3_MEMORY = "倒数三周_记忆力"
    WEEK3_EXECUTIVE = "倒数三周_执行控制"

    WEEK4_PERCEPTION = "倒数四周_感知觉"
    WEEK4_ATTENTION = "倒数四周_注意力"
    WEEK4_MEMORY = "倒数四周_记忆力"
    WEEK4_EXECUTIVE = "倒数四周_执行控制"

    WEEK5_PERCEPTION = "倒数五周_感知觉"
    WEEK5_ATTENTION = "倒数五周_注意力"
    WEEK5_MEMORY = "倒数五周_记忆力"
    WEEK5_EXECUTIVE = "倒数五周_执行控制"

    WEEK6_PERCEPTION = "倒数六周_感知觉"
    WEEK6_ATTENTION = "倒数六周_注意力"
    WEEK6_MEMORY = "倒数六周_记忆力"
    WEEK6_EXECUTIVE = "倒数六周_执行控制"

    WEEK7_PERCEPTION = "倒数七周_感知觉"
    WEEK7_ATTENTION = "倒数七周_注意力"
    WEEK7_MEMORY = "倒数七周_记忆力"
    WEEK7_EXECUTIVE = "倒数七周_执行控制"

    WEEK8_PERCEPTION = "倒数八周_感知觉"
    WEEK8_ATTENTION = "倒数八周_注意力"
    WEEK8_MEMORY = "倒数八周_记忆力"
    WEEK8_EXECUTIVE = "倒数八周_执行控制"

    WEEK9_PERCEPTION = "倒数九周_感知觉"
    WEEK9_ATTENTION = "倒数九周_注意力"
    WEEK9_MEMORY = "倒数九周_记忆力"
    WEEK9_EXECUTIVE = "倒数九周_执行控制"

    WEEK10_PERCEPTION = "倒数十周_感知觉"
    WEEK10_ATTENTION = "倒数十周_注意力"
    WEEK10_MEMORY = "倒数十周_记忆力"
    WEEK10_EXECUTIVE = "倒数十周_执行控制"

    WEEK11_PERCEPTION = "倒数十一周_感知觉"
    WEEK11_ATTENTION = "倒数十一周_注意力"
    WEEK11_MEMORY = "倒数十一周_记忆力"
    WEEK11_EXECUTIVE = "倒数十一周_执行控制"

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
    LAST_84_DAYS_TASK = "最近84天训练任务"
    LAST_84D_LATEST_PERCEPTION = "倒数第一个84天_最新_感知觉"
    LAST_84D_LATEST_ATTENTION = "倒数第一个84天_最新_注意力"
    LAST_84D_LATEST_MEMORY = "倒数第一个84天_最新_记忆力"
    LAST_84D_LATEST_EXECUTIVE = "倒数第一个84天_最新_执行控制"
    LAST_84_DAYS_FIRST_TASK = "倒数第一个84天训练任务"


class CognitiveL1DatasetName(str, Enum):
    USER_BRAIN_SCORE = "alg_cogtrain_brainscore_task_child"
    TRAINING_TASK = "alg_training_task_child"


class Level1BrainDomain(str, Enum):
    """
    一级脑能力（Level1 Cognitive Domain）
    """

    PERCEPTION = "感知觉"
    ATTENTION = "注意力"
    MEMORY = "记忆力"
    EXECUTIVE = "执行功能"

class Level2BrainDomain(str, Enum):
    """
    二级脑能力（Level2 Cognitive Domain）
    """

    WORKING_MEMORY = "工作记忆"
    CONFLICT_INHIBITION = "冲突抑制"
    INTERFERENCE_CONTROL = "干扰控制"
    ALERTING_ATTENTION = "警觉性注意"
    SELECTIVE_ATTENTION = "选择注意"
    PROCESSING_SPEED = "加工速度"
    SUSTAINED_ATTENTION = "持续注意"
    FOCUSED_ATTENTION = "集中性注意"
    SPATIAL_PERCEPTION = "空间知觉"
    SPATIAL_MEMORY = "空间记忆"
    SPATIAL_WORKING_MEMORY = "空间工作记忆"
    MEMORY_SPAN = "记忆广度"
    MOTOR_PERCEPTION = "运动知觉"
    COGNITIVE_FLEXIBILITY = "认知灵活性"
    TIME_PERCEPTION = "时间知觉"
    ATTENTION_CONTROL = "注意控制"
    RESPONSE_INHIBITION = "反应抑制"
    EPISODIC_MEMORY = "情景记忆"
    NUMERICAL_SENSE = "数感"


class ParadigmType(str, Enum):
    """
    任务范式枚举
    """

    NO_PARADIGM = "no_paradigm"

    SEQ_MEMORY_SINGLE_MATCH = "序列记忆单项匹配"
    RECALL_DISTRIBUTION_INTERFERENCE = "回忆分布+干扰"
    TWO_BACK = "2-back"
    BATCH_MEMORY_SINGLE_MATCH = "批量记忆单项匹配"
    BILATERAL_INHIBITION_REVERSE = "双侧抑制+反向"
    PSYCHOLOGICAL_ALERTNESS = "心理警觉任务"
    DIRECTION_STROOP_TASK_SWITCH = "方向Stroop+任务切换"
    BILATERAL_INHIBITION = "双侧抑制"
    COLOR_STROOP = "颜色Stroop"
    UFOV_BEGINNER = "有效视野-入门"
    SIZE_STROOP_TASK_SWITCH = "尺寸Stroop+任务切换"
    DIRECTION_STROOP_BEGINNER = "方向Stroop-入门"
    RAPID_SEQUENCE_BEGINNER = "快速序列-入门"
    CPT = "持续度表现测验"
    VISUAL_SEARCH_STANDARD = "视觉搜索-标准"
    N_BACK_TASK = "N-back任务"
    RSVP_TASK = "快速序列视觉呈现任务"
    RAPID_SEQUENCE_STANDARD = "快速序列-标准"
    LEFT_RIGHT_ROTATION_SYMMETRY = "左右旋转+对称物"
    CORSI_BLOCK = "科西方块敲击任务"
    SEQ_MEMORY_FACE = "序列记忆单项匹配+面孔"
    CANCELLATION_TEST = "划销测验"
    DYNAMIC_CANCELLATION_STANDARD = "动态划消-标准"
    NAME_ASSOCIATION = "姓名关联任务"
    VISUAL_TRACKING = "视觉追踪"
    GO_NO_GO = "尝试/不尝试任务"
    VISUAL_SEARCH_BEGINNER = "视觉搜索-入门"
    RECALL_POSITION_STANDARD = "回忆位置-标准"
    LEFT_RIGHT_ROTATION = "左右旋转"
    UFOV_MEMORY_SPAN = "有效视野+记忆广度"
    BATCH_MEMORY_MULTI_MATCH = "批量记忆多项匹配"
    UFOV_GO_NO_GO = "有效视野+go/no-go"
    FEATURE_INDUCTION_MATCH = "特征归纳匹配"

L1_LIST = list(Level1BrainDomain)
L2_LIST = list(Level2BrainDomain)

L1_INDEX = {e.value: i for i, e in enumerate(L1_LIST)}
L2_INDEX = {e.value: i for i, e in enumerate(L2_LIST)}

# 反向映射
L1_INDEX_REVERSE = {v: k for k, v in L1_INDEX.items()}
L2_INDEX_REVERSE = {v: k for k, v in L2_INDEX.items()}
