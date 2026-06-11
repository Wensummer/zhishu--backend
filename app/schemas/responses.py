"""组合响应信封 —— 镜像前端 lib/api 的 WorkbenchData / DashboardData。

(Briefing / CopilotScript 是更复杂的组合,各自单独成文件:briefing.py / session.py。)
"""
from app.schemas.base import CamelModel
from app.schemas.common import TimeSeriesPoint
from app.schemas.customer import Customer, FunnelStage, WorkbenchStat
from app.schemas.metric import DashboardStat, Metric


class WorkbenchData(CamelModel):
    customers: list[Customer]
    funnel: list[FunnelStage]
    stats: list[WorkbenchStat]


class DashboardData(CamelModel):
    stats: list[DashboardStat]
    efficiency_trend: list[TimeSeriesPoint]
    funnel: list[FunnelStage]
    trust_metrics: list[Metric]
