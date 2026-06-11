"""指标 schema —— 镜像 lib/types 的 Metric,以及大屏 DashboardStat(原在 lib/demo/metrics.ts)。"""
from typing import Literal

from app.schemas.base import CamelModel
from app.schemas.common import TimeSeriesPoint, Trend


class Metric(CamelModel):
    key: str                            # "renewRate" | "adoptionRate" ...
    label: str
    value: float
    unit: str | None = None
    baseline: float | None = None       # 现状基线(对比用)
    target: float | None = None         # 目标值
    trend: Trend | None = None
    series: list[TimeSeriesPoint] | None = None


class DashboardStat(CamelModel):
    label: str
    value: str                          # 展示串,如 "31" / "91%"
    hint: str
    trend: Trend
    icon: Literal["efficiency", "renew", "adoption", "complaint"]
    series: list[float]                 # 注:裸数字数组(非 TimeSeriesPoint)
