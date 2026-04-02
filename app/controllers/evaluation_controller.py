from fastapi import APIRouter
from app.services.evaluation_service import EvaluationService

router = APIRouter()
service = EvaluationService()


@router.post("/recommendation/evaluate")
def evaluate():
    return service.evaluate_all_users()