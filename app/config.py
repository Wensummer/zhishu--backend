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
    # 实时意图识别用的 LLM key(当前用 DeepSeek;生产可换天翼云已备案模型)
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    # Dify 知识库(话术生成检索话术库 #3;base url 与话术库 id 默认对齐前端,仅 key 需配)
    dify_api_base_url: str = os.getenv("DIFY_API_BASE_URL", "https://api.dify.ai/v1")
    dify_dataset_api_key: str = os.getenv("DIFY_DATASET_API_KEY", "")
    dify_script_dataset_id: str = os.getenv(
        "DIFY_SCRIPT_DATASET_ID", "366894d1-b153-4816-a3c1-29e2bea5dd0d"
    )
    # 配置答疑 chatbot 的技术/FAQ 知识库 id(配了才走 RAG;留空则纯 LLM 接地作答)
    dify_faq_dataset_id: str = os.getenv("DIFY_FAQ_DATASET_ID", "")


settings = Settings()
