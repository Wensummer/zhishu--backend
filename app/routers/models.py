"""GET /models → Model[](裸数组,对齐前端 getModels)。"""
from fastapi import APIRouter

from app.repo import models as repo
from app.schemas.model import Model

router = APIRouter()


@router.get("/models", response_model=list[Model], response_model_exclude_none=True)
def get_models() -> list[Model]:
    return repo.get_all()
