"""GET /announcements → Announcement[](裸数组,对齐前端 getAnnouncements)。"""
from fastapi import APIRouter

from app.repo import announcements as repo
from app.schemas.announcement import Announcement

router = APIRouter()


@router.get(
    "/announcements",
    response_model=list[Announcement],
    response_model_exclude_none=True,
)
def get_announcements() -> list[Announcement]:
    return repo.get_all()
