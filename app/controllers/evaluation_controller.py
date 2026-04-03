from fastapi import APIRouter
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.post("/recommendation/evaluate")
def evaluate():
    service = EvaluationService()
    return service.evaluate_all_users()
