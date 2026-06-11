"""GET /workbench → { customers, funnel, stats }(对齐前端 getWorkbench)。"""
from fastapi import APIRouter

from app.data.customers import CUSTOMERS, WORKBENCH_FUNNEL, WORKBENCH_STATS
from app.schemas.responses import WorkbenchData

router = APIRouter()


@router.get("/workbench", response_model=WorkbenchData, response_model_exclude_none=True)
def get_workbench() -> WorkbenchData:
    return WorkbenchData(
        customers=CUSTOMERS,
        funnel=WORKBENCH_FUNNEL,
        stats=WORKBENCH_STATS,
    )
