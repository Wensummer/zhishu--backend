"""意图识别(增强版)—— 吃"一整轮发言 + 上下文",带 few-shot,防闲聊误触发。

相比单句版的四个改进:
  1. 输入是客户「一整轮」的话(可能多句、夹闲聊),不是单句。
  2. 可带「最近对话上下文」(尤其销售刚说的话),判得更准。
  3. prompt 里给了 few-shot 示例 → 小模型也能又快又准。
  4. 闲聊/题外话 → 返回「无明显意图」,并给低 confidence,前端据此不弹屏。

用法:
    python test_intent.py            # 跑内置的 4 个场景做演示
    python test_intent.py "客户说的一整段话"
"""
import json
import sys
import urllib.request

import creds

ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"   # 要更快可换 deepseek 的轻量档;Qwen 通了可换 qwen-turbo
API_KEY = creds.DEEPSEEK_API_KEY

SYSTEM_PROMPT = """你是销售通话的实时意图识别助手。客户会说一整段话(可能夹杂闲聊、口头禅、题外话),你要识别其中的核心商机意图。

规则:
1. 忽略闲聊/题外话/寒暄(天气、球赛、客套),只抓商机信号。
2. 一段话里若有多个意图,返回最主要、最该让销售立刻行动的那个。
3. 没有明确商机信号时,needType 返回"无明显意图",confidence 给低分。
4. 结合上下文判断:比如销售刚报完价、客户说"有点高",就是价格异议。

needType 只能从这些里选:价格异议、成本敏感、新需求、成交信号、质量顾虑、犹豫拖延、无明显意图。
level 是成交意向高低 high/medium/low。confidence 是把握程度 0~1。

只输出一个 JSON,不要解释、不要 markdown:
{"level":"...","needType":"...","note":"给销售的一句话提示","confidence":0.x}"""

# few-shot:几个"输入→输出"示例,显著提升小模型准确率
FEW_SHOT = [
    ("【本轮客户发言】哎今天天气真不错,你那边下雨了吗哈哈",
     '{"level":"low","needType":"无明显意图","note":"纯闲聊,无需弹屏","confidence":0.95}'),
    ("【本轮客户发言】对了昨天那新闻看了没。行说正事,你们这价格比别家贵不少啊",
     '{"level":"medium","needType":"价格异议","note":"客户拿别家比价,强调价值与合规差异,别急着降价","confidence":0.85}'),
    ("【最近对话】销售: 这个质检增值包同行业落地效果不错\n【本轮客户发言】嗯,那你把方案发我看看",
     '{"level":"high","needType":"成交信号","note":"客户主动索要方案,推进度高,尽快发送并跟进","confidence":0.9}'),
]


def build_messages(turn: str, context: str | None):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_in, assistant_out in FEW_SHOT:
        msgs.append({"role": "user", "content": user_in})
        msgs.append({"role": "assistant", "content": assistant_out})
    content = (f"【最近对话】{context}\n" if context else "") + f"【本轮客户发言】{turn}"
    msgs.append({"role": "user", "content": content})
    return msgs


def classify(turn: str, context: str | None = None) -> str:
    body = json.dumps(
        {"model": MODEL, "messages": build_messages(turn, context), "temperature": 0.2}
    ).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# 内置演示场景:覆盖"段落夹闲聊 / 纯闲聊 / 靠上下文 / 成交信号"
SCENARIOS = [
    {
        "desc": "一整段夹闲聊 + 价格异议",
        "context": None,
        "turn": "哦对了,嗯,先说个题外话啊,上周那球赛你看了没,挺精彩哈。好了说正事,我们财务最近卡得紧,你们这续约价说实话有点超预算了,能不能给个实在的折扣",
    },
    {"desc": "纯闲聊(应判无意图)", "context": None,
     "turn": "哎今天这天气是真热啊,你们那边空调开了没,哈哈"},
    {
        "desc": "靠上下文才判得出(单看这句很模糊)",
        "context": "销售: 这个配置包年是 18 万,比月付能省两个月",
        "turn": "嗯……这个数字有点高啊",
    },
    {
        "desc": "成交信号",
        "context": "销售: 那我把质检增值包的方案整理一下发您",
        "turn": "行,那就这么定了,方案发我邮箱,续约我们走起",
    },
]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(f"客户说:{sys.argv[1]}\n\n结果:{classify(sys.argv[1])}")
    else:
        for s in SCENARIOS:
            print(f"—— {s['desc']} ——")
            if s["context"]:
                print(f"  上下文: {s['context']}")
            print(f"  客户: {s['turn']}")
            print(f"  → {classify(s['turn'], s['context'])}\n")
