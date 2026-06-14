"""通话小结(沟通历史)契约。

CallSummary 出口 camelCase(customerId/createdAt/nextSteps…)。
请求体同样走 CamelModel,前端发 camelCase 即可。
"""
from app.schemas.base import CamelModel


class CallTurn(CamelModel):
    """一轮对话:客户说的话 + 当轮意图/推荐/给销售的话术。"""
    customer_said: str
    need_type: str = ""
    recommendation: str = ""
    script: str = ""


class CallSummary(CamelModel):
    id: str | None = None
    customer_id: str
    created_at: str
    demand: str = ""
    intents: str = ""
    recommendation: str = ""
    temperature: str = ""  # 热 / 温 / 冷
    next_steps: list[str] = []
    scripts: list[str] = []
    turns: list[CallTurn] = []


class GenerateSummaryRequest(CamelModel):
    transcript: str
    customer_id: str
    customer_name: str | None = None


class SaveSummaryRequest(CamelModel):
    customer_id: str
    created_at: str | None = None
    demand: str = ""
    intents: str = ""
    recommendation: str = ""
    temperature: str = ""
    next_steps: list[str] = []
    scripts: list[str] = []
    turns: list[CallTurn] = []
