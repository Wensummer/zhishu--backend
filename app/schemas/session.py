"""通话会话 schema —— 镜像 lib/types 的 TranscriptLine / IntentEvent,
以及 copilot 剧本 CopilotScript(原在 lib/demo/sessions.ts)。

注:recommendations / scripts 是「以 id 为 key 的 dict」(Record<string, ...>),不是数组;
IntentEvent.triggers_recommendation_id / triggers_script_id 按 key 引用。
"""
from typing import Literal

from app.schemas.base import CamelModel
from app.schemas.recommendation import Recommendation
from app.schemas.script import TalkScript

IntentLevel = Literal["high", "medium", "low"]


class TranscriptLine(CamelModel):
    speaker: Literal["customer", "manager"]
    text: str
    at_sec: float                       # 进入时间(秒),驱动定时器


class IntentEvent(CamelModel):
    at_sec: float
    level: IntentLevel
    need_type: str                      # 需求类型
    note: str | None = None             # 弹屏提示语
    triggers_recommendation_id: str | None = None  # 触发动态推荐弹屏(按 key)
    triggers_script_id: str | None = None          # 触发动态话术弹屏(按 key)


class CopilotScript(CamelModel):
    customer_id: str
    customer_name: str
    max_sec: float
    transcript: list[TranscriptLine]
    intents: list[IntentEvent]
    recommendations: dict[str, Recommendation]     # ★ key 为 id,非数组
    scripts: dict[str, TalkScript]                 # ★ 同上
    summary: str
