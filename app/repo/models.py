"""模型池 + 套餐 数据访问。"""
import json
from app.database import get_connection
from app.schemas.model import Model, PricingPlan


def get_all() -> list[Model]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM models").fetchall()
    conn.close()
    return [_row_to_model(r) for r in rows]


def get_by_id(model_id: str) -> Model | None:
    conn = get_connection()
    r = conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
    conn.close()
    return _row_to_model(r) if r else None


def get_by_name(name: str) -> Model | None:
    conn = get_connection()
    r = conn.execute("SELECT * FROM models WHERE name=?", (name,)).fetchone()
    conn.close()
    return _row_to_model(r) if r else None


def upsert(model: Model) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO models VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             name=excluded.name, vendor=excluded.vendor,
             capability_tier=excluded.capability_tier, capability_score=excluded.capability_score,
             price_input_per1k=excluded.price_input_per1k, price_output_per1k=excluded.price_output_per1k,
             cache_discount=excluded.cache_discount, ttft_ms=excluded.ttft_ms,
             tpot_ms=excluded.tpot_ms, availability=excluded.availability,
             channel_purity=excluded.channel_purity, use_cases=excluded.use_cases,
             filed=excluded.filed""",
        (model.id, model.name, model.vendor, model.capability_tier,
         model.capability_score, model.price_input_per1k, model.price_output_per1k,
         model.cache_discount, model.ttft_ms, model.tpot_ms,
         model.availability, model.channel_purity,
         json.dumps(model.use_cases, ensure_ascii=False), int(model.filed)),
    )
    conn.commit()
    conn.close()


def delete(model_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM models WHERE id=?", (model_id,))
    conn.commit()
    conn.close()


def get_pricing_plans(model_id: str | None = None) -> list[PricingPlan]:
    conn = get_connection()
    if model_id:
        rows = conn.execute("SELECT * FROM pricing_plans WHERE model_id=?", (model_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM pricing_plans").fetchall()
    conn.close()
    return [_row_to_plan(r) for r in rows]


def _row_to_model(r) -> Model:
    return Model(
        id=r["id"], name=r["name"], vendor=r["vendor"],
        capability_tier=r["capability_tier"], capability_score=r["capability_score"],
        price_input_per1k=r["price_input_per1k"], price_output_per1k=r["price_output_per1k"],
        cache_discount=r["cache_discount"], ttft_ms=r["ttft_ms"], tpot_ms=r["tpot_ms"],
        availability=r["availability"], channel_purity=r["channel_purity"],
        use_cases=json.loads(r["use_cases"]), filed=bool(r["filed"]),
    )


def _row_to_plan(r) -> PricingPlan:
    return PricingPlan(
        id=r["id"], model_id=r["model_id"], name=r["name"], tier=r["tier"],
        billing_mode=r["billing_mode"], list_price=r["list_price"],
        negotiable_range=(r["negotiable_min"], r["negotiable_max"]),
        quota_tokens=r["quota_tokens"],
    )
