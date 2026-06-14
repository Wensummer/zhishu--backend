"""GET /enterprise/{customerId} → EnterpriseInfo(企查查信息)。

数据来源:customers 表的 enterprise_info_json 字段。
第三方对接(企查查 MCP)写入该字段后即生效。
"""
from fastapi import APIRouter, HTTPException

from app.repo import customers as customers_repo
from app.data.enterprise import get_enterprise_info as get_demo_enterprise
from app.schemas.enterprise import EnterpriseInfo

router = APIRouter()


@router.get(
    "/enterprise/{customer_id}",
    response_model=EnterpriseInfo,
    response_model_exclude_none=True,
)
def enterprise(customer_id: str) -> EnterpriseInfo:
    # 优先从 customers 表 enterprise_info_json 取数
    customer = customers_repo.get_by_id(customer_id)
    if customer and customer.enterprise_info:
        # enterprise_info 已是 dict,直接构造 EnterpriseInfo
        return EnterpriseInfo(**customer.enterprise_info)
    # 兜底: mock 数据
    info = get_demo_enterprise(customer_id)
    if info:
        return info
    raise HTTPException(status_code=404, detail="企业信息不存在")
