"""统一选型评分引擎(纯函数)—— 忠实移植 lib/recommendation/score.ts。

简报、四问向导、横评三处共用同一套逻辑,产出可核验证据链。
Phase 后期数据来源切到天翼云评测台/监控/定价库(改 source 与 collected_at),公式与结构保持不变。
"""
from app.repo import models as models_repo
from app.schemas.evidence import EvidenceChain, EvidenceFactor
from app.schemas.common import SourceRef
from app.schemas.model import Model

SCORE_FORMULA = "综合分 = 能力分 × 可用率 × 成本系数"

# 成本系数基准混合价(元/千 token):比基准便宜则系数 > 1。
COST_REFERENCE = 0.06

# 占位采集时间(P2 写死;接真后由各数据源回填真实时间戳)。
COLLECTED = {
    "capability": "2026-05-30",
    "availability": "2026-06-08",
    "cost": "2026-06-01",
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def blended_price(model: Model) -> float:
    """模型加权混合价(元/千 token):输入 0.3 + 输出 0.7。移植 models.ts。"""
    return model.price_input_per1k * 0.3 + model.price_output_per1k * 0.7


def cost_factor(model: Model) -> float:
    """成本系数:越便宜系数越高,限制在 [0.85, 1.15],保留两位。"""
    raw = COST_REFERENCE / blended_price(model)
    return round(_clamp(raw, 0.85, 1.15), 2)


def score_model(model: Model) -> EvidenceChain:
    """根据模型指标计算综合分并返回可核验证据链。"""
    cf = cost_factor(model)

    factors = [
        EvidenceFactor(
            key="capability",
            label="能力分",
            value=model.capability_score,
            display=str(int(model.capability_score))
            if model.capability_score == int(model.capability_score)
            else str(model.capability_score),
            source=SourceRef(
                label="天翼云模型评测台 / 2026Q2 基准集",
                collected_at=COLLECTED["capability"],
            ),
        ),
        EvidenceFactor(
            key="availability",
            label="可用率",
            value=model.availability,
            display=f"{model.availability * 100:.1f}%",
            source=SourceRef(
                label="可用性监控 · 30 天滚动",
                collected_at=COLLECTED["availability"],
            ),
        ),
        EvidenceFactor(
            key="costFactor",
            label="成本系数",
            value=cf,
            display=f"×{cf:.2f}",
            source=SourceRef(
                label="定价知识库 · 混合价基准",
                collected_at=COLLECTED["cost"],
            ),
        ),
    ]

    score = round(model.capability_score * model.availability * cf, 1)

    return EvidenceChain(formula=SCORE_FORMULA, score=score, factors=factors)


def score_model_for_task(model: Model, task: str) -> EvidenceChain:
    """按「具体任务维度」算综合分(智能选型用)。

    与 score_model 同一公式,只是能力分取该任务的分(代码/数学/长文本…),
    而非笼统总分。这样推荐才对得上客户的真实需求,且证据链点明用的是哪个任务的评测分。
    """
    cap = task_score(model, task)
    cf = cost_factor(model)

    factors = [
        EvidenceFactor(
            key="capability",
            label=f"{task}能力分",
            value=cap,
            display=str(int(cap)) if cap == int(cap) else str(cap),
            source=SourceRef(
                label=f"选型评测台 · {task}任务集(C-Eval/SuperCLUE)",
                collected_at=COLLECTED["capability"],
            ),
        ),
        EvidenceFactor(
            key="availability",
            label="可用率",
            value=model.availability,
            display=f"{model.availability * 100:.1f}%",
            source=SourceRef(label="可用性监控 · 30 天滚动", collected_at=COLLECTED["availability"]),
        ),
        EvidenceFactor(
            key="costFactor",
            label="成本系数",
            value=cf,
            display=f"×{cf:.2f}",
            source=SourceRef(label="定价知识库 · 混合价基准", collected_at=COLLECTED["cost"]),
        ),
    ]
    score = round(cap * model.availability * cf, 1)
    return EvidenceChain(
        formula=f"综合分 = {task}能力 × 可用率 × 成本系数", score=score, factors=factors
    )
