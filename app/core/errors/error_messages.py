# app/core/errors/error_messages.py

from .error_codes import ErrorCode


ERROR_MESSAGES = {
    ErrorCode.USER_NOT_FOUND: "未找到对应用户",
    ErrorCode.DATA_FILE_NOT_FOUND: "数据文件不存在",
    ErrorCode.COLUMN_MAPPING_NOT_FOUND: "列映射文件不存在",
    ErrorCode.TASK_REPO_EMPTY: "任务仓库为空",
    ErrorCode.TASK_REPO_BUILD_FAILED: "任务仓库构建失败",
    ErrorCode.MODEL_NOT_LOADED: "预测模型未加载",
    ErrorCode.SCORE_PREDICTION_FAILED: "能力预测失败",
    ErrorCode.LLM_CALL_FAILED: "大模型调用失败",
    ErrorCode.AI_PLAN_GENERATION_FAILED: "AI训练方案生成失败",
    ErrorCode.INTERNAL_ERROR: "系统内部错误",
}
