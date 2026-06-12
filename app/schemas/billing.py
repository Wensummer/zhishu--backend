"""计费明细 schema —— 对齐前端 BillingRecord。"""
from app.schemas.base import CamelModel


class BillingRecord(CamelModel):
    id: str
    date: str
    model: str
    model_id: str
    api_key_name: str
    tokens: int
    input_tokens: int
    output_tokens: int
    amount: float
    unit_price: float
    billing_mode: str
    customer_id: str | None = None
