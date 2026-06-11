"""响应模型基类。

内部字段用 snake_case(Pythonic),出口序列化成 camelCase,
对齐前端 lib/types 契约。可选字段缺省时不输出(见各路由 response_model_exclude_none)。
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
