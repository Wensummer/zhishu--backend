"""演示用模型池(原样移植 lib/demo/models.ts)。

Phase 后期由 services 从天翼云已备案模型目录 + 评测台取数替换。
注:模型名为公开产品名;客户/企业名才需脱敏。
"""
from app.schemas.model import Model

MODELS: list[Model] = [
    Model(
        id="qwen-max", name="通义千问-Max", vendor="阿里云百炼",
        capability_tier="S", capability_score=94,
        price_input_per1k=0.04, price_output_per1k=0.12, cache_discount=0.4,
        ttft_ms=420, tpot_ms=28, availability=0.998, channel_purity=1,
        use_cases=["复杂推理", "长文档", "Agent"], filed=True,
    ),
    Model(
        id="qwen-plus", name="通义千问-Plus", vendor="阿里云百炼",
        capability_tier="A", capability_score=88,
        price_input_per1k=0.008, price_output_per1k=0.02, cache_discount=0.4,
        ttft_ms=360, tpot_ms=22, availability=0.997, channel_purity=1,
        use_cases=["通用对话", "高并发", "性价比"], filed=True,
    ),
    Model(
        id="ernie-4", name="文心一言-4.0", vendor="百度智能云",
        capability_tier="S", capability_score=92,
        price_input_per1k=0.03, price_output_per1k=0.09, cache_discount=0.3,
        ttft_ms=480, tpot_ms=30, availability=0.995, channel_purity=1,
        use_cases=["知识问答", "金融合规", "长文档"], filed=True,
    ),
    Model(
        id="deepseek-v3", name="DeepSeek-V3", vendor="深度求索",
        capability_tier="A", capability_score=90,
        price_input_per1k=0.002, price_output_per1k=0.008, cache_discount=0.5,
        ttft_ms=520, tpot_ms=26, availability=0.992, channel_purity=1,
        use_cases=["代码", "性价比", "通用对话"], filed=True,
    ),
    Model(
        id="deepseek-r1", name="DeepSeek-R1", vendor="深度求索",
        capability_tier="S", capability_score=93,
        price_input_per1k=0.004, price_output_per1k=0.016, cache_discount=0.5,
        ttft_ms=900, tpot_ms=34, availability=0.99, channel_purity=1,
        use_cases=["深度推理", "数学", "代码"], filed=True,
    ),
    Model(
        id="glm-4", name="智谱 GLM-4", vendor="智谱 AI",
        capability_tier="A", capability_score=87,
        price_input_per1k=0.05, price_output_per1k=0.05, cache_discount=0.3,
        ttft_ms=400, tpot_ms=24, availability=0.996, channel_purity=1,
        use_cases=["通用对话", "工具调用", "多模态"], filed=True,
    ),
    Model(
        id="moonshot-128k", name="Kimi-128K", vendor="月之暗面",
        capability_tier="A", capability_score=86,
        price_input_per1k=0.06, price_output_per1k=0.06, cache_discount=0.2,
        ttft_ms=560, tpot_ms=27, availability=0.994, channel_purity=1,
        use_cases=["超长上下文", "文档分析", "RAG"], filed=True,
    ),
    Model(
        id="baichuan-4", name="百川-4", vendor="百川智能",
        capability_tier="B", capability_score=82,
        price_input_per1k=0.01, price_output_per1k=0.03, cache_discount=0.25,
        ttft_ms=440, tpot_ms=25, availability=0.991, channel_purity=1,
        use_cases=["通用对话", "性价比"], filed=True,
    ),
]


def get_model_by_id(model_id: str) -> Model | None:
    return next((m for m in MODELS if m.id == model_id), None)


def get_model_by_name(name: str) -> Model | None:
    """按展示名查模型(客户记录里存的是模型名而非 id)。"""
    return next((m for m in MODELS if m.name == name), None)


def blended_price(m: Model) -> float:
    """模型加权混合价(元/千 token):输入 0.3 + 输出 0.7。移植 models.ts。"""
    return m.price_input_per1k * 0.3 + m.price_output_per1k * 0.7


def model_health(m: Model) -> str:
    """单模型健康档位:正常 / 波动 / 异常。移植 models.ts。"""
    if m.availability >= 0.995:
        return "ok"
    if m.availability >= 0.99:
        return "warn"
    return "down"


# ── 分任务能力分(选型库 #1 的"能力画像")────────────────────────────────
# 占位数据,接组员真实选型库后整表替换(来源:C-Eval / CMMLU / SuperCLUE / 自跑任务集)。
# 智能选型按"需求对应的任务维度"取分,而非笼统用一个总分。
ALL_TASKS = ["通用对话", "代码", "数学推理", "长文本", "中文理解", "Agent"]

TASK_SCORES: dict[str, dict[str, float]] = {
    "qwen-max":      {"通用对话": 93, "代码": 88, "数学推理": 90, "长文本": 94, "中文理解": 95, "Agent": 92},
    "qwen-plus":     {"通用对话": 88, "代码": 82, "数学推理": 80, "长文本": 85, "中文理解": 90, "Agent": 80},
    "ernie-4":       {"通用对话": 91, "代码": 80, "数学推理": 85, "长文本": 90, "中文理解": 94, "Agent": 82},
    "deepseek-v3":   {"通用对话": 87, "代码": 92, "数学推理": 88, "长文本": 84, "中文理解": 86, "Agent": 85},
    "deepseek-r1":   {"通用对话": 85, "代码": 93, "数学推理": 96, "长文本": 82, "中文理解": 84, "Agent": 84},
    "glm-4":         {"通用对话": 87, "代码": 83, "数学推理": 82, "长文本": 84, "中文理解": 88, "Agent": 88},
    "moonshot-128k": {"通用对话": 84, "代码": 78, "数学推理": 78, "长文本": 96, "中文理解": 87, "Agent": 80},
    "baichuan-4":    {"通用对话": 82, "代码": 75, "数学推理": 74, "长文本": 80, "中文理解": 85, "Agent": 72},
}


def task_score(m: Model, task: str) -> float:
    """取模型在某任务上的能力分;查不到则兜底用总分。"""
    return TASK_SCORES.get(m.id, {}).get(task, m.capability_score)


# ── 生命周期状态(选型库 #1 的"上下架/备案状态")────────────────────────
# 占位数据,接组员选型库后替换。active=在用 / deprecating=即将下线 / retired=已下线。
# 选型引擎据此跳过将下线/已下线的模型,从源头避免推一个快停的模型。
MODEL_STATUS: dict[str, str] = {
    "deepseek-r1": "deprecating",  # 知识库标注:DeepSeek-R1 即将 5.20 下线
}


def model_status(m: Model) -> str:
    return MODEL_STATUS.get(m.id, "active")
