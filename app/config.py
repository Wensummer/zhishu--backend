"""运行配置。

红线:真实 API Key 只从服务端环境变量读取,绝不出现在任何 response_model 里。
本阶段不依赖 pydantic-settings,纯 os.getenv,零额外安装即可跑通。
"""
import os


def _origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings:
    # 前端跨域白名单(逗号分隔可配多个)
    cors_origins: list[str] = _origins()
    # 天翼云已备案模型 key —— 仅服务端使用,详见 integrations/tianyi.py
    tianyi_api_key: str = os.getenv("TIANYI_API_KEY", "")
    tianyi_base_url: str = os.getenv("TIANYI_BASE_URL", "")


settings = Settings()
