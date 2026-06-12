"""管理大屏 + 计费明细 数据访问。"""
import json
from app.database import get_connection
from app.schemas.common import TimeSeriesPoint
from app.schemas.customer import FunnelStage
from app.schemas.metric import DashboardStat, Metric
from app.schemas.billing import BillingRecord


# ===== 管理大屏 =====

def get_efficiency_trend() -> list[TimeSeriesPoint]:
    conn = get_connection()
    rows = conn.execute("SELECT date, value FROM dashboard_efficiency ORDER BY rowid").fetchall()
    conn.close()
    return [TimeSeriesPoint(date=r["date"], value=r["value"]) for r in rows]


def get_admin_funnel() -> list[FunnelStage]:
    conn = get_connection()
    rows = conn.execute("SELECT label, value FROM dashboard_funnel ORDER BY rowid").fetchall()
    conn.close()
    return [FunnelStage(label=r["label"], value=r["value"]) for r in rows]


def get_trust_metrics() -> list[Metric]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM dashboard_trust_metrics").fetchall()
    conn.close()
    results = []
    for r in rows:
        m = Metric(key=r["key"], label=r["label"], value=r["value"], unit=r["unit"],
                   baseline=r["baseline"], target=r["target"])
        if r["series_json"]:
            m.series = [TimeSeriesPoint(**p) for p in json.loads(r["series_json"])]
        results.append(m)
    return results


def get_all_dashboard_stats() -> list[DashboardStat]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM dashboard_stats").fetchall()
    conn.close()
    return [
        DashboardStat(
            label=r["label"], value=r["value"], hint=r["hint"],
            trend=r["trend"], icon=r["icon"], series=json.loads(r["series_json"]),
        )
        for r in rows
    ]


def update_trust_metric(key: str, value: float, baseline: float | None = None, target: float | None = None) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE dashboard_trust_metrics SET value=?, baseline=COALESCE(?, baseline), target=COALESCE(?, target) WHERE key=?",
        (value, baseline, target, key),
    )
    conn.commit()
    conn.close()


# ===== 计费明细 =====

def get_billing_records(customer_id: str | None = None,
                        model: str | None = None,
                        api_key_name: str | None = None) -> list[BillingRecord]:
    conn = get_connection()
    where = []
    params = []
    if customer_id:
        where.append("customer_id=?")
        params.append(customer_id)
    if model:
        where.append("model=?")
        params.append(model)
    if api_key_name:
        where.append("api_key_name=?")
        params.append(api_key_name)

    sql = "SELECT * FROM billing_records"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row_to_billing(r) for r in rows]


def insert_billing_records(records: list[BillingRecord]) -> None:
    conn = get_connection()
    for r in records:
        conn.execute(
            """INSERT OR REPLACE INTO billing_records
               (id, date, model, model_id, api_key_name, tokens, input_tokens, output_tokens,
                amount, unit_price, billing_mode, customer_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r.id, r.date, r.model, r.model_id, r.api_key_name,
             r.tokens, r.input_tokens, r.output_tokens, r.amount,
             r.unit_price, r.billing_mode, r.customer_id or None),
        )
    conn.commit()
    conn.close()


def _row_to_billing(r) -> BillingRecord:
    return BillingRecord(
        id=r["id"], date=r["date"], model=r["model"], model_id=r["model_id"],
        api_key_name=r["api_key_name"], tokens=r["tokens"],
        input_tokens=r["input_tokens"], output_tokens=r["output_tokens"],
        amount=r["amount"], unit_price=r["unit_price"],
        billing_mode=r["billing_mode"],
        customer_id=r["customer_id"],
    )
