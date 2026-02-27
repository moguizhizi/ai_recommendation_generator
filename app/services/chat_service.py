# app/services/chat_service.py
from app.clients.task_client import fetch_task_info
from app.clients.user_profile_client import fetch_user_profile
from app.schemas.chat import AIRecPlanRequest, AIRecPlanResponse
from app.services.prompt_builder import build_ai_plan_prompt
from app.services.response_parser import parse_ai_plan_response
from app.services.plan_rule_engine import get_fixed_templates, calc_user_type
from app.services.task_processor import process_task_info
from llm.factory import create_llm
from configs import load_config

config = load_config()
llm = create_llm(config)

def generate_ai_plan(req: AIRecPlanRequest) -> AIRecPlanResponse:
    
    profile = fetch_user_profile(req.user_id, req.patient_code)

    user_type = calc_user_type(profile)

    fixed_templates = get_fixed_templates(user_type)

    raw_task_info = fetch_task_info()
    
    task_info = process_task_info(profile, raw_task_info)

    prompt = build_ai_plan_prompt(req, profile, user_type)

    raw_text = llm.generate(prompt)

    llm_part = parse_ai_plan_response(raw_text)

    response = AIRecPlanResponse(
        user_type=user_type,
        overview=fixed_templates["overview"],                 # 固定
        training_plan_intro=llm_part.training_plan_intro,     # LLM
        modules=llm_part.modules,                              # LLM
        score_prediction=llm_part.score_prediction,            # LLM
        home_advice=fixed_templates["home_advice"],            # 固定
        tracking_and_adjustment=fixed_templates["tracking_and_adjustment"],  # 固定
        raw_text=raw_text
    )

    return response