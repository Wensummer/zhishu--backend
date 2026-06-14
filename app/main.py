"""智枢后端 —— FastAPI 入口。

路由挂在根(无 /api 前缀),对齐前端 lib/api 的取数路径,
前端只需把 .env.local 的 NEXT_PUBLIC_USE_MOCK=false、NEXT_PUBLIC_API_BASE 指过来,代码零改动。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import admin, admin_data, admin_prompts, announcements, billing, briefing, chat, copilot, enterprise, models, workbench


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="智枢 · 选型营销赋能平台 后端", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(announcements.router)
app.include_router(briefing.router)
app.include_router(workbench.router)
app.include_router(admin.router)
app.include_router(admin_data.router)
app.include_router(billing.router)
app.include_router(copilot.router)
app.include_router(chat.router)
app.include_router(enterprise.router)
app.include_router(admin_prompts.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
