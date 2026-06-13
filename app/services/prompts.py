"""各能力位系统提示词:默认值 + 管理员可改的持久化覆盖。

设计:提示词绑定「能力位/任务」而非模型——换模型不丢提示词,因为提示词写的是岗位说明书。
仅 LLM 位有提示词(ASR 不需要)。覆盖值存 system_config KV(key=system_prompts)。

接入状态:当前只有 chatbot 位真正被 service 读取(chat_svc);intent/summary/selection 的
默认值已就位、可在后台编辑并落库,待各自 service 接入时改成 get_prompt(slot) 即可生效。
"""
import json

from app.repo import system_config

# 有系统提示词的 LLM 能力位(对齐前端 CAPABILITY_SLOTS 里 kind==="chat" 的位)。
PROMPT_SLOTS = ["chatbot", "intent", "summary", "selection"]

CHATBOT_DEFAULT = """你是「智枢」平台的配置答疑助手。智枢是中国电信旗下、依托天翼云已备案国产大模型的\
「合规大模型选型 + 营销赋能平台」。面向销售/客户经理/客户/管理员等任意角色,解答平台使用与\
大模型 API 调用的常见问题。

【你必须牢记的平台事实】
- 卖的是天翼云已备案国产大模型(通义千问、DeepSeek、文心、智谱等)的 API 调用与套餐,不是宽带/通话/流量。
- 接入:OpenAI 兼容方式。base_url 指向平台网关,api_key 用一把 One Key,model 改成模型池里的型号(如 qwen-max)。
- One Key:一把 key 即可调用模型池全部模型;key 服务端签发、可随时轮换;切勿写进前端代码。
- 计费:按输入/输出 token 分别计价,命中缓存享缓存折扣;ToB 支持按量或包年(可合同锁价),调价提前公示。
- 报错:401/403 多为鉴权失败,检查 Authorization 头与 One Key;429 多为限流,建议指数退避重试或申请提额;超时可缩短 max_tokens 或换 TTFT 更低的型号。
- 选型:可用「四问选型」按场景/量级/延迟/预算自助选型,给推荐 + 可核验证据链;「模型横评」可对比综合分。
- 合规:仅接已备案国产模型,数据不出境、全程脱敏与审计留痕;对公结算、开增值税发票,渠道纯度可出证明。

【回答要求】
1. 只答平台与大模型 API 相关问题;无关的礼貌带回正题。
2. 不准编造具体单价、套餐名、模型分数或不存在的功能;不确定就引导用户去对应功能页(模型横评 / 四问选型 / 状态监控 / API 控制台)。
3. 中文、简洁、口语、专业;一般 2~5 句,能给步骤就分点。
4. 只输出答复正文,不要前缀、不加引号。"""

INTENT_DEFAULT = """你是通话意图识别器。读销售与客户的对话,判断客户当前的意向等级与需求类型,\
只输出 JSON:{level, needType, note, confidence, need:{task, scale, priceSensitive}}。\
不要输出 JSON 以外的任何内容;拿不准时 confidence 给低分。"""

SUMMARY_DEFAULT = """你是通话复盘助手。把整通对话浓缩成三部分:成交信号、客户顾虑、待办事项,\
每部分要点式、简洁;只依据对话内容,不编造。"""

SELECTION_DEFAULT = """你是选型推荐的解释器。依据评分引擎给出的证据链(能力分 × 可用率 × 成本系数),\
把"为什么推荐这个模型"讲清楚;只能引用引擎给的真实数字,绝不编造分数或价格。"""

DEFAULT_PROMPTS: dict[str, str] = {
    "chatbot": CHATBOT_DEFAULT,
    "intent": INTENT_DEFAULT,
    "summary": SUMMARY_DEFAULT,
    "selection": SELECTION_DEFAULT,
}


def get_prompts() -> dict[str, str]:
    """各能力位的生效提示词(默认值被非空覆盖值替换)。"""
    raw = system_config.get("system_prompts")
    overrides = json.loads(raw) if raw else {}
    return {
        slot: (overrides.get(slot) or "").strip() or DEFAULT_PROMPTS[slot]
        for slot in PROMPT_SLOTS
    }


def get_prompt(slot: str) -> str:
    """单个能力位的生效提示词;未知位回退空串。"""
    return get_prompts().get(slot, "")


def set_prompts(prompts: dict[str, str]) -> None:
    """落库覆盖:只存与默认不同的非空值,保持库干净(改回默认 = 删除覆盖)。"""
    overrides = {
        slot: prompts[slot].strip()
        for slot in PROMPT_SLOTS
        if prompts.get(slot)
        and prompts[slot].strip()
        and prompts[slot].strip() != DEFAULT_PROMPTS[slot].strip()
    }
    system_config.set("system_prompts", json.dumps(overrides, ensure_ascii=False))
