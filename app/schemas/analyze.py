"""实时通话分析 schema —— POST /copilot/analyze 的请求/响应。

浏览器(Web Speech)转写出一句客户的话 → 送到这里 → 返回意图 + 触发的推荐/话术。
转写在前端做,后端只管"文本 → 意图 → 推荐触发"。
"""
from app.schemas.base import CamelModel
from app.schemas.recommendation import Recommendation
from app.schemas.script import TalkScript
from app.schemas.session import IntentEvent


class AnalyzeRequest(CamelModel):
    text: str                       # 客户这一轮说的话(已转写)
    context: str | None = None      # 最近几轮对话(可选,提升准确率)


class AnalyzeResponse(CamelModel):
    intent: IntentEvent                          # 识别出的意图
    recommendation: Recommendation | None = None  # 命中商机才有
    script: TalkScript | None = None              # 话术已改异步(见 ScriptRequest),analyze 不再返回
    need: dict | None = None                      # 抽出的结构化需求(task/scale/priceSensitive),供前端查 Dify 场景


class ScriptRequest(CamelModel):
    """POST /copilot/script —— 每轮客户发言后,前端异步来取"给销售的话术"。"""
    text: str                            # 客户这一轮说的话
    context: str | None = None           # 最近几轮对话
    need_type: str | None = None         # 意图类型(决定话术场景)
    note: str | None = None              # 意图提示(客户当前的具体顾虑)
    target_model_id: str | None = None   # 推荐的模型名(可空:纯异议应对时无新模型)
    reason: str | None = None            # 推荐理由
    score: float = 0                     # 综合分
