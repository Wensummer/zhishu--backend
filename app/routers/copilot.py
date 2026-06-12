"""通话 copilot 接口。

GET  /copilot/{customerId} → CopilotScript(剧本回放,对齐前端 getCopilotSession)
POST /copilot/analyze      → 实时通话:一句客户的话 → 意图 + 触发的推荐/话术
"""
from fastapi import APIRouter

from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.session import CopilotScript
from app.services.copilot_svc import get_copilot_script
from app.services.intent_svc import analyze

router = APIRouter()


@router.get(
    "/copilot/{customer_id}",
    response_model=CopilotScript,
    response_model_exclude_none=True,
)
def copilot(customer_id: str) -> CopilotScript:
    return get_copilot_script(customer_id)


@router.post(
    "/copilot/analyze",
    response_model=AnalyzeResponse,
    response_model_exclude_none=True,
)
def copilot_analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    intent, recommendation, script = analyze(req.text, req.context)
    return AnalyzeResponse(intent=intent, recommendation=recommendation, script=script)
