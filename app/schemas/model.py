"""模型 / 套餐 schema —— 镜像 lib/types 的 Model / PricingPlan。"""
from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel

CapabilityTier = Literal["S", "A", "B", "C"]
BillingMode = Literal["payg", "package"]


class Model(CamelModel):
    id: str
    name: str                       # 公开产品名(模型名无需脱敏,客户/企业名才脱敏)
    vendor: str                     # 备案厂商
    capability_tier: CapabilityTier
    capability_score: float         # 0~100
    # to_camel 会把 per1k 误转成 per1K(大写),显式 alias 锁死小写 k 对齐前端契约
    price_input_per1k: float = Field(alias="priceInputPer1k")   # 输入 token 单价(元/千 token)
    price_output_per1k: float = Field(alias="priceOutputPer1k")  # 输出 token 单价(元/千 token)
    cache_discount: float           # 缓存折扣 0~1
    ttft_ms: float                  # 首 token 延迟(毫秒)
    tpot_ms: float                  # 单 token 输出耗时(毫秒)
    availability: float             # 可用率 0~1
    channel_purity: float           # 渠道纯度 0~1(差异化卖点)
    use_cases: list[str]
    filed: bool                     # 是否已备案


class PricingPlan(CamelModel):
    id: str
    model_id: str
    name: str
    tier: Literal["toB", "toC"]
    billing_mode: BillingMode
    list_price: float
    negotiable_range: tuple[float, float]
    quota_tokens: int | None = None
