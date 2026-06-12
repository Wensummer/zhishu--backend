"""GET /admin/dashboard → { stats, efficiencyTrend, funnel, trustMetrics }(对齐前端 getDashboard)。"""
from fastapi import APIRouter

from app.repo import dashboard as repo
from app.schemas.responses import DashboardData

router = APIRouter()


@router.get("/admin/dashboard", response_model=DashboardData, response_model_exclude_none=True)
def get_dashboard() -> DashboardData:
    return DashboardData(
        stats=repo.get_all_dashboard_stats(),
        efficiency_trend=repo.get_efficiency_trend(),
        funnel=repo.get_admin_funnel(),
        trust_metrics=repo.get_trust_metrics(),
    )
