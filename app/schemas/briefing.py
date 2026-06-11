"""通话前简报响应 schema —— 镜像 lib/demo/briefings.ts 的 BriefingCustomer / Briefing。

注:BriefingCustomer 是「拍平的客户视图」,把 UsageRecord 的 rate_limit_hits/error_count 合进来,
current_model / current_plan 存的是名称字符串(非 id)。
"""
from app.schemas.base import CamelModel
from app.schemas.common import TimeSeriesPoint
from app.schemas.customer import OpportunityStage
from app.schemas.recommendation import Recommendation
from app.schemas.script import TalkScript


class BriefingCustomer(CamelModel):
    id: str
    name: str
    industry: str
    stage: OpportunityStage
    contact: str
    current_model: str                  # 模型名称(非 id)
    current_plan: str
    balance: float
    expire_at: str
    rate_limit_hits: int
    error_count: int


class Briefing(CamelModel):
    customer: BriefingCustomer
    usage: list[TimeSeriesPoint]
    recommendations: list[Recommendation]
    scripts: list[TalkScript]
    next_actions: list[str]
