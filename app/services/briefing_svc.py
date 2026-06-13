"""通话前简报组装。

- c-1024:原样还原 lib/demo/briefings.ts(保前端像素级一致,招牌客户)。
- 其他客户:走 scoring 引擎实时生成证据链(展示「评分→可核验证据链」主线)。
- 新客 / 未命中:回退 c-1024(对齐前端 getBriefingData 的 ?? 兜底)。

Phase 后期:推荐/话术来源切到 RAG + 天翼云模型,Briefing 形状不变。
"""
from app.repo import customers as customers_repo
from app.repo import models as models_repo
from app.schemas.briefing import Briefing, BriefingCustomer, TelecomProduct
from app.schemas.customer import Customer
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
    telecom_products=[
        TelecomProduct(id="tp-1", name="天翼云专线",
                       description="提供稳定低延迟的专属网络连接，保障数据传输质量",
                       category="云专线",
                       reason="制造企业对实时数据传输要求高，云专线可提升工厂与云端的连接稳定性",
                       estimated_price="2000~5000元/月"),
        TelecomProduct(id="tp-2", name="天翼云会议",
                       description="高清视频会议服务，支持多方协同与屏幕共享",
                       category="云会议",
                       reason="跨部门协同频繁，云会议可降低差旅成本、提升沟通效率",
                       estimated_price="299元/月起"),
        TelecomProduct(id="tp-3", name="天翼云安全·WAF",
                       description="Web应用防火墙，防御SQL注入、XSS等攻击",
                       category="云安全",
                       reason="制造企业MES等系统暴露面扩大，急需Web安全防护",
                       estimated_price="1500元/月"),
    ],
)

CURATED: dict[str, Briefing] = {"c-1024": BRIEFING_C1024}


# ============ 其他客户:评分引擎实时生成 ============
_STAGE_TYPE = {
    "renew": "renew", "upgrade": "upgrade", "expand": "expand",
    "silent": "renew", "newLead": "upgrade",
}

# 阶段化话术模板(对齐前端 scripts.ts)
_STAGE_SCRIPTS: dict[str, list[dict]] = {
    "renew": [
        {"scene": "opening", "title": "续约切入",
         "content": "{contact}您好,这季度贵司调用量涨了约 40%,稳定性一直保持在 99.8%。续约前我把用量和选型给您过一遍,顺便锁个价,避免后面调价影响预算。"},
        {"scene": "sellingPoint", "title": "合规 + 锁价",
         "content": "我们是天翼云备案直连、渠道纯度可出证明,合同锁价 + 调价提前公示,发票对公正规 —— 这几点是中转站给不了的,贵司做预算和审计都省心。"},
        {"scene": "objection", "title": "价格异议", "objection": "市面上有更便宜的中转",
         "content": "便宜的多是逆向渠道、随时可能跳价或跑路,日志里还可能掺别的模型。我们贵在确定性:锁价、SLA、7×24 和数据不出境。需要的话我把证据链摊给您看每一分数据的来源。"},
    ],
    "upgrade": [
        {"scene": "opening", "title": "用量升级诊断",
         "content": "{contact}您好,这几个月贵司调用量增长明显,当前套餐的配额可能快不够用了。我帮您看看是不是升级到更高规格更划算,避免超量后单价反而更贵。"},
        {"scene": "sellingPoint", "title": "高规格解锁能力",
         "content": "升级后不仅能获得更大并发配额,还能解锁高级能力——更低首 token 延迟、更高上下文窗口、优先调度权。这些对您业务体验的提升是立竿见影的,而且综合下来单位成本反而更低。"},
        {"scene": "objection", "title": "升级成本顾虑", "objection": "升级后成本更高了",
         "content": "短期看月费确实上浮了,但按当前增速,下季度您很可能就会触发现有限额,届时的超量费用比升级费高出 30% 以上。升级相当于提前锁一个更低的单价,跑得越多省得越多。"},
    ],
    "expand": [
        {"scene": "opening", "title": "多部门扩容方案",
         "content": "{contact}您好,我们看到贵司多个部门都在使用模型能力,当前共享额度可能不够分。我帮您设计一个多部门独立配额 + 统一管控的方案,每个部门用多少、花多少一目了然。"},
        {"scene": "sellingPoint", "title": "独立配额 + 统一管控",
         "content": "我们可以按部门设置独立额度、独立预算、独立调用链监控,但统一走您的企业账户结算。各部门互不影响,您随时能看到全盘的用量大盘和成本分布,审计对账一次过。"},
        {"scene": "objection", "title": "跨部门管理复杂度", "objection": "跨部门协调太麻烦,业务部门不好配合",
         "content": "理解您的顾虑,我们有一键模板方案:您确定总预算和各部门占比后,我们帮配好独立密钥和监控看板。每个部门拿到开箱即用的密钥,不用他们额外配合,您在后管平台就能看到全貌。"},
    ],
    "silent": [
        {"scene": "opening", "title": "用量下滑诊断",
         "content": "{contact}您好,看到贵司近两个月用量有所下滑,想跟您了解一下是不是当前的方案不太匹配了。我们可以一起看看问题出在哪,调整个更适合的方案。"},
        {"scene": "sellingPoint", "title": "轻量套餐 + 按量灵活",
         "content": "如果包年包月的压力太大,可以切到按量付费,用多少付多少,没有硬性最低消费。另外我们还有轻量入门套餐,月费不到原来一半,核心能力保留,等业务恢复再升回去也方便。"},
        {"scene": "objection", "title": "预算不足", "objection": "预算砍了,暂时不需要了",
         "content": "完全理解,预算收紧时我们都经历过。要不这样——我帮您开一个最低成本的保号方案,月付几十块保留账号和数据配置,这样等预算恢复时可以直接复用,不用重新对接。总比到时候重新接入省事得多。"},
    ],
    "newLead": [
        {"scene": "opening", "title": "行业切入建立信任",
         "content": "{contact}您好,我是天翼云的客户经理。了解到贵司在{industry}领域有 AI 能力需求,我们刚帮同行业的几家企业做了落地。方便的话我介绍一下我们能做什么、和市面上的方案有什么不同。"},
        {"scene": "sellingPoint", "title": "零风险试用 + POC 支持",
         "content": "我们为前期客户提供零风险的试用方案——首月充值金额全额抵扣次月费用,效果不满意可以退费。另外我们还提供免费 POC 环境,您可以先把真实场景跑一遍,看到效果再做决定。"},
        {"scene": "objection", "title": "已有供应商", "objection": "我们已经在用别家的了",
         "content": "理解,切换供应商确实要慎重。不过我们和别家最大的区别是:天翼云是直连备案模型,渠道纯度可出证明、可开正规增值税发票、数据不出境。您可以先拿一个非核心业务过来 POC,不用任何承诺,跑完对比一下延迟和稳定性,数据说话。"},
    ],
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
    stage = customer.stage
    templates = _STAGE_SCRIPTS.get(stage, _STAGE_SCRIPTS["newLead"])
    scripts: list[TalkScript] = []
    for i, t in enumerate(templates):
        content = t["content"].replace("{contact}", customer.contact or "对接人")
        if "{industry}" in content:
            content = content.replace("{industry}", customer.industry)
        scripts.append(TalkScript(
            id=f"s-{customer.id}-{i}",
            scene=t["scene"],
            title=t["title"],
            content=content,
            objection=t.get("objection"),
        ))
    return scripts


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

    customer = customers_repo.get_by_id(customer_id)
    # 新客无用量/无当前模型,或未命中 → 回退招牌客户(对齐前端 ?? 兜底)
    if customer is None or customer.is_new or not customer.current_model_id:
        return BRIEFING_C1024

    model = models_repo.get_by_name(customer.current_model_id)
    if model is None:
        return BRIEFING_C1024

    chain = score_model(model)
    return Briefing(
        customer=_to_briefing_customer(customer),
        usage=_generated_usage(customer.monthly_spend or 0),
        recommendations=[_build_recommendation(customer, chain)],
        scripts=_generated_scripts(customer),
        telecom_products=[],
        next_actions=[
            "本周内电话确认意向,主推合规 + 锁价",
            "把证据链来源摊给客户,强化可核验信任",
            "通话要点回流话术库 / 商机库,便于复盘",
        ],
    )
