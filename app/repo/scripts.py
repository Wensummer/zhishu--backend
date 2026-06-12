"""话术模板 数据访问。"""
from app.database import get_connection
from app.schemas.script import TalkScript


def get_all() -> list[TalkScript]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM talk_scripts").fetchall()
    conn.close()
    return [_row_to_script(r) for r in rows]


def get_by_stage(stage: str) -> list[TalkScript]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM talk_scripts WHERE stage=?", (stage,)).fetchall()
    conn.close()
    return [_row_to_script(r) for r in rows]


def upsert(script: TalkScript, stage: str) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO talk_scripts VALUES (?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             stage=excluded.stage, scene=excluded.scene, title=excluded.title,
             content=excluded.content, objection=excluded.objection""",
        (script.id, stage, script.scene, script.title, script.content, script.objection),
    )
    conn.commit()
    conn.close()


def _row_to_script(r) -> TalkScript:
    return TalkScript(
        id=r["id"], scene=r["scene"], title=r["title"],
        content=r["content"], objection=r["objection"],
    )
