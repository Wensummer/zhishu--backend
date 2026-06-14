"""通话小结生成 —— 结束通话后用 LLM 把整通对话凝练成可跟进、可沉淀的结构化小结。

输入:整通转写文本(+ 客户名)。输出 JSON:
  demand(诉求/场景)、intents(关键意图与异议)、recommendation(推荐与报价)、
  temperature(成交温度:热/温/冷)、nextSteps(下一步跟进建议,含客情维护,带时机)、
  scripts(可沉淀话术片段)。
用途:帮销售跟进、回流商机、话术沉淀。失败抛异常,由路由兜底。
"""
import json
import urllib.request

from app.config import settings

DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

PROMPT = """你是中国电信客户经理的通话复盘助手。下面是一通销售与客户通话的转写。请凝练成一份\
**给销售跟进用**的结构化小结。我们卖的是天翼云已备案国产大模型的 API 调用与套餐、智能选型等\
(不是宽带/通话/流量),不要编造对话里没有的价格、套餐或事实。

只输出一个 JSON 对象,字段如下(全部用中文,简洁):
{
  "demand": "客户的核心诉求 / 使用场景(一两句)",
  "intents": "关键意图与异议(如:在意价格、担心合规、比价中…)",
  "recommendation": "本通推荐了什么 + 报价口径(对话没提就写'本通未明确推荐')",
  "temperature": "成交温度,只能是:热 / 温 / 冷",
  "nextSteps": ["下一步跟进动作,要具体、可执行、带时机,并兼顾客情维护(如'3天内发同行案例''节前送合规白皮书维护关系')", "2~4 条"],
  "scripts": ["本通值得沉淀、复用的话术片段(0~3 条,没有就空数组)"]
}
不要输出 JSON 以外的任何内容、不要代码块标记。

客户:{customer}
通话转写:
{transcript}"""


def _parse(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s[:4].lower() == "json":
            s = s[4:]
    return json.loads(s.strip())


def generate_summary(transcript: str, customer_name: str | None = None) -> dict:
    """调 LLM 生成小结 dict(camelCase 字段:demand/intents/recommendation/temperature/nextSteps/scripts)。"""
    prompt = PROMPT.replace("{customer}", customer_name or "(未知)").replace(
        "{transcript}", transcript[:6000]
    )
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        content = json.loads(resp.read())["choices"][0]["message"]["content"]
    data = _parse(content)

    # 规整:温度限定取值,数组字段兜底
    temp = str(data.get("temperature", "")).strip()
    if temp not in ("热", "温", "冷"):
        temp = "温"
    return {
        "demand": str(data.get("demand", "")).strip(),
        "intents": str(data.get("intents", "")).strip(),
        "recommendation": str(data.get("recommendation", "")).strip(),
        "temperature": temp,
        "next_steps": [str(x).strip() for x in data.get("nextSteps", []) if str(x).strip()][:4],
        "scripts": [str(x).strip() for x in data.get("scripts", []) if str(x).strip()][:3],
    }
