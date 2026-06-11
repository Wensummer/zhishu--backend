"""演示用客户与工作台数据(原样移植 lib/demo/customers.ts)。

客户名、企业名均为脱敏假数据。Phase 后期由 service 从 CRM/计费(脱敏后)取数替换。
"""
from app.schemas.customer import Customer, FunnelStage, WorkbenchStat

CUSTOMERS: list[Customer] = [
    Customer(
        id="c-1024", name="云帆智造科技", industry="智能制造", is_new=False,
        current_model_id="通义千问-Max", current_plan_id="包年企业版",
        balance=38000, expire_at="2026-07-15", stage="renew",
        tags=["高活跃", "对延迟敏感"], owner_manager_id="m-01",
        contact="周经理", monthly_spend=24800,
    ),
    Customer(
        id="c-1031", name="锦书文化传媒", industry="内容/营销", is_new=False,
        current_model_id="DeepSeek-V3", current_plan_id="按量标准版",
        balance=6200, expire_at="2026-06-28", stage="upgrade",
        tags=["用量上涨", "可加推 Agent"], owner_manager_id="m-01",
        contact="林总", monthly_spend=15600,
    ),
    Customer(
        id="c-1042", name="恒生金服数科", industry="金融科技", is_new=False,
        current_model_id="文心一言-4.0", current_plan_id="包年企业版",
        balance=120000, expire_at="2026-09-30", stage="expand",
        tags=["多部门扩容", "合规要求高"], owner_manager_id="m-01",
        contact="吴总监", monthly_spend=86000,
    ),
    Customer(
        id="c-1055", name="蓝橙教育", industry="在线教育", is_new=False,
        current_model_id="智谱 GLM-4", current_plan_id="按量标准版",
        balance=800, expire_at="2026-06-12", stage="silent",
        tags=["用量下滑", "余额不足"], owner_manager_id="m-01",
        contact="陈老师", monthly_spend=3200,
    ),
    Customer(
        id="c-2003", name="途新出行", industry="出行/物流", is_new=True,
        stage="newLead", tags=["官网咨询", "待画像"], owner_manager_id="m-01",
        contact="赵经理",
    ),
]


def get_customer_by_id(customer_id: str) -> Customer | None:
    return next((c for c in CUSTOMERS if c.id == customer_id), None)


WORKBENCH_FUNNEL: list[FunnelStage] = [
    FunnelStage(label="线索", value=86),
    FunnelStage(label="商机", value=42),
    FunnelStage(label="报价", value=23),
    FunnelStage(label="成交", value=11),
]

WORKBENCH_STATS: list[WorkbenchStat] = [
    WorkbenchStat(label="本月跟进客户", value="32", hint="较上月 +6", trend="up", icon="users"),
    WorkbenchStat(label="待跟进商机", value="14", hint="其中 5 个高意向", trend="flat", icon="target"),
    WorkbenchStat(label="推荐采纳率", value="68%", hint="较上月 +9%", trend="up", icon="adoption"),
    WorkbenchStat(label="续费率", value="91%", hint="较上月 +2%", trend="up", icon="renew"),
]
