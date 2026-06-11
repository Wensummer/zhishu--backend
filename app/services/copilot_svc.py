"""通话 copilot 剧本组装 —— 原样还原 lib/demo/sessions.ts 的 SESSION_C1024。

未命中回退 c-1024(对齐前端 getCopilotScript 的 ?? 兜底)。
Phase 后期:转写来自实时 ASR,意图/推荐/话术映射来自天翼云模型 + RAG,CopilotScript 形状不变。
"""
from app.schemas.common import SourceRef
from app.schemas.evidence import EvidenceChain, EvidenceFactor
from app.schemas.recommendation import Recommendation
from app.schemas.script import TalkScript
from app.schemas.session import CopilotScript, IntentEvent, TranscriptLine

SESSION_C1024 = CopilotScript(
    customer_id="c-1024",
    customer_name="云帆智造科技",
    max_sec=34,
    transcript=[
        TranscriptLine(speaker="manager", text="周经理您好,这季度贵司调用量涨了约 40%,稳定性一直 99.8%,今天想和您过一下续约。", at_sec=0),
        TranscriptLine(speaker="customer", text="嗯,量确实涨了。不过最近财务在压成本,续约这块预算卡得紧。", at_sec=3),
        TranscriptLine(speaker="manager", text="理解,我们可以包年锁价,后面调价不影响您,预算更好做。", at_sec=7),
        TranscriptLine(speaker="customer", text="说到这个,我看市面上有些中转便宜不少,你们价格能不能再松松?", at_sec=11),
        TranscriptLine(speaker="manager", text="便宜的多是逆向渠道、随时跳价甚至跑路。我们是备案直连、渠道纯度可出证明,还能开正规发票。", at_sec=16),
        TranscriptLine(speaker="customer", text="发票和合规这块我们确实必须要。对了,我们质检那边想试试更智能的方案。", at_sec=21),
        TranscriptLine(speaker="manager", text="正好,我们有行业 MCP + 质检 Agent 的增值包,同行业落地效果不错,我回头给您发个方案。", at_sec=26),
        TranscriptLine(speaker="customer", text="可以,那续约我们走起,增值包也发我看看。", at_sec=31),
    ],
    intents=[
        IntentEvent(at_sec=3, level="medium", need_type="成本敏感", note="客户提到财务压成本,预算紧"),
        IntentEvent(at_sec=11, level="medium", need_type="价格异议", note="拿中转比价施压", triggers_script_id="s-3", triggers_recommendation_id="r-1"),
        IntentEvent(at_sec=21, level="high", need_type="质检新需求", note="主动抛出质检智能化诉求", triggers_recommendation_id="r-2"),
        IntentEvent(at_sec=31, level="high", need_type="成交信号", note="确认续约 + 索要增值包方案"),
    ],
    recommendations={
        "r-1": Recommendation(
            id="r-1", type="renew", title="包年锁价续约,化解预算顾虑",
            target_model_id="通义千问-Max", target_plan_id="包年企业版",
            reason="客户担心成本与调价 —— 包年锁价给预算确定性,正面回应。",
            quote_range=(180000, 210000),
            evidence_chain=EvidenceChain(
                formula="综合分 = 能力分 × 可用率 × 成本系数", score=96.4,
                factors=[
                    EvidenceFactor(key="capability", label="能力分", value=92, display="92",
                                   source=SourceRef(label="天翼云模型评测台", collected_at="2026-05-30")),
                    EvidenceFactor(key="availability", label="可用率", value=0.998, display="99.8%",
                                   source=SourceRef(label="可用性监控 · 30 天", collected_at="2026-06-08")),
                    EvidenceFactor(key="costFactor", label="成本系数", value=1.05, display="×1.05",
                                   source=SourceRef(label="定价知识库 · 包年", collected_at="2026-06-01")),
                ],
            ),
        ),
        "r-2": Recommendation(
            id="r-2", type="addon", title="加推质检 Agent 增值包",
            target_model_id="通义千问-Max",
            reason="客户主动提到质检场景 —— 顺势加推,采纳概率高。",
            quote_range=(36000, 52000),
            evidence_chain=EvidenceChain(
                formula="综合分 = 场景匹配 × 落地确定性 × 增值系数", score=88.2,
                factors=[
                    EvidenceFactor(key="fit", label="场景匹配", value=0.94, display="94%",
                                   source=SourceRef(label="客户用量画像", collected_at="2026-06-07")),
                    EvidenceFactor(key="certainty", label="落地确定性", value=0.92, display="92%",
                                   source=SourceRef(label="同行业案例库", collected_at="2026-05-20")),
                    EvidenceFactor(key="valueFactor", label="增值系数", value=1.02, display="×1.02",
                                   source=SourceRef(label="增值产品策略", collected_at="2026-06-01")),
                ],
            ),
        ),
    },
    scripts={
        "s-3": TalkScript(
            id="s-3", scene="objection", title="应对比价异议", objection="市面上有更便宜的中转",
            content="便宜多是逆向渠道、随时跳价或跑路,日志还可能掺别的模型。我们贵在确定性:锁价、SLA、7×24、数据不出境,证据链每项来源都能摊给您看。",
        ),
    },
    summary="客户确认续约「通义千问-Max 包年企业版」,接受包年锁价;对质检 Agent 增值包有明确兴趣,需补发方案。比价异议已用合规 + 锁价话术化解。",
)

SESSIONS: dict[str, CopilotScript] = {"c-1024": SESSION_C1024}


def get_copilot_script(customer_id: str) -> CopilotScript:
    """取某客户的通话剧本;未命中回退 c-1024(对齐前端 ?? 兜底)。"""
    return SESSIONS.get(customer_id, SESSION_C1024)
