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
