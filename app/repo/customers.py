"""客户 + 工作台统计 数据访问。"""
import json
from app.database import get_connection
from app.schemas.customer import Customer


def get_all() -> list[Customer]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM customers").fetchall()
    conn.close()
    return [_row_to_customer(r) for r in rows]


def get_by_id(customer_id: str) -> Customer | None:
    conn = get_connection()
    r = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    conn.close()
    return _row_to_customer(r) if r else None


def upsert(customer: Customer) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             name=excluded.name, industry=excluded.industry,
             is_new=excluded.is_new, current_model_id=excluded.current_model_id,
             current_plan_id=excluded.current_plan_id, balance=excluded.balance,
             expire_at=excluded.expire_at, stage=excluded.stage,
             tags=excluded.tags, owner_manager_id=excluded.owner_manager_id,
             contact=excluded.contact, monthly_spend=excluded.monthly_spend""",
        (customer.id, customer.name, customer.industry, int(customer.is_new),
         customer.current_model_id, customer.current_plan_id,
         customer.balance, customer.expire_at, customer.stage,
         json.dumps(customer.tags, ensure_ascii=False),
         customer.owner_manager_id, customer.contact, customer.monthly_spend),
    )
    conn.commit()
    conn.close()


def delete(customer_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
    conn.commit()
    conn.close()


def _row_to_customer(r) -> Customer:
    return Customer(
        id=r["id"], name=r["name"], industry=r["industry"],
        is_new=bool(r["is_new"]),
        current_model_id=r["current_model_id"], current_plan_id=r["current_plan_id"],
        balance=r["balance"], expire_at=r["expire_at"], stage=r["stage"],
        tags=json.loads(r["tags"]),
        owner_manager_id=r["owner_manager_id"], contact=r["contact"],
        monthly_spend=r["monthly_spend"],
    )
