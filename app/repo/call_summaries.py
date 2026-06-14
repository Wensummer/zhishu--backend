"""通话小结(沟通历史 / 跟进时间线)数据访问。

每条 = 一次通话结束后 LLM 生成的小结,挂在客户名下,供复盘与话术沉淀。
next_steps / scripts 以 JSON 数组存。
"""
import json

from app.database import get_connection


def insert(s: dict) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO call_summaries
           (id, customer_id, created_at, demand, intents, recommendation,
            temperature, next_steps, scripts, turns)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            s["id"],
            s["customer_id"],
            s["created_at"],
            s.get("demand", ""),
            s.get("intents", ""),
            s.get("recommendation", ""),
            s.get("temperature", ""),
            json.dumps(s.get("next_steps", []), ensure_ascii=False),
            json.dumps(s.get("scripts", []), ensure_ascii=False),
            json.dumps(s.get("turns", []), ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def add_customer_tag(customer_id: str, tag: str) -> None:
    """给客户 tags 追加一个标签(直接 SQL,绕开 Customer 整体反序列化,稳健抗 schema 漂移)。"""
    conn = get_connection()
    row = conn.execute(
        "SELECT tags FROM customers WHERE id=?", (customer_id,)
    ).fetchone()
    if row:
        tags = json.loads(row["tags"] or "[]")
        if tag and tag not in tags:
            tags.append(tag)
            conn.execute(
                "UPDATE customers SET tags=? WHERE id=?",
                (json.dumps(tags, ensure_ascii=False), customer_id),
            )
            conn.commit()
    conn.close()


def list_by_customer(customer_id: str) -> list[dict]:
    """该客户的全部小结,最新在前。"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM call_summaries WHERE customer_id=? ORDER BY created_at DESC",
        (customer_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "customer_id": r["customer_id"],
            "created_at": r["created_at"],
            "demand": r["demand"],
            "intents": r["intents"],
            "recommendation": r["recommendation"],
            "temperature": r["temperature"],
            "next_steps": json.loads(r["next_steps"] or "[]"),
            "scripts": json.loads(r["scripts"] or "[]"),
            "turns": json.loads(_col(r, "turns") or "[]"),
        }
        for r in rows
    ]


def _col(row, name: str) -> str:
    """安全取列(老库可能还没迁移出该列时返回空)。"""
    try:
        v = row[name]
        return v if v is not None else ""
    except (IndexError, KeyError):
        return ""
