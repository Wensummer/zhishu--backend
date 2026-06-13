# 智枢 · 通话中实时 Copilot · 实现文档

> 配套设计方案见 [copilot-realtime.md](./copilot-realtime.md)。本文记录**实际搭出来的东西**:
> 验证结论、架构、代码位置、怎么跑、哪些是占位待替换、下一步。

状态(截至 2026-06-11):**语音转写 → 意图识别 → 智能选型推荐**整条链路已真机跑通,
可在浏览器里对着麦克风说话、实时弹出带证据链的推荐。

---

## 1. 一句话架构

```
浏览器 Web Speech(本地实时转写)
   │  每句话定稿
   ▼
前端 /api/copilot/analyze (Next.js 同源转发)
   ▼
后端 POST /copilot/analyze
   ├─ DeepSeek:意图识别 + 抽结构化需求(task/scale/priceSensitive)
   └─ 选型引擎:需求 → 模型池按任务算综合分 → 出带证据链的推荐
   ▼
前端弹屏:意图徽标 + 推荐卡(证据链) + 话术卡
```

**关键设计**:ASR 在浏览器本地做,所以**这一版不需要 WebSocket**——只在每句话定稿时把文本 POST 给后端。

---

## 2. 技术选型(及为什么)

| 环节 | 现在用 | 生产建议 | 备注 |
|---|---|---|---|
| **语音转写 ASR** | 浏览器 Web Speech API | **讯飞 实时语音转写 / 语音听写** | Web Speech 中文一般、且音频走谷歌(出境),仅用于快速看手感;讯飞已验证质量好、合规 |
| **意图识别** | DeepSeek (`deepseek-chat`) | 天翼云已备案模型 | OpenAI 兼容,接口不变 |
| **选型推荐** | 自建评分引擎 `scoring.py` | 同左 | 确定性算分,证据链可核验,**不能让 LLM 编** |

### 踩过的坑(留档,避免重走)
- **讯飞星火域名 `spark-api.xfyun.cn` 被本机网络挡**(其他 LLM 都通)→ 意图识别改用 DeepSeek。
- **讯飞实时语音转写标准版无免费额度**(198元/40h);**语音听写有免费额度**,spike 用的是语音听写,端点 `wss://ws-api.xfyun.cn/v2/iat`(旧的 `iat-api.xfyun.cn` 不要用)。
- **阿里云百炼 Qwen** 域名能连,但需先在控制台**开通百炼**,否则 key 报 `invalid_api_key`。
- 合规红线不变:数据不出境、只用备案模型、Key 只在服务端。

---

## 3. 代码地图

### 后端 `zhishu-backend/`
| 文件 | 改动 | 作用 |
|---|---|---|
| `app/routers/copilot.py` | +`POST /copilot/analyze` | 实时分析入口 |
| `app/schemas/analyze.py` | 新增 | `AnalyzeRequest{text,context}` / `AnalyzeResponse{intent,recommendation?,script?}` |
| `app/services/intent_svc.py` | 新增 | DeepSeek 意图识别 + 抽需求;有需求走选型引擎,否则回退 demo 卡 |
| `app/services/selection_svc.py` | 新增 | 选型引擎:需求 → 候选 → 评分 → 推荐 |
| `app/services/scoring.py` | +`score_model_for_task` | 按"具体任务维度"算综合分 |
| `app/data/models.py` | +`TASK_SCORES`/`ALL_TASKS`/`task_score` | 模型池的分任务能力分(占位) |
| `app/config.py` | +`deepseek_api_key` | 从环境变量读 LLM key |
| `app/main.py` | CORS `allow_methods` 加 `POST` | 放行实时分析的 POST |

### 前端 `zhishu/`
| 文件 | 改动 | 作用 |
|---|---|---|
| `src/components/copilot/live-copilot-client.tsx` | 新增 | 实时麦克风模式:Web Speech 转写 + 调后端 + 弹屏;静音 5s 自动停止 |
| `src/components/copilot/copilot-client.tsx` | +模式切换 | 「剧本回放 / 实时麦克风」两档 |
| `src/components/copilot/intent-badge.tsx` | +`whitespace-nowrap` | 修徽标换行 |
| `src/app/api/copilot/analyze/route.ts` | 新增 | 同源转发到后端(免端口转发、免跨域) |
| `src/lib/api/index.ts` | +`analyzeUtterance` | 调 `/api/copilot/analyze` |
| `.env.local` | `NEXT_PUBLIC_API_BASE=http://localhost:8000` | 转发路由的后端地址 |

### 验证用 spike `zhishu-backend/experiments/voice/`(不进生产,留作参考/回归)
| 文件 | 作用 |
|---|---|
| `test_asr.py` | 讯飞语音听写转写(wav → 文字) |
| `test_intent.py` | DeepSeek 意图识别(含 few-shot、防闲聊、吃长段落+上下文) |
| `copilot_pipeline.py` | 转写+意图串成一条流的命令行 demo |
| `webspeech.html` | Web Speech 纯前端转写体感页 |
| `creds.py` | 讯飞 + DeepSeek 的 key(已 gitignore,不进库) |

---

## 4. 数据流详解:一句话怎么变成推荐

```
1. 浏览器 Web Speech 把"我们一百人团队做AI编程,想性价比高的"转成文字
2. live-copilot-client 在句子定稿时 POST {text, context(最近3轮)} → /api/copilot/analyze
3. Next.js 转发路由 → 后端 POST /copilot/analyze
4. intent_svc 调 DeepSeek,一次返回:
   { level, needType, note, confidence,
     need: {task:"代码", scale:"约100人", priceSensitive:true} }
5. 有 need.task → selection_svc.recommend_for_need:
   - 归一任务("编程/开发"→"代码")
   - 模型池每个模型按"代码"维度算 综合分=代码能力×可用率×成本系数
   - 选最高 → DeepSeek-R1
   - 出 Recommendation:含 evidenceChain(每项带 source/采集时间)、报价区间
6. 后端返回 {intent, recommendation, script?}
7. 前端弹:意图徽标 + 推荐卡(可展开证据链)
```

证据链的数字**全部来自结构化数据 + 确定性公式**,不是 LLM 生成的——这是"可核验、非黑盒"招牌的落地点。

---

## 5. 怎么跑(本地联调)

```bash
# 终端 1 — 后端(带 DeepSeek key)
cd zhishu-backend
DEEPSEEK_API_KEY=<你的key> uvicorn app.main:app --reload --port 8000

# 终端 2 — 前端
cd zhishu
npm run dev
```

- Mac 的 **Chrome** 打开 `http://localhost:3000/workbench/copilot/c-1024`
- VSCode 远程开发时,确认 **3000 端口已转发**(8000 走前端同源转发,无需单独转发)
- 顶部切「实时麦克风」→「开始说话」→ 允许麦克风 → 说一句客户的话
- 静音 5 秒自动停止;也可手动点「停止」

**冒烟(不开浏览器,直接打接口)**:
```bash
curl -s -X POST http://127.0.0.1:8000/copilot/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"我们一百人团队做AI编程,想性价比高的"}' | python3 -m json.tool
```

---

## 6. 占位项:接组员知识库后要替换的地方

| 占位 | 位置 | 换成 |
|---|---|---|
| 分任务能力分 `TASK_SCORES` | `data/models.py` | **选型库 #1** 的真实评测分(C-Eval/CMMLU/SuperCLUE/自跑任务集) |
| 生命周期状态 `MODEL_STATUS` | `data/models.py` | **选型库 #1** 的真实上下架/备案状态(见第 7 节) |
| 报价估算 `ASSUMED_ANNUAL_KTOKENS` | `selection_svc.py` | **定价库 #2** 的真实套餐价 + 议价区间 |
| 证据链 `source` 的 label/采集时间 | `scoring.py` `COLLECTED` | 各真实数据源(评测台/监控/定价库)的来源与时间戳 |

> 引擎逻辑、公式、证据链结构都不动,**只换数字**。这就是"数字走结构化喂引擎"的好处。

### 知识库分工(开发前必读)
- **数字走结构化**:选型库 #1 / 定价库 #2 直接以结构化数据喂引擎算分,**不走 Dify 向量检索**(否则解析不出精确数字,证据链不可核验)。
- **文字走向量 RAG**:话术库 #3 / 技术库 #4 给大模型用(话术润色、答疑 chatbot、citation 回填证据链 source)。

---

## 7. 双层风险防护:生命周期状态过滤 + 知识库风险检测

**背景**:实测"代码"需求时,数字引擎按 `能力×可用率×成本` 把 **DeepSeek-R1 排第一**,但知识库里写着 `DeepSeek-R1(即将5.20下线)`。光看数字会自信地推一个快停的模型——这正是"量化"看不出、需要"定性"补位的风险。

为此做了**两道防线**:

**① 引擎层(从源头避免)** —— 不推即将/已下线的模型
- `data/models.py` 的 `MODEL_STATUS`:每个模型的生命周期 `active`(在用)/ `deprecating`(即将下线)/ `retired`(已下线)。**占位数据**(当前 `deepseek-r1=deprecating`),待选型库 #1 的真实上下架状态替换。
- `selection_svc.py` 的 `_selectable()`:**只在「在用」模型里选**;若该任务下没有在用模型,退而取非「已下线」的。`retired` 永不推荐。
- 效果:"代码"需求现在推 **DeepSeek-V3(在用)**,自动避开了 R1。

**② 知识库层(第二道保险)** —— `RecommendationCard` 的推荐置信度
- 前端 `lib/recommendation/confidence.ts` 的 `RISK_PATTERN` 扫描 Dify 命中内容里的"下线/停售/停用/不再提供/停止服务"等词。
- 命中则**扣 18 分 + 标「需复核」+ 红色「状态风险」标**(置信度 = 量化×0.35 + 场景×0.3 + 知识×0.35 − 风险罚分)。
- 即使引擎层漏了(状态数据没更新),知识库层仍会兜底预警。

**比赛价值**:这是"量化 + 定性双证据、可核验"的最佳案例——**数字引擎不是黑盒打分,系统还能拦住"这模型快下线了"这种数字看不出的坑**。两道一起,推荐既算得准、又不踩生命周期的坑。

---

## 8. 已知限制 / 调优点

- **Web Speech 中文转写一般**(技术词易错、不加标点)。正式 demo 换讯飞,改动小:把转写来源从浏览器换成后端讯飞,下游不变。
- **成本系数公式偏向便宜模型**(性价比导向)。想让某些场景更看重能力,调 `scoring.py` 的 `COST_REFERENCE` 或 clamp 区间 `[0.85, 1.15]`。
- `need.priceSensitive` / `scale` 目前只用于 LLM 判断,未进评分公式;后续可据此调权重或选套餐档位。
- 报价是按假设年用量估的占位,接定价库前别当真。

---

## 9. 下一步建议

1. **接真数据**:组员选型库 #1 / 定价库 #2 导出 JSON → 替换 `TASK_SCORES` 与报价逻辑。
2. **话术 RAG**:推荐弹出时从 Dify 话术库 #3 检索,润色 `reason` / 补 `script`。
3. **citation 回填**:Dify 检索来源填进证据链 `source`,从"占位来源"变"真实知识库引用"。
4. **生产 ASR**:Web Speech → 讯飞(后端转发,合规、质量好)。
5. **复盘摘要**:通话结束对全量 transcript 生成摘要 + 待办(对齐前端 summary)。
