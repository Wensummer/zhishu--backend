"""公告 数据访问。"""
from app.database import get_connection
from app.schemas.announcement import Announcement


def get_all() -> list[Announcement]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM announcements ORDER BY published_at DESC").fetchall()
    conn.close()
    return [_row_to_announcement(r) for r in rows]


def get_by_id(announcement_id: str) -> Announcement | None:
    conn = get_connection()
    r = conn.execute("SELECT * FROM announcements WHERE id=?", (announcement_id,)).fetchone()
    conn.close()
    return _row_to_announcement(r) if r else None


def upsert(announcement: Announcement) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO announcements VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             kind=excluded.kind, title=excluded.title, body=excluded.body,
             model_id=excluded.model_id, published_at=excluded.published_at,
             resolved_at=excluded.resolved_at""",
        (announcement.id, announcement.kind, announcement.title,
         announcement.body, announcement.model_id,
         announcement.published_at, announcement.resolved_at),
    )
    conn.commit()
    conn.close()


def delete(announcement_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM announcements WHERE id=?", (announcement_id,))
    conn.commit()
    conn.close()


def _row_to_announcement(r) -> Announcement:
    return Announcement(
        id=r["id"], kind=r["kind"], title=r["title"], body=r["body"],
        model_id=r["model_id"], published_at=r["published_at"],
        resolved_at=r["resolved_at"],
    )
