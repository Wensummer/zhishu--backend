"""GET /briefing/{customerId} → Briefing(对齐前端 getBriefing)。"""
from fastapi import APIRouter

from app.schemas.briefing import Briefing
from app.services.briefing_svc import get_briefing

router = APIRouter()


@router.get(
    "/briefing/{customer_id}",
    response_model=Briefing,
    response_model_exclude_none=True,
)
def briefing(customer_id: str) -> Briefing:
    return get_briefing(customer_id)
