# app/services/chat_service.py
from typing import Any, Dict

from fastapi import HTTPException

from app.core.constants import UserType
from app.schemas.chat import AIRecPlanData, AIRecPlanRequest, AIRecPlanResponse
from app.services.plan_rule_engine import (
    build_L2_brain_ability_treemap,
    build_advantage_user_modules,
    build_growth_user_modules,
    build_potential_user_modules,
    build_score_prediction,
    build_special_user_modules,
    enrich_profile_with_user_type,
    enrich_user_profile_with_brain_distribution,
    enrich_user_profile_with_tasks,
    get_fixed_templates,
    render_plan_text,
)
from app.services.task_processor import (
    build_level2_to_level1_map,
    get_task_repository,
)
from app.services.user_processor import fetch_user_profile
from llm.base import BaseLLM

from utils.logger import get_logger
from models.model_factory import ModelManager

logger = get_logger(__name__)


USER_TYPE_MODULE_BUILDER = {
    UserType.ADVANTAGE: build_advantage_user_modules,
    UserType.POTENTIAL: build_potential_user_modules,
    UserType.SPECIAL: build_special_user_modules,
    UserType.GROWTH: build_growth_user_modules,
}


def generate_ai_plan(
    req: AIRecPlanRequest,
    llm: BaseLLM,
    model_manager: ModelManager,
    config: Dict[str, Any],
) -> AIRecPlanResponse:

    task_repo = get_task_repository(config=config)
    profile = fetch_user_profile(req.user_id, req.patient_code, config=config)
    
    profile = enrich_user_profile_with_tasks(profile, task_repo)
    profile = enrich_user_profile_with_brain_distribution(profile, task_repo)
    profile = enrich_profile_with_user_type(profile)

    fixed_templates = get_fixed_templates(profile)
    level2_to_level1 = build_level2_to_level1_map(task_repo)
    build_L2_brain_ability_treemap(profile, task_repo)

    user_type: UserType = profile["user_type"]

    module_builder = USER_TYPE_MODULE_BUILDER.get(user_type, build_growth_user_modules)
    modules = module_builder(profile, level2_to_level1, llm)

    score_prediction = build_score_prediction(profile, fixed_templates, model_manager)

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
