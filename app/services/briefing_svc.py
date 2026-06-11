"""通话前简报组装。

- c-1024:原样还原 lib/demo/briefings.ts(保前端像素级一致,招牌客户)。
- 其他客户:走 scoring 引擎实时生成证据链(展示「评分→可核验证据链」主线)。
- 新客 / 未命中:回退 c-1024(对齐前端 getBriefingData 的 ?? 兜底)。

Phase 后期:推荐/话术来源切到 RAG + 天翼云模型,Briefing 形状不变。
"""
from app.data.customers import Customer, get_customer_by_id
from app.data.models import get_model_by_name
from app.schemas.briefing import Briefing, BriefingCustomer
from app.schemas.common import TimeSeriesPoint
from app.schemas.evidence import EvidenceChain, EvidenceFactor
from app.schemas.common import SourceRef
from app.schemas.recommendation import Recommendation
from app.schemas.script import TalkScript
from app.services.scoring import score_model

# ============ c-1024:demo 原样还原 ============
BRIEFING_C1024 = Briefing(
    customer=BriefingCustomer(
        id="c-1024", name="云帆智造科技", industry="智能制造", stage="renew",
        contact="周经理", current_model="通义千问-Max", current_plan="包年企业版",
        balance=38000, expire_at="2026-07-15", rate_limit_hits=12, error_count=3,
    ),
    usage=[
        TimeSeriesPoint(date="1月", value=182),
        TimeSeriesPoint(date="2月", value=196),
        TimeSeriesPoint(date="3月", value=175),
        TimeSeriesPoint(date="4月", value=224),
        TimeSeriesPoint(date="5月", value=268),
        TimeSeriesPoint(date="6月", value=312),
    ],
    recommendations=[
        Recommendation(
            id="r-1", customer_id="c-1024", type="renew",
            title="续约「通义千问-Max 包年企业版」并锁价",
            target_model_id="通义千问-Max", target_plan_id="包年企业版",
            reason="近 3 个月用量稳定上行、可用率 99.8%,当前型号最配其低延迟需求;包年锁价规避调价波动。",
            quote_range=(180000, 210000),
            evidence_chain=EvidenceChain(
                formula="综合分 = 能力分 × 可用率 × 成本系数", score=96.4,
                factors=[
                    EvidenceFactor(key="capability", label="能力分", value=92, display="92",
                                   source=SourceRef(label="天翼云模型评测台 / 2026Q2 基准集", collected_at="2026-05-30")),
                    EvidenceFactor(key="availability", label="可用率", value=0.998, display="99.8%",
                                   source=SourceRef(label="可用性监控 · 30 天滚动", collected_at="2026-06-08")),
                    EvidenceFactor(key="costFactor", label="成本系数", value=1.05, display="×1.05",
                                   source=SourceRef(label="定价知识库 · 包年折扣", collected_at="2026-06-01")),
                ],
            ),
        ),
        Recommendation(
            id="r-2", customer_id="c-1024", type="addon",
            title="加推「行业 MCP + 质检 Agent」增值包",
            target_model_id="通义千问-Max",
            reason="制造质检场景用量集中,叠加行业 MCP 可提升落地效果,属高价值增量,采纳率历史偏高。",
            quote_range=(36000, 52000),
            evidence_chain=EvidenceChain(
                formula="综合分 = 场景匹配 × 落地确定性 × 增值系数", score=88.2,
                factors=[
                    EvidenceFactor(key="fit", label="场景匹配", value=0.94, display="94%",
                                   source=SourceRef(label="客户用量画像 · 质检类调用占比", collected_at="2026-06-07")),
                    EvidenceFactor(key="certainty", label="落地确定性", value=0.92, display="92%",
                                   source=SourceRef(label="同行业落地案例库", collected_at="2026-05-20")),
                    EvidenceFactor(key="valueFactor", label="增值系数", value=1.02, display="×1.02",
                                   source=SourceRef(label="增值产品策略", collected_at="2026-06-01")),
                ],
            ),
        ),
    ],
    scripts=[
        TalkScript(id="s-1", scene="opening", title="续约切入",
                   content="周经理您好,这季度贵司调用量涨了约 40%,稳定性一直保持在 99.8%。续约前我把用量和选型给您过一遍,顺便锁个价,避免后面调价影响预算。"),
        TalkScript(id="s-2", scene="sellingPoint", title="合规 + 锁价",
                   content="我们是天翼云备案直连、渠道纯度可出证明,合同锁价 + 调价提前公示,发票对公正规 —— 这几点是中转站给不了的,贵司做预算和审计都省心。"),
        TalkScript(id="s-3", scene="objection", title="价格异议", objection="市面上有更便宜的中转",
                   content="便宜的多是逆向渠道、随时可能跳价或跑路,日志里还可能掺别的模型。我们贵在确定性:锁价、SLA、7×24 和数据不出境。需要的话我把证据链摊给您看每一分数据的来源。"),
    ],
    next_actions=[
        "本周内电话确认续约意向,主推包年锁价",
        "同步抛出质检 Agent 增值包,试探加推空间",
        "通话要点回流话术库 / 商机库,便于复盘",
    ],
)

CURATED: dict[str, Briefing] = {"c-1024": BRIEFING_C1024}


# ============ 其他客户:评分引擎实时生成 ============
_STAGE_TYPE = {
    "renew": "renew", "upgrade": "upgrade", "expand": "expand",
    "silent": "renew", "newLead": "upgrade",
}


def _generated_usage(monthly_spend: float) -> list[TimeSeriesPoint]:
    """按月消费推一条占位用量趋势(接真后换成实际调用量序列)。"""
    base = max(monthly_spend / 1000, 20)
    labels = ["1月", "2月", "3月", "4月", "5月", "6月"]
    factors = [0.8, 0.86, 0.92, 0.97, 1.05, 1.12]
    return [TimeSeriesPoint(date=l, value=round(base * f, 1)) for l, f in zip(labels, factors)]


def _build_recommendation(customer: Customer, chain: EvidenceChain) -> Recommendation:
    rtype = _STAGE_TYPE.get(customer.stage, "renew")
    model_name = customer.current_model_id or ""
    spend = customer.monthly_spend or 0
    title_map = {
        "renew": f"续约「{model_name} {customer.current_plan_id or ''}」并锁价",
        "upgrade": f"升级「{model_name}」至更高规格,匹配用量上行",
        "expand": f"为「{model_name}」扩容多部门并发额度",
    }
    return Recommendation(
        id=f"r-{customer.id}", customer_id=customer.id, type=rtype,
        title=title_map.get(rtype, f"为「{model_name}」续约锁价"),
        target_model_id=model_name, target_plan_id=customer.current_plan_id,
        reason=f"综合分 {chain.score}(能力 × 可用率 × 成本系数);结合 {customer.stage} 阶段画像,优先稳住盘子再谈增量。",
        quote_range=(round(spend * 11), round(spend * 13)),
        evidence_chain=chain,
    )


def _generated_scripts(customer: Customer) -> list[TalkScript]:
    return [
        TalkScript(id=f"s-{customer.id}-1", scene="opening", title="开场切入",
                   content=f"{customer.contact}您好,我把贵司近几个月的用量和选型给您过一遍,顺便看看有没有更省更稳的方案。"),
        TalkScript(id=f"s-{customer.id}-2", scene="sellingPoint", title="合规 + 锁价",
                   content="我们是天翼云备案直连、渠道纯度可出证明,合同锁价、发票对公正规,数据不出境——预算和审计都省心。"),
        TalkScript(id=f"s-{customer.id}-3", scene="objection", title="价格异议", objection="市面上有更便宜的中转",
                   content="便宜的多是逆向渠道,可能跳价、跑路、掺模型。我们贵在确定性,证据链每一分来源都能摊开给您看。"),
    ]


def _to_briefing_customer(customer: Customer) -> BriefingCustomer:
    return BriefingCustomer(
        id=customer.id, name=customer.name, industry=customer.industry,
        stage=customer.stage, contact=customer.contact or "对接人",
        current_model=customer.current_model_id or "",
        current_plan=customer.current_plan_id or "",
        balance=customer.balance or 0, expire_at=customer.expire_at or "",
        # 占位:接真后由 UsageRecord 回填
        rate_limit_hits=8, error_count=2,
    )


def get_briefing(customer_id: str) -> Briefing:
    if customer_id in CURATED:
        return CURATED[customer_id]

    customer = get_customer_by_id(customer_id)
    # 新客无用量/无当前模型,或未命中 → 回退招牌客户(对齐前端 ?? 兜底)
    if customer is None or customer.is_new or not customer.current_model_id:
        return BRIEFING_C1024

    model = get_model_by_name(customer.current_model_id)
    if model is None:
        return BRIEFING_C1024

    chain = score_model(model)
    return Briefing(
        customer=_to_briefing_customer(customer),
        usage=_generated_usage(customer.monthly_spend or 0),
        recommendations=[_build_recommendation(customer, chain)],
        scripts=_generated_scripts(customer),
        next_actions=[
            "本周内电话确认意向,主推合规 + 锁价",
            "把证据链来源摊给客户,强化可核验信任",
            "通话要点回流话术库 / 商机库,便于复盘",
        ],
    )
