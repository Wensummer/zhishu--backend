"""配置答疑 chatbot 的请求体。

流式问答返回的是纯文本流(非 JSON),故只需定义请求 schema。
"""
from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    # 用户当前所在页面的简述(如「模型横评 — 对比各模型综合分/价格/延迟」),用于让回答贴合本页
    page: str | None = None
