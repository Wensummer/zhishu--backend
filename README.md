# 智枢后端 · zhishu-backend

江苏电信 OPC 大赛「智枢 —— 合规国产大模型选型 + 营销赋能平台」的后端。

- **技术栈**:Python 3.12 + FastAPI + Pydantic v2
- **定位**:对接天翼云已备案国产模型;RAG / 选型评分 / 话术生成逐步接入,当前阶段用 mock + 内置评分引擎跑通全部接口。
- **铁律**:返回 JSON **严格对齐前端共享契约**(前端仓库的 `src/lib/types/index.ts` + `src/lib/demo/*.ts`)。前端把 `NEXT_PUBLIC_USE_MOCK=false` 一开就走真后端,**前端代码一行不改**。

> 前端仓库在 `../zhishu`(Next.js 14)。契约是前后端唯一的合同,改字段必须两边同步。

---

## 1. 快速开始

```bash
# 1) 进目录(注意目录名带空格)
cd "/home/wxl/tele_work/ai_camp/zhishu- backend"

# 2) 建虚拟环境并装依赖(推荐,避免污染系统 Python)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3) 起服务(--reload 改代码自动重启)
uvicorn app.main:app --reload --port 8000

# 4) 验证
curl http://127.0.0.1:8000/health          # {"status":"ok"}
curl http://127.0.0.1:8000/models | jq '.[0]'
```

> 系统 Python 若被 PEP 668 锁定(`externally-managed-environment`),用上面的 venv 方案即可;
> 不想建 venv 也可 `pip install --break-system-packages -r requirements.txt`(自负风险)。

交互式 API 文档(FastAPI 自带):启动后访问 <http://127.0.0.1:8000/docs>。

---

## 2. 与前端联调(前端零改动)

前端只改 `.env.local`:

```
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- 后端路由**挂在根、无 `/api` 前缀**,前端 `fetch(`${API_BASE}${path}`)` 直接命中。
- CORS 默认放行 `http://localhost:3000`,改白名单见下方环境变量。

### 环境变量(见 `.env.example`)

| 变量 | 用途 | 默认 |
|---|---|---|
| `CORS_ORIGINS` | 前端跨域白名单(逗号分隔多个) | `http://localhost:3000` |
| `TIANYI_API_KEY` | 天翼云已备案模型 key(**仅服务端**,P5 用) | 空 |
| `TIANYI_BASE_URL` | 天翼云端点(P5 用) | 空 |

`app/config.py` 用纯 `os.getenv` 读取(本阶段不依赖 pydantic-settings,零额外安装)。

---

## 3. 目录结构与分层职责

```
app/
├── main.py            # FastAPI 实例 + CORS + 路由注册
├── config.py          # 环境变量(CORS 白名单、天翼云 key)
├── schemas/           # ★ Pydantic 响应模型 = 前端 lib/types 的镜像。改契约只动这里
│   ├── base.py            # CamelModel 基类(snake_case ↔ camelCase)
│   ├── common.py          # Trend / TimeSeriesPoint / SourceRef
│   ├── evidence.py        # EvidenceFactor / EvidenceChain   ← 招牌证据链
│   ├── model.py           # Model / PricingPlan
│   ├── customer.py        # Customer / FunnelStage / WorkbenchStat
│   ├── recommendation.py  # Recommendation
│   ├── script.py          # TalkScript
│   ├── session.py         # TranscriptLine / IntentEvent / CopilotScript
│   ├── announcement.py    # Announcement
│   ├── metric.py          # Metric / DashboardStat
│   ├── briefing.py        # BriefingCustomer / Briefing(组合)
│   └── responses.py       # WorkbenchData / DashboardData(组合)
├── routers/           # 只管 HTTP:声明路径 + response_model,调 services/data 取数
│   ├── models.py · announcements.py · workbench.py
│   ├── briefing.py · copilot.py · admin.py
├── services/          # ★ 业务逻辑 = 「占位→接真」的唯一改动点
│   ├── scoring.py         # 选型评分引擎(招牌主线),移植自前端 score.ts
│   ├── briefing_svc.py    # 组装 Briefing
│   └── copilot_svc.py     # 组装 CopilotScript
├── data/              # 临时 mock 常量(原样移植前端 lib/demo),接真后逐个删
│   ├── models.py · customers.py · announcements.py · metrics.py
└── integrations/      # 外部依赖客户端(当前空壳,P5 填)
    └── (tianyi.py / dify.py 待建)
```

**一句话分层**:`routers` 接 HTTP，`services` 装逻辑,`data` 放假数据,`schemas` 是契约。
接真数据时**只动 `data/` → `services/`,`schemas/` 和 `routers/` 不用碰,前端更不用动**。

### 数据流

```
前端 → routers(HTTP + response_model 校验) → services(业务逻辑) → data(mock) / integrations(天翼云·Dify)
```

`response_model` 是安全网:返回结构对不齐契约会**当场在后端报错**,不会把脏数据漏给前端。

---

## 4. 接口清单

六个接口全部完成(全 mock)。base = `http://127.0.0.1:8000`。

| 接口 | 返回类型 | 数据来源 | 说明 |
|---|---|---|---|
| `GET /models` | `Model[]` | mock | 模型池(横评/向导/状态共用) |
| `GET /announcements` | `Announcement[]` | mock | 调价/故障/上架公告 |
| `GET /workbench` | `{customers, funnel, stats}` | mock | 工作台:客户列表 + 漏斗 + 指标卡 |
| `GET /briefing/{customerId}` | `Briefing` | mock + 评分引擎 | c-1024 还原 demo;其他客户走引擎实时生成证据链 |
| `GET /copilot/{customerId}` | `CopilotScript` | mock | 通话剧本:转写 + 意图时间线 + 推荐/话术映射 + 摘要 |
| `GET /admin/dashboard` | `{stats, efficiencyTrend, funnel, trustMetrics}` | mock | 管理大屏 |

```bash
# 快速冒烟
for p in /models /announcements /workbench /briefing/c-1024 /copilot/c-1024 /admin/dashboard; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000$p)  $p"
done
```

---

## 5. 招牌主线:选型评分引擎

`services/scoring.py` 忠实移植前端 `src/lib/recommendation/score.ts`:

```
综合分 = 能力分 × 可用率 × 成本系数
成本系数 = 基准混合价(0.06) / 模型混合价   # clamp 到 [0.85, 1.15]
混合价   = 输入单价 × 0.3 + 输出单价 × 0.7
```

每个分项(`EvidenceFactor`)都带 `source`(数据来源 + 采集时间)→ 这是「**可核验**」的落地点:
推荐不是黑盒打分,而是公式分解 + 每项数值 + 每项来源都摊得开。

- **c-1024**:简报用 demo 手写的证据链(score 96.4),保前端像素级一致。
- **其他客户**(如 c-1031):证据链由 `score_model()` 按该客户当前模型**实时算**(展示引擎真在跑)。
- 接真后**只改 `source` 和 `collected_at` 的数据来源**(评测台/监控/定价库/Dify 检索 citation),**公式和结构不动**。

> 注:综合分可 >100(能力分最高 ~100 再 ×1.15),与 score.ts 一致,前端原样渲染,不是 bug。

---

## 6. How-To:加一个新接口

以加 `GET /pricing/{modelId}` 为例,四步:

1. **建 schema**(`app/schemas/xxx.py`):继承 `CamelModel`,字段写 snake_case。
2. **备数据/逻辑**:简单查表放 `data/`,有计算放 `services/`。
3. **写 router**(`app/routers/xxx.py`):
   ```python
   from fastapi import APIRouter
   router = APIRouter()

   @router.get("/pricing/{model_id}", response_model=PricingPlan,
               response_model_exclude_none=True)
   def get_pricing(model_id: str) -> PricingPlan:
       ...
   ```
4. **注册**:在 `app/main.py` 里 `from app.routers import xxx` + `app.include_router(xxx.router)`。

`--reload` 会自动重启,`curl` 一下即可。

## 7. How-To:把 mock 换成真数据(P5)

接真**不碰 schema 和 router**,只改 service 的取数来源:

```python
# 改前(data 里的 mock 常量)
from app.data.models import MODELS
return MODELS

# 改后(services 调天翼云/CRM,出库前脱敏)
from app.integrations.tianyi import list_filed_models
return [desensitize(m) for m in await list_filed_models()]
```

- **`/models`** → 天翼云已备案模型目录 + 评测台分数。
- **`/briefing` 证据链** → `scoring.py` 里 `source/collected_at` 换真实数据源。
- **话术 / 摘要** → 天翼云已备案大模型生成(key 留服务端)。
- **知识库/RAG** → 自托管 Dify,接进 `integrations/dify.py`(检索 citation 回填证据链 source)。

> ⚠️ Dify 必须**自托管**(私有部署),不能用 dify.ai 云版——会违反「数据不出境」。
> Dify 里的模型要配成天翼云 OpenAI 兼容端点,链路里只有已备案国产模型。

---

## 8. 契约坑清单(改代码前必读)

这些形状从前端 `lib/demo/*.ts` 挖出来,`types/index.ts` 里看不到,**很容易写错**:

- **组合返回类型不在 `types/index.ts`**,在 demo 文件:`FunnelStage`/`WorkbenchStat`(customers.ts)、`DashboardStat`(metrics.ts)、`Briefing`/`BriefingCustomer`(briefings.ts)、`CopilotScript`(sessions.ts)。
- **`CopilotScript.recommendations` 和 `.scripts` 是 dict(以 id 为 key),不是数组**;`IntentEvent.triggersRecommendationId` 按 key 引用。
- **`BriefingCustomer` 是拍平视图**:含 `rateLimitHits`/`errorCount`;`currentModel`/`currentPlan` 存的是**名称字符串(不是 id)**。`Customer.currentModelId`、`Recommendation.targetModelId` 同样用模型名(如 `"通义千问-Max"`)而非 `"qwen-max"`。
- **Stat 的 `value` 是字符串**(`"32"` / `"68%"`),格式化是后端的活。
- **返回裸 array / object,无 `{data:...}` 信封**。
- **`getBriefing` / `getCopilot` 有「未命中回退 c-1024」逻辑**,后端已复刻(换 id 不会 404)。

## 9. 序列化约定

- 基类 `CamelModel`:内部 snake_case,出口 camelCase(`alias_generator=to_camel`)。构造时用 snake_case 字段名(`populate_by_name=True`)。
- 路由统一 `response_model_exclude_none=True`:可选字段缺省时**不输出 null**(对齐 TS 的 `field?`)。
- `tuple[float, float]` → JSON 数组 `[a, b]`(对齐 TS 的 `[number, number]`)。
- ⚠️ **`to_camel` 会把 `per1k` 误转成 `per1K`(大写 K)**。`Model.price_input_per1k` / `price_output_per1k` 已用显式 `Field(alias="priceInputPer1k")` 锁死小写 k。**以后再加 `数字+字母` 结尾的字段名要警惕同类问题。**

---

## 10. 红线(合规,不可妥协)

- 真实 API Key **只存服务端环境变量**,绝不出现在任何 `response_model` / 下发前端。
- **数据不出境**:天翼云境内备案直连;Dify 自托管。
- **脱敏**:客户名 / 企业名脱敏后才进 schema(模型名是公开产品名,不脱敏)。

## 11. 进度与下一步

- ✅ **P1–P4**:六接口全部跑通(全 mock + 评分引擎),CORS 通,前端可整体联调。
- ⬜ **P5**:接天翼云模型 + 自托管 Dify 知识库;建 `integrations/tianyi.py` / `dify.py`;`data/` 逐个换 `services/` 真取数。
- ⬜ **(可选)契约测试**:`tests/test_contract.py` 用前端 demo JSON 做快照断言,接真数据时防字段跑偏。
