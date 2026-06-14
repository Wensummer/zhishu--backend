"""企业画像(企查查)响应 schema。

对齐前端 lib/types EnterpriseInfo 类型。
Phase 后期由企查查 MCP 获取真实数据替换。
"""
from app.schemas.base import CamelModel


class EnterpriseProfile(CamelModel):
    name: str
    credit_code: str
    legal_person: str
    registered_capital: str
    establish_date: str
    business_status: str
    address: str
    business_scope: str
    contact_person: str | None = None
    contact_phone: str | None = None


class EnterpriseKeyPersonnel(CamelModel):
    name: str
    title: str


class EnterpriseShareholder(CamelModel):
    name: str
    ratio: str
    amount: str


class EnterpriseController(CamelModel):
    name: str
    ratio: str
    path: str | None = None


class EnterpriseBranch(CamelModel):
    name: str
    ratio: str
    amount: str
    business_status: str


class EnterpriseHonor(CamelModel):
    name: str
    issuer: str
    date: str


class EnterpriseFunding(CamelModel):
    round: str
    amount: str
    date: str
    investors: str


class EnterpriseRiskItem(CamelModel):
    type: str
    title: str
    date: str
    amount: str | None = None
    department: str | None = None
    detail: str


class EnterpriseNews(CamelModel):
    title: str
    url: str
    date: str
    sentiment: str  # positive / neutral / negative
    summary: str


class EnterpriseIPR(CamelModel):
    type: str  # patent / trademark / copyright
    name: str
    reg_no: str
    status: str
    apply_date: str


class EnterpriseBid(CamelModel):
    title: str
    publish_date: str
    amount: str
    buyer: str


class EnterpriseInfo(CamelModel):
    profile: EnterpriseProfile
    personnel: list[EnterpriseKeyPersonnel]
    shareholders: list[EnterpriseShareholder]
    controller: EnterpriseController | None = None
    branches: list[EnterpriseBranch]
    honors: list[EnterpriseHonor]
    funding: list[EnterpriseFunding]
    risks: list[EnterpriseRiskItem]
    news: list[EnterpriseNews]
    ipr: list[EnterpriseIPR]
    bids: list[EnterpriseBid]
