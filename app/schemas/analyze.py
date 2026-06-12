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
    script: TalkScript | None = None              # 命中异议场景才有
