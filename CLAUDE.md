# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

**智枢后端** — 江苏电信 OPC 大赛「选型 + 营销」智能赋能平台的后端。

技术栈:Python 3.12 + FastAPI + Pydantic v2。对接天翼云已备案国产模型(RAG / 选型评分 / 话术生成),当前阶段用 mock + 内置评分引擎跑通全部接口。

**铁律**:返回 JSON **严格对齐前端共享契约**(前端 `src/lib/types/index.ts` + `src/lib/demo/*.ts`)。前端把 `NEXT_PUBLIC_USE_MOCK=false` 一开就走真后端,**前端代码一行不改**。前端在 `../zhishu`(Next.js 14)。

## 启动开发

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# 交互式 API 文档: http://localhost:8000/docs
```

## 目录结构与分层

```
app/
├── main.py            # FastAPI 实例 + CORS + 路由注册
├── config.py          # 环境变量(CORS 白名单、天翼云 key)
├── schemas/           # ★ Pydantic 响应模型 = 前端 lib/types 的镜像。改契约只动这里
│   ├── base.py             # CamelModel 基类(snake_case → camelCase)
│   ├── common.py           # Trend / TimeSeriesPoint / SourceRef
│   ├── evidence.py         # EvidenceFactor / EvidenceChain   ← 招牌证据链
│   ├── model.py · customer.py · recommendation.py · script.py
│   ├── session.py · announcement.py · metric.py · briefing.py · billing.py
│   └── responses.py        # 组合返回类型
├── routers/           # 只管 HTTP:声明路径 + response_model,调 services/data 取数
│   ├── models.py · announcements.py · workbench.py
│   ├── briefing.py · copilot.py · admin.py · billing.py
├── services/          # ★ 业务逻辑 = 「占位→接真」的唯一改动点
│   ├── scoring.py          # 选型评分引擎(综合分 = 能力分 × 可用率 × 成本系数)
│   ├── briefing_svc.py     # 组装 Briefing
│   └── copilot_svc.py      # 组装 CopilotScript
├── data/              # 临时 mock 常量(原样移植前端 lib/demo),接真后逐个删
│   ├── models.py · customers.py · announcements.py · metrics.py · billing.py
└── integrations/      # 外部依赖客户端(当前空壳,P5 填)
    └── (tianyi.py / dify.py 待建)
```

### 数据流

```
前端 → routers(HTTP + response_model 校验) → services(业务逻辑) → data(mock) / integrations(天翼云·Dify)
```

`response_model` 是安全网:返回结构对不齐契约会**当场在后端报错**。

## 接口清单(6 + 1 个,全 mock)

| 接口 | 返回 |
|---|---|
| `GET /models` | Model[] |
| `GET /announcements` | Announcement[] |
| `GET /workbench` | WorkbenchData |
| `GET /briefing/{customerId}` | Briefing(mock + 评分引擎) |
| `GET /copilot/{customerId}` | CopilotScript |
| `GET /admin/dashboard` | DashboardData |
| `GET /billing` | BillingRecord[] |

快速冒烟:
```bash
for p in /models /announcements /workbench /briefing/c-1024 /copilot/c-1024 /admin/dashboard; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000$p)  $p"
done
```

## 序列化约定(避坑)

- **基类 `CamelModel`**:内部 snake_case,出口 camelCase。构造时用 snake_case 字段名(`populate_by_name=True`)。
- 路由统一 `response_model_exclude_none=True`:可选字段缺省时**不输出 null**。
- **`to_camel` 会把 `per1k` 误转成 `per1K`(大写 K)**。已用显式 `Field(alias="priceInputPer1k")` 锁死小写 k。以后再加 `数字+字母` 结尾的字段名要警惕。
- `tuple[float, float]` → JSON 数组 `[a, b]`。

## 契约坑清单(改代码前必读)

- 组合返回类型不在 `types/index.ts`,在 demo 文件里。
- **`CopilotScript.recommendations` 和 `.scripts` 是 dict(以 id 为 key),不是数组**;`IntentEvent.triggersRecommendationId` 按 key 引用。
- **`BriefingCustomer` 是拍平视图**,`currentModel`/`currentPlan` 存的是**名称字符串(不是 id)**。`Customer.currentModelId`、`Recommendation.targetModelId` 同样用模型名(如 `"通义千问-Max"`)而非 `"qwen-max"`。
- Stat 的 `value` 是字符串(`"32"` / `"68%"`)。
- 返回裸 array / object,无 `{data:...}` 信封。

## 评分引擎

`services/scoring.py`:

```
综合分 = 能力分 × 可用率 × 成本系数
成本系数 = 基准混合价(0.06) / 模型混合价   # clamp [0.85, 1.15]
混合价 = 输入单价 × 0.3 + 输出单价 × 0.7
```

- **c-1024**:简报用 demo 手写证据链(score 96.4),保前端像素级一致。
- **其他客户**:证据链由 `score_model()` 实时计算(展示引擎真在跑)。

## 红线

- 真实 API Key **只存服务端环境变量**,绝不出现在任何 `response_model` 中
- **数据不出境**:天翼云境内备案直连;Dify 自托管
- **脱敏**:客户名 / 企业名脱敏后才进 schema

## 接真数据的模式(P5)

```python
# 改前
from app.data.models import MODELS
return MODELS

# 改后
from app.integrations.tianyi import list_filed_models
return [desensitize(m) for m in await list_filed_models()]
```

**只动 `data/` → `services/`,`schemas/` 和 `routers/` 不用碰,前端更不用动**。
