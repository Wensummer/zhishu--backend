"""GET /copilot/{customerId} → CopilotScript(对齐前端 getCopilotSession)。"""
from fastapi import APIRouter

from app.schemas.session import CopilotScript
from app.services.copilot_svc import get_copilot_script

router = APIRouter()


@router.get(
    "/copilot/{customer_id}",
    response_model=CopilotScript,
    response_model_exclude_none=True,
)
def copilot(customer_id: str) -> CopilotScript:
    return get_copilot_script(customer_id)
