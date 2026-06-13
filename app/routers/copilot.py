"""通话 copilot 接口。

GET  /copilot/{customerId} → CopilotScript(剧本回放,对齐前端 getCopilotSession)
POST /copilot/analyze      → 实时通话:一句客户的话 → 意图 + 推荐(快)
POST /copilot/script       → 拿到推荐后,异步生成"给销售的话术"(慢路径,不阻塞推荐)
"""
from fastapi import APIRouter, HTTPException

from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse, ScriptRequest
from app.schemas.script import TalkScript
from app.schemas.session import CopilotScript
from app.services.copilot_svc import get_copilot_script
from app.services.intent_svc import analyze
from app.services.script_svc import generate_sales_script

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
    intent, recommendation, script, need = analyze(req.text, req.context)
    return AnalyzeResponse(
        intent=intent, recommendation=recommendation, script=script, need=need
    )


@router.post(
    "/copilot/script",
    response_model=TalkScript,
    response_model_exclude_none=True,
)
def copilot_script(req: ScriptRequest) -> TalkScript:
    script = generate_sales_script(
        req.text,
        req.context,
        req.need_type,
        req.note,
        req.target_model_id,
        req.reason,
        req.score,
    )
    if script is None:
        raise HTTPException(status_code=502, detail="话术生成失败")
    return script
