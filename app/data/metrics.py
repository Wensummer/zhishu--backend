"""演示用管理侧大屏数据(原样移植 lib/demo/metrics.ts)。

Phase 后期由 service 从监控/运营后台聚合取数替换。
"""
from app.schemas.common import TimeSeriesPoint
from app.schemas.customer import FunnelStage
from app.schemas.metric import DashboardStat, Metric

EFFICIENCY_TREND: list[TimeSeriesPoint] = [
    TimeSeriesPoint(date="1月", value=18),
    TimeSeriesPoint(date="2月", value=19),
    TimeSeriesPoint(date="3月", value=21),
    TimeSeriesPoint(date="4月", value=24),
    TimeSeriesPoint(date="5月", value=27),
    TimeSeriesPoint(date="6月", value=31),
]

ADMIN_FUNNEL: list[FunnelStage] = [
    FunnelStage(label="线索", value=320),
    FunnelStage(label="商机", value=168),
    FunnelStage(label="报价", value=92),
    FunnelStage(label="成交", value=47),
]

# 信任工程相关指标:现状 vs 目标。
TRUST_METRICS: list[Metric] = [
    Metric(key="renewRate", label="续费率", value=0.91, baseline=0.82, target=0.93, unit="%"),
    Metric(key="expandRate", label="扩容率", value=0.34, baseline=0.21, target=0.4, unit="%"),
    Metric(key="adoptionRate", label="推荐采纳率", value=0.68, baseline=0.45, target=0.75, unit="%"),
    Metric(key="complaintRate", label="选型相关客诉率", value=0.03, baseline=0.08, target=0.02, unit="%"),
]

DASHBOARD_STATS: list[DashboardStat] = [
    DashboardStat(label="客户经理人效(单人月签约)", value="31", hint="较基线 +13", trend="up", icon="efficiency", series=[18, 19, 21, 24, 27, 31]),
    DashboardStat(label="续费率", value="91%", hint="目标 93%", trend="up", icon="renew", series=[82, 85, 86, 88, 90, 91]),
    DashboardStat(label="推荐采纳率", value="68%", hint="较基线 +23%", trend="up", icon="adoption", series=[45, 50, 55, 60, 64, 68]),
    DashboardStat(label="选型相关客诉率", value="3%", hint="较基线 -5%(越低越好)", trend="down", icon="complaint", series=[8, 7, 6, 5, 4, 3]),
]
