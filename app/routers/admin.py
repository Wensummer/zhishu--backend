"""GET /admin/dashboard → { stats, efficiencyTrend, funnel, trustMetrics }(对齐前端 getDashboard)。"""
from fastapi import APIRouter

from app.data.metrics import (
    ADMIN_FUNNEL,
    DASHBOARD_STATS,
    EFFICIENCY_TREND,
    TRUST_METRICS,
)
from app.schemas.responses import DashboardData

router = APIRouter()


@router.get("/admin/dashboard", response_model=DashboardData, response_model_exclude_none=True)
def get_dashboard() -> DashboardData:
    return DashboardData(
        stats=DASHBOARD_STATS,
        efficiency_trend=EFFICIENCY_TREND,
        funnel=ADMIN_FUNNEL,
        trust_metrics=TRUST_METRICS,
    )
