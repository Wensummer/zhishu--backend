"""通用 schema —— 镜像 lib/types 的 Trend / TimeSeriesPoint / SourceRef。"""
from typing import Literal

from app.schemas.base import CamelModel

Trend = Literal["up", "down", "flat"]


class TimeSeriesPoint(CamelModel):
    date: str                       # ISO date 或展示标签(如 "6月")
    value: float


class SourceRef(CamelModel):
    """数据来源与采集时间,挂在证据链每个分项上,支撑「可核验」。"""
    label: str                      # 如 "天翼云模型评测台 / 2026Q2 基准集"
    collected_at: str               # ISO date,采集时间
