# app/services/chat_service.py
from app.clients.task_client import fetch_task_info
from app.clients.user_profile_client import fetch_user_profile
from app.core.constants import UserType
from app.schemas.chat import AIRecPlanData, AIRecPlanRequest, AIRecPlanResponse
from app.services.plan_rule_engine import (
    build_advantage_user_modules,
    build_growth_user_modules,
    build_potential_user_modules,
    build_score_prediction,
    build_special_user_modules,
    enrich_profile_with_user_type,
    enrich_user_profile_with_tasks,
    get_fixed_templates,
    render_plan_text,
)
from app.services.task_processor import (
    build_level2_to_level1_map,
    build_task_repository,
)
from llm.base import BaseLLM

from app.core.logging import get_logger

logger = get_logger(__name__)


USER_TYPE_MODULE_BUILDER = {
    UserType.ADVANTAGE: build_advantage_user_modules,
    UserType.POTENTIAL: build_potential_user_modules,
    UserType.SPECIAL: build_special_user_modules,
    UserType.GROWTH: build_growth_user_modules,
}


def generate_ai_plan(req: AIRecPlanRequest, llm: BaseLLM) -> AIRecPlanResponse:
    try:
        profile = fetch_user_profile(req.user_id, req.patient_code)
        raw_task_info = fetch_task_info()
        task_repo = build_task_repository(raw_task_info)

        profile = enrich_user_profile_with_tasks(profile, task_repo)
        profile = enrich_profile_with_user_type(profile)

        fixed_templates = get_fixed_templates(profile)
        level2_to_level1 = build_level2_to_level1_map(task_repo)

        user_type: UserType = profile["user_type"]

        module_builder = USER_TYPE_MODULE_BUILDER.get(
            user_type, build_growth_user_modules
        )
        modules = module_builder(profile, level2_to_level1, llm)

        score_prediction = build_score_prediction(profile, fixed_templates)

        # 构建核心数据对象
        plan_data = AIRecPlanData(
            user_type=user_type,
            overview=fixed_templates["overview"],
            training_plan_intro=fixed_templates["training_plan_intro"],
            modules=modules,
            score_prediction=score_prediction,
            home_advice=fixed_templates["home_advice"],
            tracking_and_adjustment=fixed_templates["tracking_and_adjustment"],
            raw_text="",  # 如果后面接LLM可以填
        )

        # 渲染展示文本
        display_text = render_plan_text(plan_data)

        # 返回包装结构
        return AIRecPlanResponse(
            data=plan_data,
            display_text=display_text,
        )

    except Exception as e:
        logger.exception(f"[AI_PLAN_ERROR] user_id={req.user_id} error={str(e)}")
        raise
