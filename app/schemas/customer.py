"""客户 / 用量 schema —— 镜像 lib/types 的 Customer / UsageRecord,
以及工作台用的 FunnelStage / WorkbenchStat(原在 lib/demo/customers.ts)。
"""
from typing import Literal

from app.schemas.base import CamelModel
from app.schemas.common import TimeSeriesPoint, Trend

OpportunityStage = Literal["renew", "upgrade", "expand", "silent", "newLead"]


class Customer(CamelModel):
    id: str
    name: str                           # 脱敏假企业名
    industry: str
    is_new: bool                        # 新客无用量数据
    current_model_id: str | None = None
    current_plan_id: str | None = None
    balance: float | None = None
    expire_at: str | None = None
    stage: OpportunityStage
    tags: list[str]
    owner_manager_id: str
    contact: str | None = None
    monthly_spend: float | None = None
    telecom_products: list[str] = []   # 其他电信业务推荐(名称列表)


class FunnelStage(CamelModel):
    label: str
    value: float


class WorkbenchStat(CamelModel):
    label: str
    value: str                          # 注:展示串,如 "32" / "68%"
    hint: str
    trend: Trend
    icon: Literal["users", "target", "adoption", "renew"]
