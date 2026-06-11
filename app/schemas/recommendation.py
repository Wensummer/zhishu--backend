"""推荐 schema —— 镜像 lib/types 的 Recommendation。

招牌主线:每条推荐必须带 evidence_chain(评分公式分解 + 分项数值 + 各项数据来源/采集时间)。
"""
from typing import Literal

from app.schemas.base import CamelModel
from app.schemas.evidence import EvidenceChain

RecommendationType = Literal["renew", "upgrade", "expand", "switch", "addon"]


class Recommendation(CamelModel):
    id: str
    customer_id: str | None = None      # 向导场景可空
    type: RecommendationType
    title: str                          # 一句话主张
    target_model_id: str
    target_plan_id: str | None = None
    reason: str                         # 更省 / 更稳 / 更配场景
    quote_range: tuple[float, float]    # 报价区间 → JSON [a, b]
    evidence_chain: EvidenceChain       # ★ 可核验证据链
