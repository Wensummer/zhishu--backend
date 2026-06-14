"""通话小结接口(结束通话后的 LLM 小结 + 持久化/回流)。

POST /copilot/summary/generate     → 据整通转写生成结构化小结(不存)
POST /copilot/summary/save         → 存到客户名下(沟通历史)并回流商机(温度→客户标签)
GET  /copilot/summary/{customerId} → 列出该客户历次小结(跟进时间线 / 复盘)
前端走同源 BFF /api/copilot/summary*。
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.repo import call_summaries as repo
from app.schemas.summary import (
    CallSummary,
    GenerateSummaryRequest,
    SaveSummaryRequest,
)
from app.services.summary_svc import generate_summary

router = APIRouter()

CN_TZ = timezone(timedelta(hours=8))
# 成交温度 → 回流到客户商机标签
TEMP_TAG = {"热": "🔥高意向", "温": "持续跟进", "冷": "长期培育"}


def _now() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M")


@router.post(
    "/copilot/summary/generate",
    response_model=CallSummary,
    response_model_exclude_none=True,
)
def generate(req: GenerateSummaryRequest) -> CallSummary:
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="转写为空")
    try:
        data = generate_summary(req.transcript, req.customer_name)
    except Exception:
        raise HTTPException(status_code=502, detail="小结生成失败")
    return CallSummary(customer_id=req.customer_id, created_at=_now(), **data)


@router.post(
    "/copilot/summary/save",
    response_model=CallSummary,
    response_model_exclude_none=True,
)
def save(req: SaveSummaryRequest) -> CallSummary:
    sid = uuid.uuid4().hex[:12]
    created = req.created_at or _now()
    record = {
        "id": sid,
        "customer_id": req.customer_id,
        "created_at": created,
        "demand": req.demand,
        "intents": req.intents,
        "recommendation": req.recommendation,
        "temperature": req.temperature,
        "next_steps": req.next_steps,
        "scripts": req.scripts,
        "turns": [t.model_dump() for t in req.turns],
    }
    repo.insert(record)

    # 回流商机:把成交温度标签并入客户 tags(附加动作,失败不影响小结已保存)
    try:
        tag = TEMP_TAG.get(req.temperature)
        if tag:
            repo.add_customer_tag(req.customer_id, tag)
    except Exception:
        pass

    return CallSummary(**record)


@router.get(
    "/copilot/summary/{customer_id}",
    response_model=list[CallSummary],
    response_model_exclude_none=True,
)
def list_for_customer(customer_id: str) -> list[CallSummary]:
    return [CallSummary(**s) for s in repo.list_by_customer(customer_id)]
