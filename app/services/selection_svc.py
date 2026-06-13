"""智能选型引擎 —— 把"客户需求"变成"带证据链的推荐"。

流程:需求(任务维度)→ 在备案模型池里按该任务算综合分 → 选最高 → 生成推荐卡。
公式与证据链来自 scoring.py(确定性,可核验),不是大模型编的。

接组员真实知识库后:
  - 选型库 #1 → 替换 data/models.py 的 TASK_SCORES;
  - 定价库 #2 → 替换下面的报价估算,改用真实套餐价 + 议价区间。
"""
from app.data.models import ALL_TASKS, MODELS, blended_price, model_status
from app.schemas.recommendation import Recommendation
from app.services.scoring import cost_factor, score_model_for_task

# 把客户口语里的任务说法,归一到选型库的能力维度。
TASK_ALIASES = {
    "编程": "代码", "写代码": "代码", "开发": "代码", "coding": "代码", "code": "代码",
    "推理": "数学推理", "数学": "数学推理", "做题": "数学推理",
    "文档": "长文本", "长文档": "长文本", "长文本处理": "长文本", "rag": "长文本",
    "客服": "通用对话", "对话": "通用对话", "聊天": "通用对话", "问答": "通用对话",
    "智能体": "Agent", "agent": "Agent", "工具调用": "Agent",
}

# 占位:假设的年用量(千 token),用于估报价区间。接定价库 #2 后用真实套餐价替换。
ASSUMED_ANNUAL_KTOKENS = 600_000


def _norm_task(task: str) -> str:
    """任务说法归一;落不到已知维度就按通用对话处理。"""
    t = (task or "").strip().lower()
    if task in ALL_TASKS:
        return task
    return TASK_ALIASES.get(t, TASK_ALIASES.get(task, "通用对话"))


def _selectable():
    """可推荐的候选:优先只在「在用」模型里选;若该状态下没有,退而求其次取非「已下线」的。
    从源头避免推一个即将下线/已下线的模型(知识库的风险检测作为第二道保险)。"""
    active = [m for m in MODELS if model_status(m) == "active"]
    if active:
        return active
    return [m for m in MODELS if model_status(m) != "retired"]


def recommend_for_need(need: dict) -> Recommendation | None:
    """根据结构化需求,从模型池选出最合适的模型并产出推荐(含证据链)。"""
    task = _norm_task(need.get("task", ""))

    # 在「可推荐」的模型里按该任务维度算综合分,选最高的(已排除即将/已下线)
    best = max(_selectable(), key=lambda m: score_model_for_task(m, task).score)
    chain = score_model_for_task(best, task)

    # 报价估算(占位,待接定价库 #2)
    annual = blended_price(best) * ASSUMED_ANNUAL_KTOKENS
    quote = (round(annual * 0.9), round(annual * 1.1))

    value_phrase = "性价比突出" if cost_factor(best) >= 1.0 else "能力优先、稳定性强"
    reason = (
        f"按「{task}」需求,在已备案模型池中综合分最高"
        f"({task}能力 × 可用率 × 成本系数),{value_phrase}。"
    )

    return Recommendation(
        id=f"live-{best.id}",
        type="switch",
        title=f"推荐选用 {best.name}",
        target_model_id=best.name,          # 契约:用模型名而非 id
        reason=reason,
        quote_range=quote,
        evidence_chain=chain,
    )
