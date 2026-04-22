from fastapi import APIRouter

from app.services.evaluation_service import EvaluationService
from app.services.score_prediction_evaluation_service import (
    ScorePredictionEvaluationService,
)
from configs.loader import load_config

router = APIRouter()


@router.post("/recommendation/evaluate")
def evaluate():
    service = EvaluationService()
    return service.evaluate_all_users()


@router.post("/score-prediction/evaluate")
def evaluate_score_prediction():
    service = ScorePredictionEvaluationService(
        config=load_config(),
    )
    return service.evaluate_all_users()
