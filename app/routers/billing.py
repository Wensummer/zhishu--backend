"""GET /billing → 计费明细列表(对齐前端 getBillingRecords)。"""
from fastapi import APIRouter, Query

from app.schemas.billing import BillingRecord
from app.repo import dashboard as repo

router = APIRouter()


@router.get("/billing", response_model=list[BillingRecord], response_model_exclude_none=True)
def billing(
    customer_id: str | None = Query(None, alias="customer_id"),
    model: str | None = None,
    api_key_name: str | None = Query(None, alias="api_key_name"),
) -> list[BillingRecord]:
    return repo.get_billing_records(
        customer_id=customer_id, model=model, api_key_name=api_key_name
    )
