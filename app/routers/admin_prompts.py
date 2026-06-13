"""各能力位系统提示词的读写(管理员·系统模型配置页用)。

GET /admin/system-prompts → {slot: prompt}(生效值=默认或覆盖)
PUT /admin/system-prompts → 保存覆盖并返回最新生效值

提示词绑「能力位」非模型;仅 LLM 位有(asr 无)。当前 chatbot 位即时生效(chat_svc 读取)。
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.prompts import get_prompts, set_prompts

router = APIRouter()


class PromptsBody(BaseModel):
    prompts: dict[str, str]


@router.get("/admin/system-prompts")
def read_prompts() -> dict[str, str]:
    return get_prompts()


@router.put("/admin/system-prompts")
def write_prompts(body: PromptsBody) -> dict[str, str]:
    set_prompts(body.prompts)
    return get_prompts()
