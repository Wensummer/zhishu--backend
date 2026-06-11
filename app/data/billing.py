"""演示用计费明细数据 —— 对齐前端 lib/demo/billing.ts。"""
import random
from datetime import datetime, timedelta
from app.schemas.billing import BillingRecord

API_KEYS_C_END = ["默认 Key", "个人 Key-01", "个人 Key-02"]
API_KEYS_ENTERPRISE: dict[str, list[str]] = {
    "c-1024": ["生产环境 Key", "测试环境 Key", "质检 Agent Key"],
    "c-1031": ["主 Key", "内容生产 Key"],
    "c-1042": ["核心交易 Key", "合规审计 Key", "数据分析 Key", "风控 Key"],
    "c-1055": ["通用 Key"],
    "c-2003": [],
}

MODELS = [
    "DeepSeek-V3", "DeepSeek-R1",
    "通义千问-Max", "通义千问-Plus", "通义千问-Turbo",
    "智谱 GLM-4", "智谱 GLM-4-Flash",
    "文心一言-4.0", "文心一言-3.5",
]


def _random_item(arr: list[str]) -> str:
    return arr[random.randint(0, len(arr) - 1)]


def _random_int(lo: int, hi: int) -> int:
    return random.randint(lo, hi)


def _generate_records(
    api_keys: list[str],
    day_count: int,
    token_scale: tuple[int, int] = (5000, 50000),
) -> list[BillingRecord]:
    if not api_keys:
        return []
    records: list[BillingRecord] = []
    now = datetime.now()
    for i in range(day_count):
        d = now - timedelta(days=i)
        model = _random_item(MODELS)
        inp = _random_int(token_scale[0], token_scale[1])
        out = _random_int(token_scale[0] // 2, token_scale[1] // 2)
        tokens = inp + out
        unit_price = round(random.uniform(0.01, 0.09), 4)
        amount = round((tokens / 1000) * unit_price, 2)
        records.append(BillingRecord(
            id=f"bill-{i}",
            date=d.strftime("%Y-%m-%d"),
            model=model,
            model_id=model,
            api_key_name=_random_item(api_keys),
            tokens=tokens,
            input_tokens=inp,
            output_tokens=out,
            amount=amount,
            unit_price=unit_price,
            billing_mode="payg",
        ))
    return records


_cached_cend: list[BillingRecord] | None = None


def get_cend_billing_records() -> list[BillingRecord]:
    global _cached_cend
    if _cached_cend is None:
        _cached_cend = _generate_records(API_KEYS_C_END, 30)
    return _cached_cend


def get_customer_billing_records(customer_id: str) -> list[BillingRecord]:
    keys = API_KEYS_ENTERPRISE.get(customer_id, [])
    day_count = 90 if customer_id == "c-1042" else 60
    return _generate_records(keys, day_count, token_scale=(20000, 200000))
