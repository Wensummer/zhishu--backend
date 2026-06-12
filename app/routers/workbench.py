"""GET /workbench → { customers, funnel, stats }(对齐前端 getWorkbench)。"""
from fastapi import APIRouter

from app.repo import customers as repo
from app.schemas.customer import FunnelStage, WorkbenchStat
from app.schemas.responses import WorkbenchData

router = APIRouter()


@router.get("/workbench", response_model=WorkbenchData, response_model_exclude_none=True)
def get_workbench() -> WorkbenchData:
    return WorkbenchData(
        customers=repo.get_all(),
        funnel=[FunnelStage(label="线索", value=86),
                FunnelStage(label="商机", value=42),
                FunnelStage(label="报价", value=23),
                FunnelStage(label="成交", value=11)],
        stats=[WorkbenchStat(label="本月跟进客户", value="32", hint="较上月 +6", trend="up", icon="users"),
               WorkbenchStat(label="待跟进商机", value="14", hint="其中 5 个高意向", trend="flat", icon="target"),
               WorkbenchStat(label="推荐采纳率", value="68%", hint="较上月 +9%", trend="up", icon="adoption"),
               WorkbenchStat(label="续费率", value="91%", hint="较上月 +2%", trend="up", icon="renew")],
    )
