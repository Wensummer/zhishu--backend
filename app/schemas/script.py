"""话术 schema —— 镜像 lib/types 的 TalkScript。"""
from typing import Literal

from app.schemas.base import CamelModel

ScriptScene = Literal["opening", "sellingPoint", "objection", "pricing", "renewal"]


class TalkScript(CamelModel):
    id: str
    customer_id: str | None = None
    scene: ScriptScene
    title: str
    content: str
    objection: str | None = None        # objection 场景:客户可能的异议
