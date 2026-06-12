"""智枢后端 —— FastAPI 入口。

路由挂在根(无 /api 前缀),对齐前端 lib/api 的取数路径,
前端只需把 .env.local 的 NEXT_PUBLIC_USE_MOCK=false、NEXT_PUBLIC_API_BASE 指过来,代码零改动。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, announcements, billing, briefing, copilot, models, workbench

app = FastAPI(title="智枢 · 选型营销赋能平台 后端", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(announcements.router)
app.include_router(briefing.router)
app.include_router(workbench.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(copilot.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
