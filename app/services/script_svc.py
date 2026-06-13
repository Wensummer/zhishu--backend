"""给销售的话术生成 —— 知识库(话术库 #3)+ LLM 结合。

流程:推荐产出后 → 按场景去话术库检索模板 → 把【模板 + 客户原话 + 推荐】喂 DeepSeek
     → 生成一段销售能照着说的话术 → 填进返回的 script。

话术库检索的是"骨架/风格",LLM 负责贴合当下对话、填进推荐的模型与数字。
"""
import json
import urllib.request

from app.config import settings
from app.integrations.dify import retrieve_knowledge
from app.schemas.script import TalkScript

DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# 产品背景:钉死话术不跑偏(卖的是大模型 API,不是宽带/通话)
PRODUCT_CONTEXT = (
    "我们是中国电信旗下的「合规国产大模型选型 + 营销赋能平台」:卖的是天翼云已备案的"
    "国产大模型(通义千问、DeepSeek、文心、智谱等)的 API 调用与套餐(按量 / 包年),"
    "外加智能选型、Agent 等增值服务。核心卖点:一个 key 调全部主流模型、合规备案、"
    "渠道纯度可审计、SLA 保障、央企背书。"
)

# 意图 → 话术场景(对齐前端 script-evidence 的 scene)
def _scene_for(need_type: str) -> str:
    return {
        "价格异议": "objection",
        "成本敏感": "pricing",
        "成交信号": "renewal",
        "质量顾虑": "objection",
        "犹豫拖延": "objection",
    }.get(need_type, "sellingPoint")  # 新需求/选型默认走卖点话术


# 场景 → 话术库检索关键词(对齐前端 SCENE_QUERIES)
_SCENE_QUERY = {
    "opening": "客户经理开场话术 建立信任",
    "sellingPoint": "产品卖点 合规 一个key调多模型 智能选型 SLA 央企背书 中立聚合",
    "objection": "客户异议处理 价格异议 比价应对 合同顾虑 服务保障",
    "pricing": "议价策略 报价技巧 锁价方案",
    "renewal": "续费话术 续约技巧 留存 灵活条款",
}

# 场景 → 无模型推荐时的话术标题
_SCENE_TITLE = {
    "opening": "开场",
    "sellingPoint": "价值主张",
    "objection": "异议应对",
    "pricing": "议价应对",
    "renewal": "续费推进",
}


def _call_deepseek(prompt: str) -> str:
    body = json.dumps(
        {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.6}
    ).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


def generate_sales_script(
    text: str,
    context: str | None,
    need_type: str | None,
    note: str | None = None,
    target_model_id: str | None = None,
    reason: str | None = None,
    score: float = 0,
) -> TalkScript | None:
    """每轮客户发言后,基于话术库 + 客户原话(+ 可选的模型推荐)生成给销售的话术。

    有模型推荐 → 话术围绕该模型;无推荐(纯异议/顾虑)→ 针对客户当前顾虑应对。失败返回 None。
    """
    scene = _scene_for(need_type or "")
    passages = retrieve_knowledge(
        _SCENE_QUERY.get(scene, "销售话术"), settings.dify_script_dataset_id, top_k=3
    )
    refs = "\n".join(f"- {p[:300]}" for p in passages) or "(话术库暂无命中,凭对话生成)"

    if target_model_id:
        rec_part = f"推荐 {target_model_id};理由:{reason};综合分 {score}"
        title = f"推荐 {target_model_id} · 给销售的话术"
    else:
        rec_part = "(本轮无新模型推荐,针对客户当前的异议/顾虑应对即可)"
        title = f"{_SCENE_TITLE.get(scene, '应对')} · 给销售的话术"

    intent_part = (need_type or "") + (f"({note})" if note else "")

    prompt = f"""你是中国电信客户经理的实时话术助手。结合【客户刚说的话】,生成一段销售能**当场照着对客户说**的话术。

【产品背景(务必记牢)】{PRODUCT_CONTEXT}

【硬性要求】
1. 只围绕"大模型 API / 选型套餐"展开;**严禁**出现宽带、通话时长、流量、办公等与本产品无关的东西。
2. **不准编造**任何价格、套餐名、模型分数——只能引用【系统推荐】里给的真实数字;没有就别提具体数(也不要出现"XX元"这种占位)。
3. 若客户想要推荐/选型、但**没说清使用场景**(写代码 / 客服 / 长文档 / 数据分析 等)或规模、预算,**不要瞎推**——而是引导销售**反问客户的使用场景**,以便后续精准选型。
4. 口语、自然、专业;40~120字;只输出话术正文,不要解释、不加引号或前缀。

【客户刚说的话】{text}
{f'【最近对话】{context}' if context else ''}
【客户当前意图】{intent_part}
【系统推荐】{rec_part}
【话术库参考】
{refs}"""

    try:
        content = _call_deepseek(prompt)
    except Exception:
        return None
    if not content:
        return None

    return TalkScript(
        id=f"live-script-{target_model_id or scene}",
        scene=scene,
        title=title,
        content=content,
    )
