"""系统配置 数据访问。"""
import json
from app.database import get_connection


def get(key: str) -> str | None:
    conn = get_connection()
    r = conn.execute("SELECT value FROM system_config WHERE key=?", (key,)).fetchone()
    conn.close()
    return r["value"] if r else None


def set(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO system_config VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_model_bindings() -> dict[str, str]:
    val = get("system_model_bindings")
    return json.loads(val) if val else {}


def set_model_bindings(bindings: dict[str, str]) -> None:
    set("system_model_bindings", json.dumps(bindings, ensure_ascii=False))
