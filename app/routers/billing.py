"""GET /billing → 计费明细列表(对齐前端 getBillingRecords)。"""
from fastapi import APIRouter, Query

from app.schemas.billing import BillingRecord
from app.data.billing import get_cend_billing_records, get_customer_billing_records

router = APIRouter()


@router.get("/billing", response_model=list[BillingRecord], response_model_exclude_none=True)
def billing(
    customer_id: str | None = Query(None, alias="customer_id"),
    model: str | None = None,
    api_key_name: str | None = Query(None, alias="api_key_name"),
) -> list[BillingRecord]:
    if customer_id:
        records = get_customer_billing_records(customer_id)
    else:
        records = get_cend_billing_records()

    if model:
        records = [r for r in records if r.model == model]
    if api_key_name:
        records = [r for r in records if r.api_key_name == api_key_name]

    return records
