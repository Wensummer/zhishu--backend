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


class ScriptKnowledgeEvidence(CamelModel):
    """知识库检索结果记录 —— 镜像 KnowledgeEvidenceRecord。"""
    segment_id: str
    document_id: str
    document_name: str
    content: str
    score: float
    collected_at: str | None = None


class ScriptEvidenceResult(CamelModel):
    """单条话术的知识库证据结果。"""
    script_id: str
    query: str
    records: list[ScriptKnowledgeEvidence]
