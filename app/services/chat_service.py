# app/services/chat_service.py
from app.clients.task_client import fetch_task_info
from app.clients.user_profile_client import fetch_user_profile
from app.core.constants import UserType
from app.schemas.chat import AIRecPlanRequest, AIRecPlanResponse
from app.services.plan_rule_engine import (
    build_advantage_user_modules,
    build_growth_user_modules,
    build_potential_user_modules,
    build_special_user_modules,
    enrich_profile_with_user_type,
    enrich_user_profile_with_tasks,
    get_fixed_templates,
)
from app.services.task_processor import (
    build_level2_to_level1_map,
    build_task_repository,
)
from llm.factory import create_llm
from configs import load_config

config = load_config()
llm = create_llm(config)

USER_TYPE_MODULE_BUILDER = {
    UserType.ADVANTAGE: build_advantage_user_modules,
    UserType.POTENTIAL: build_potential_user_modules,
    UserType.SPECIAL: build_special_user_modules,
    UserType.GROWTH: build_growth_user_modules,
}


def generate_ai_plan(req: AIRecPlanRequest) -> AIRecPlanResponse:
    profile = fetch_user_profile(req.user_id, req.patient_code)

    raw_task_info = fetch_task_info()
    task_repo = build_task_repository(raw_task_info)

    profile = enrich_user_profile_with_tasks(profile, task_repo)
    profile = enrich_profile_with_user_type(profile)

    fixed_templates = get_fixed_templates(profile)
    level2_to_level1 = build_level2_to_level1_map(task_repo)

    user_type: UserType = profile["user_type"]

    module_builder = USER_TYPE_MODULE_BUILDER.get(user_type, build_growth_user_modules)
    modules = module_builder(profile, level2_to_level1)

    prompt = build_ai_plan_prompt(req, profile, modules)

    raw_text = llm.generate(prompt)
    llm_part = parse_ai_plan_response(raw_text)

    modules = merge_llm_into_modules(modules, llm_part.modules)

    return AIRecPlanResponse(
        user_type=user_type,
        overview=fixed_templates["overview"],
        training_plan_intro=llm_part.training_plan_intro,
        modules=modules,
        score_prediction=llm_part.score_prediction,
        home_advice=fixed_templates["home_advice"],
        tracking_and_adjustment=fixed_templates["tracking_and_adjustment"],
        raw_text=raw_text,
    )
