"""实时意图识别 + 推荐触发。

ASR 在前端浏览器做(Web Speech API);本服务只负责「文本 → 意图 → 触发推荐/话术」。
意图识别走 DeepSeek(OpenAI 兼容接口)。生产可换天翼云已备案模型,函数签名不变。

经命令行 spike(experiments/voice/)验证:能区分价格异议/成交信号/无明显意图,
吃一整段夹闲聊的话、结合上下文判断,闲聊不误触发。
"""
import json
import urllib.request

from app.config import settings
from app.schemas.recommendation import Recommendation
from app.schemas.script import TalkScript
from app.schemas.session import IntentEvent
from app.services.copilot_svc import SESSION_C1024
from app.services.selection_svc import recommend_for_need

DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

SYSTEM_PROMPT = """你是销售通话的实时意图识别助手。客户会说一整段话(可能夹杂闲聊、口头禅、题外话),你要识别其中的核心商机意图。

规则:
1. 忽略闲聊/题外话/寒暄(天气、球赛、客套),只抓商机信号。
2. 一段话里若有多个意图,返回最主要、最该让销售立刻行动的那个。
3. 没有明确商机信号时,needType 返回"无明显意图",confidence 给低分。
4. 结合上下文判断:比如销售刚报完价、客户说"有点高",就是价格异议。

needType 只能从这些里选:价格异议、成本敏感、新需求、成交信号、质量顾虑、犹豫拖延、无明显意图。
level 是成交意向高低 high/medium/low。confidence 是把握程度 0~1。

若客户表达了具体的「选型/采购需求」(要买、或要用模型做某类任务),额外给出 need 对象:
{"task":"任务类型","scale":"规模描述,如 100人/高频","priceSensitive":true 或 false};
没有具体选型需求时 need 设为 null。
task 只能从这些里选:通用对话、代码、数学推理、长文本、中文理解、Agent。

只输出一个 JSON,不要解释、不要 markdown:
{"level":"...","needType":"...","note":"给销售的一句话提示","confidence":0.x,"need":{...} 或 null}"""

FEW_SHOT = [
    ("【本轮客户发言】哎今天天气真不错,你那边下雨了吗哈哈",
     '{"level":"low","needType":"无明显意图","note":"纯闲聊,无需弹屏","confidence":0.95}'),
    ("【本轮客户发言】对了昨天那新闻看了没。行说正事,你们这价格比别家贵不少啊",
     '{"level":"medium","needType":"价格异议","note":"客户拿别家比价,强调价值与合规差异,别急着降价","confidence":0.85}'),
    ("【最近对话】销售: 这个质检增值包同行业落地效果不错\n【本轮客户发言】嗯,那你把方案发我看看",
     '{"level":"high","needType":"成交信号","note":"客户主动索要方案,推进度高,尽快发送并跟进","confidence":0.9,"need":null}'),
    ("【本轮客户发言】我们大概一百人的团队,主要拿来做 AI 编程写代码,想要性价比高一点的",
     '{"level":"high","needType":"新需求","note":"明确选型需求:代码场景+性价比,按代码任务推荐","confidence":0.9,"need":{"task":"代码","scale":"约100人","priceSensitive":true}}'),
]

_LEVELS = {"high", "medium", "low"}
# 复用 c-1024 简报里已成形的推荐/话术(含完整证据链)做触发目标
_RECS = SESSION_C1024.recommendations   # r-1 包年锁价续约 / r-2 质检增值包


def _call_llm(text: str, context: str | None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_in, assistant_out in FEW_SHOT:
        messages.append({"role": "user", "content": user_in})
        messages.append({"role": "assistant", "content": assistant_out})
    content = (f"【最近对话】{context}\n" if context else "") + f"【本轮客户发言】{text}"
    messages.append({"role": "user", "content": content})

    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.2}).encode("utf-8")
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


def _parse(raw: str) -> dict:
    """容错解析 LLM 输出的 JSON(可能裹着 markdown 代码块)。"""
    s = raw[raw.find("{") : raw.rfind("}") + 1]
    return json.loads(s)


def analyze(
    text: str, context: str | None = None
) -> tuple[IntentEvent, Recommendation | None, TalkScript | None, dict | None]:
    """文本 → 意图 + 触发的推荐/话术 + 抽出的结构化需求(供前端查 Dify)。"""
    data = _parse(_call_llm(text, context))
    level = data.get("level") if data.get("level") in _LEVELS else "medium"
    need_type = data.get("needType", "无明显意图")
    intent = IntentEvent(at_sec=0, level=level, need_type=need_type, note=data.get("note"))

    rec: Recommendation | None = None

    need_profile = data.get("need")
    if isinstance(need_profile, dict) and need_profile.get("task"):
        # ★ 有具体选型需求 → 跑真选型引擎,按任务维度算出对得上的推荐(含真实证据链)
        rec = recommend_for_need(need_profile)
    elif need_type in ("价格异议", "成本敏感"):
        rec = _RECS.get("r-1")           # 包年锁价续约,正面回应预算/价格顾虑
    elif need_type == "质量顾虑":
        rec = _RECS.get("r-2")           # 质检增值包(仅当客户确实提到质量/质检时)

    # 话术改为异步生成(前端拿到推荐后调 POST /copilot/script),analyze 保持快速响应
    need = need_profile if isinstance(need_profile, dict) else None
    return intent, rec, None, need
