# app/services/chat_service.py
from typing import Any, Dict, Tuple

from app.core.constants import UserType
from app.schemas.chat import (
    AIRecPlanData,
    AIRecPlanRequest,
    AIRecPlanResponse,
    L2AbilityDistributionBlock,
)
from app.schemas.chat_v2 import (
    AIRecPlanResponseV2,
    AIRecPlanV2,
    HomeAdviceSection,
    ResponseMetaV2,
    TrainingPlanSection,
    TrainingTipsSection,
)
from app.services.plan_rule_engine import (
    build_L2_brain_ability_treemap,
    build_advantage_user_modules,
    build_growth_user_modules,
    build_l1_task_map,
    build_potential_user_modules,
    build_score_prediction,
    build_special_user_modules,
    enrich_profile_with_user_type,
    enrich_user_profile_with_brain_distribution,
    enrich_user_profile_with_domain_histories,
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

HOME_ADVICE_CONTENT_V2 = (
    "1、每日可增加10分钟“家庭寻宝游戏”（锻炼感知觉）或“时间管理小任务”（锻炼执行控制），强化能力迁移"
)
TRAINING_TIPS_ITEMS_V2 = [
    "1. 看曲线：关注【儿童认知数字疗法】小程序查看训练日报、周报，孩子进步一目了然～",
    "2. 看里程碑：小程序定期推送阶段报告，查看孩子认知成长里程碑，见证阶段性收获～",
    "3. 看任务：日报 / 周报可看训练明细，周报提交训练反馈，做孩子训练的“贴心队友”～",
]


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
    plan_data, display_text = build_ai_plan_content_v1(
        req=req,
        llm=llm,
        model_manager=model_manager,
        config=config,
    )

    return AIRecPlanResponse(
        data=plan_data,
        display_text=display_text,
    )


def generate_ai_plan_v2(
    req: AIRecPlanRequest,
    model_manager: ModelManager,
    config: Dict[str, Any],
) -> AIRecPlanResponseV2:
    profile, plan_data = build_ai_plan_content_v2(
        req=req,
        model_manager=model_manager,
        config=config,
    )

    return AIRecPlanResponseV2(
        meta=ResponseMetaV2(
            version="v2",
            user_id=profile.get("user_id"),
            patient_code=profile.get("patient_code"),
        ),
        plan=plan_data,
    )


def build_ai_plan_content_v1(
    req: AIRecPlanRequest,
    llm: BaseLLM,
    model_manager: ModelManager,
    config: Dict[str, Any],
) -> Tuple[AIRecPlanData, str]:
    task_repo = get_task_repository(config=config)
    profile = fetch_user_profile(req.user_id, req.patient_code, config=config)

    profile = enrich_user_profile_with_tasks(profile, task_repo)
    profile = enrich_user_profile_with_brain_distribution(
        profile, profile.get("last_84_days_task"), task_repo
    )
    profile = enrich_user_profile_with_domain_histories(profile, config=config)
    profile = enrich_profile_with_user_type(profile)

    fixed_templates = get_fixed_templates(profile)
    level2_to_level1 = build_level2_to_level1_map(task_repo)

    recommended_tasks, l2_stats = build_L2_brain_ability_treemap(
        profile,
        profile["latest_level1_scores"],
        task_repo,
    )

    l1_task_map = build_l1_task_map(recommended_tasks)

    user_type: UserType = profile["user_type"]

    module_builder = USER_TYPE_MODULE_BUILDER.get(user_type, build_growth_user_modules)
    modules = module_builder(profile, level2_to_level1, llm, l1_task_map)

    score_prediction = build_score_prediction(
        profile,
        model_manager,
        config=config,
    )

    # 构建核心数据对象
    plan_data = AIRecPlanData(
        user_type=user_type,
        overview=fixed_templates["overview"],
        training_plan_intro=fixed_templates["training_plan_intro"],
        modules=modules,
        score_prediction=score_prediction,
        home_advice=fixed_templates["home_advice"],
        tracking_and_adjustment=fixed_templates["tracking_and_adjustment"],
        l2_ability_distribution=l2_stats,
        raw_text="",  # 如果后面接LLM可以填
    )

    # 渲染展示文本
    display_text = render_plan_text(plan_data)

    return plan_data, display_text


def build_ai_plan_content_v2(
    req: AIRecPlanRequest,
    model_manager: ModelManager,
    config: Dict[str, Any],
) -> Tuple[Dict[str, Any], AIRecPlanV2]:
    task_repo = get_task_repository(config=config)
    profile = fetch_user_profile(req.user_id, req.patient_code, config=config)

    profile = enrich_user_profile_with_tasks(profile, task_repo)
    profile = enrich_user_profile_with_brain_distribution(
        profile, profile.get("last_84_days_task"), task_repo
    )
    profile = enrich_user_profile_with_domain_histories(profile, config=config)
    profile = enrich_profile_with_user_type(profile)

    _, l2_stats = build_L2_brain_ability_treemap(
        profile,
        profile["latest_level1_scores"],
        task_repo,
    )


    score_prediction = build_score_prediction(
        profile,
        model_manager,
        config=config,
    )

    plan_data_v2 = AIRecPlanV2(
        training_plan_section=TrainingPlanSection(
            score_prediction=score_prediction,
            l2_block=L2AbilityDistributionBlock(
                l2_ability_distribution=l2_stats,
            ),
        ),
        home_advice_section=HomeAdviceSection(content=HOME_ADVICE_CONTENT_V2),
        training_tips_section=TrainingTipsSection(items=TRAINING_TIPS_ITEMS_V2),
    )

    return profile, plan_data_v2
