"""证据链 schema(招牌主线)—— 镜像 lib/types 的 EvidenceFactor / EvidenceChain。"""
from app.schemas.base import CamelModel
from app.schemas.common import SourceRef


class EvidenceFactor(CamelModel):
    """评分公式中的一个分项。"""
    key: str                        # "capability" | "availability" | "costFactor" ...
    label: str                      # "能力分" / "可用率" / "成本系数"
    value: float                    # 分项数值(参与计算)
    display: str | None = None      # 预格式化展示串,如 "99.8%" / "×1.05"
    weight: float | None = None     # 权重(可选)
    source: SourceRef               # 该项数据来源与采集时间


class EvidenceChain(CamelModel):
    """一条推荐背后的完整可核验证据链。"""
    formula: str                    # "综合分 = 能力分 × 可用率 × 成本系数"
    score: float                    # 综合分
    factors: list[EvidenceFactor]
