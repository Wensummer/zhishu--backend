"""推荐选型依据知识库检索路由 —— POST /recommendation/evidence。"""
from fastapi import APIRouter

from app.schemas.recommendation_evidence import (
    RecommendationEvidenceRequest,
    RecommendationEvidenceResponse,
)
from app.services.recommendation_evidence_svc import get_recommendation_evidence

router = APIRouter()


@router.post(
    "/recommendation/evidence",
    response_model=RecommendationEvidenceResponse,
    response_model_exclude_none=True,
)
def recommendation_evidence(
    req: RecommendationEvidenceRequest,
) -> RecommendationEvidenceResponse:
    """为候选模型列表检索选型依据知识库,返回每个模型的知识支撑。"""
    return get_recommendation_evidence(req)
