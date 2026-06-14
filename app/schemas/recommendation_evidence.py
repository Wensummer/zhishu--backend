"""推荐选型支撑依据知识库检索 schema。

前端四问选型/简报/copilot 拿到推荐后 → 调 POST /recommendation/evidence
→ 从 Dify 选型依据知识库检索定性的理论支撑 → 返回命中段落供前端展示。
"""
from pydantic import Field

from app.schemas.base import CamelModel


class EvidenceCandidate(CamelModel):
    model_id: str = ""
    model_name: str = ""
    query: str | None = None  # 前端传入的检索文本,不对齐 camelCase,用别名保持原样
    customer_id: str = ""

    class Config:
        # 让 query 字段不经过 alias_generator 转换,保持原始值
        protected_namespaces = ()

    def model_dump_query(self) -> str | None:
        return self.query


class RecommendationAnswers(CamelModel):
    scene: str = "general"
    scale: str = "medium"
    latency: str = "mid"
    budget: str = "mid"


class RecommendationEvidenceRequest(CamelModel):
    candidates: list[EvidenceCandidate] = []
    answers: RecommendationAnswers = RecommendationAnswers()
    force_refresh: bool = False


class KnowledgeRecord(CamelModel):
    segment_id: str
    document_id: str
    document_name: str
    content: str
    score: float
    collected_at: str | None = None


class EvidenceResult(CamelModel):
    model_id: str
    model_name: str
    query: str
    customer_id: str = ""
    records: list[KnowledgeRecord] = []
    theory: str = ""


class RecommendationEvidenceResponse(CamelModel):
    results: list[EvidenceResult] = []
