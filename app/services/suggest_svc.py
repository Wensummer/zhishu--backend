"""「猜你想问」生成:按当前页面让 LLM 生成几个贴合的快捷问句。

前端打开 chatbot 时异步拉取,替换手写兜底问句。失败返回 [](前端保留手写),不拖累体验。
约束:只问平台真实功能、简短,防跑偏。
"""
import json
import urllib.request

from app.config import settings

DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

PROMPT = """你是「智枢」答疑助手的"猜你想问"生成器。智枢是中国电信旗下、依托天翼云已备案国产大模型的\
「合规大模型选型 + 营销赋能平台」(卖的是大模型 API 调用与套餐、智能选型等)。

用户当前在【{page}】页面。生成 3 个该页用户最可能点的快捷问题。

要求:
- 每个问句不超过 14 字,口语、像用户会顺手点的引导问题。
- 只针对平台真实功能(大模型选型 / API 接入 / 计费 / 报错 / 合规 / 证据链等),严禁编造不存在的功能或产品。
- 贴合本页;不要和本页无关。
- 只输出 JSON 字符串数组,形如 ["问题一","问题二","问题三"],不要任何额外文字或代码块标记。"""


def _parse(raw: str) -> list[str]:
    """容错解析:剥掉可能的 ```json 代码块包裹后取数组。"""
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s[:4].lower() == "json":
            s = s[4:]
    s = s.strip()
    arr = json.loads(s)
    if not isinstance(arr, list):
        return []
    return [str(q).strip() for q in arr if str(q).strip()][:4]


def suggest_questions(page: str) -> list[str]:
    """按页面生成快捷问句;page 为空或调用失败时返回 []。"""
    if not page or not settings.deepseek_api_key:
        return []
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT.format(page=page)}],
            "temperature": 0.7,
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
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = json.loads(resp.read())["choices"][0]["message"]["content"]
        return _parse(content)
    except Exception:
        return []
