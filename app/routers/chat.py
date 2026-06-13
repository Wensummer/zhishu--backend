"""配置答疑 chatbot 接口。

POST /chat → 流式纯文本(text/plain),逐字吐 LLM 答复。任意角色/页面可用。
前端走同源 BFF /api/chat 转发,读 ReadableStream 边收边显示;后端故障由前端兜底本地 FAQ。
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.chat_svc import stream_chat

router = APIRouter()


@router.post("/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    history = [m.model_dump() for m in req.messages]

    def gen():
        try:
            yield from stream_chat(history)
        except Exception:
            yield "抱歉,答疑助手暂时连不上,请稍后再试,或前往对应功能页查看(模型横评 / 四问选型 / 状态监控)。"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
