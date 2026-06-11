"""公告 / 告警 schema —— 镜像 lib/types 的 Announcement。"""
from typing import Literal

from app.schemas.base import CamelModel

AnnouncementKind = Literal["priceChange", "incident", "maintenance", "shelf"]


class Announcement(CamelModel):
    id: str
    kind: AnnouncementKind
    title: str
    body: str
    model_id: str | None = None
    published_at: str               # ISO date
    resolved_at: str | None = None  # 故障处理完成时间
