"""配置答疑 chatbot —— 接 LLM(DeepSeek)流式问答。

任何角色、任意页面都能问;主答「平台是什么 + 大模型 API 怎么用」这类常见问题。
- 接地:用 SYSTEM_PROMPT 钉死平台事实(合规聚合、One Key、OpenAI 兼容接入、计费、合规),
  防跑偏/防瞎编价格规格。
- 可选 RAG:配了 dify_faq_dataset_id 就先检索技术/FAQ 库,把命中段落塞进 system,答得更准。
- 流式:逐字吐 token,前端边收边显示;失败由前端兜底到本地 FAQ。
"""
import json
import urllib.request
from collections.abc import Iterator

from app.config import settings
from app.integrations.dify import retrieve_knowledge
from app.services.prompts import get_prompt

DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def _build_messages(history: list[dict], page: str | None = None) -> list[dict]:
    """history 为 [{role, content}](role ∈ user/assistant)。最后一条用户问题做可选 RAG 检索。

    系统提示词从「答疑」能力位配置读取(管理员可在系统模型配置页改);未配置时用默认值。
    page:用户当前页面简述,有则注入,让回答贴合本页。
    """
    system = get_prompt("chatbot")
    if page:
        system += (
            f"\n\n【用户当前所在页面】{page}\n"
            "若用户的问题与本页相关,优先结合本页功能解答;无关则正常回答。"
        )
    last_user = next(
        (m["content"] for m in reversed(history) if m.get("role") == "user"), ""
    )
    if last_user and settings.dify_faq_dataset_id:
        passages = retrieve_knowledge(last_user, settings.dify_faq_dataset_id, top_k=3)
        if passages:
            refs = "\n".join(f"- {p[:400]}" for p in passages)
            system += f"\n\n【知识库检索(优先据此作答,与上面事实冲突时以此为准)】\n{refs}"
    return [{"role": "system", "content": system}, *history]


def stream_chat(history: list[dict], page: str | None = None) -> Iterator[str]:
    """流式问答:逐段 yield 文本增量。LLM 不可用时抛异常,由路由兜底。"""
    body = json.dumps(
        {
            "model": MODEL,
            "messages": _build_messages(history, page),
            "temperature": 0.5,
            "stream": True,
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                delta = json.loads(payload)["choices"][0]["delta"].get("content")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if delta:
                yield delta
