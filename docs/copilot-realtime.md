# 智枢 · 通话中实时 Copilot · 后端技术方案

> 面向后端开发。前端(Next.js,位于 `../zhishu`)的通话页 UI 与数据结构已完成,
> 真实化的本质是:**把前端"时钟驱动的剧本回放"换成"后端真实管线产生的同结构事件"**。
> 前端组件几乎不改,只把数据源从定时器换成 WebSocket 订阅。

---

## 0. 核心原则

**AI 不进入说话回路**,只在旁边给客户经理弹建议。因此端到端延迟 **1~3 秒完全可接受** ——
这大幅降低实现难度与现场风险,也决定了"快/慢双路径"的设计。

- **快路径(秒级)**:ASR 流式转写 + 轻量意图识别 → 实时上字、实时标意图。
- **慢路径(异步)**:RAG 选型 + 评分引擎(大模型)→ 算好带证据链的推荐再弹屏,不卡转写。

---

## 1. 整体架构

```
麦克风/通话音频
   │ (PCM 音频帧)
   ▼
前端浏览器 ──WebSocket(/ws/copilot/{sessionId})──► 后端(FastAPI 编排)
   ▲                                                  │
   │  下行事件流(JSON):                                ├─► 实时 ASR(流式 STT)      ← 快
   │  ready/transcript_*/intent/recommendation/        ├─► 意图识别(小模型/规则)    ← 快
   │  script/summary/error                             └─► RAG 选型 + 评分引擎(大模型)← 慢(异步)
   └──────────────────────────────────────────────────┘
```

- 前后端**一条 WebSocket** 双向:上行音频 + 控制消息,下行事件。
- 后端持有所有密钥(ASR / 大模型),音频经后端转发到 ASR(**合规:Key 只在服务端,数据可控**)。
- 大模型走天翼云已备案模型池。

---

## 2. 技术选型(每环带推荐)

### 2.1 实时 ASR(流式语音转文字)—— 选国产合规
- 推荐**讯飞 / 阿里云 / 腾讯云 实时语音转写**(WebSocket 流式,中文成熟,带标点、partial/final 结果)。
  若天翼云提供 ASR 能力则优先(贴合"依托天翼云")。
- 走法:**前端音频 → 后端 → ASR 提供商**(后端转发,持密钥)。不要让前端直连 ASR(密钥/合规)。
- 不用浏览器原生 Web Speech API(中文不稳、不合规)。

### 2.2 说话人区分(客户 vs 客户经理)—— 现场关键难点
真实电话是两路音频;现场 demo 无真电话,按可靠性排序:
- **方案 A(最稳)**:双声道/双设备,客户经理一路、客户一路,`speaker` 由声道决定。
- **方案 C(演示友好)**:单麦 + 前端"切换说话人"按钮,人工标注,100% 可靠。
- 方案 B(说话人分离 diarization):复杂易错,**现场不建议**。
> 后端在事件里输出 `speaker` 字段;具体由谁判定(声道/前端标注)在控制消息里约定。

### 2.3 意图识别(快路径,每句话级)
- 触发时机:ASR 给出一句 **final 转写**(尤其客户的话)。
- 实现:**小模型/快模型分类**(意向 high/medium/low + 需求类型)为主,**关键词规则兜底**(保证现场不空场)。
- 产出 = 前端 `IntentEvent`。

### 2.4 推荐 / 话术(慢路径,异步)
- 触发:识别到"新需求 / 异议 / 成交信号"。
- 跑 **RAG 选型 + 评分引擎**,复用前端同一公式:`综合分 = 能力分 × 可用率 × 成本系数`
  (参考 `../zhishu/src/lib/recommendation/score.ts`)。
- **务必填全证据链**:公式分解 + 各分项数值 + 每项数据来源与采集时间(产品差异化核心)。
- 算好再 push,不阻塞转写。

### 2.5 复盘摘要(通话结束)
- 大模型对全量 transcript 生成摘要 + 待办 + 回流标注 → 前端 `summary`。

---

## 3. WebSocket 协议(后端需实现的核心)

**连接**:`GET /ws/copilot/{sessionId}`(可带 `?customerId=c-1024`)

### 3.1 上行(前端 → 后端)
- **二进制帧**:音频数据(PCM16 / Opus,采样率在 start 里声明)。
- **控制消息(JSON 文本帧)**:
```json
// 开始
{ "type": "start", "customerId": "c-1024", "sampleRate": 16000, "encoding": "pcm16", "channels": 1 }
// 切换说话人(单麦方案 C 用)
{ "type": "speaker", "speaker": "customer" }   // 或 "manager"
// 结束
{ "type": "end" }
```

### 3.2 下行(后端 → 前端),统一信封 `{ type, payload }`
```jsonc
// 1) 就绪
{ "type": "ready", "payload": { "sessionId": "s-001" } }

// 2) 转写(partial 可被后续覆盖;final 落定)
{ "type": "transcript_partial", "payload": { "speaker": "customer", "text": "我看市面上有些中转便宜不少", "atSec": 11.2 } }
{ "type": "transcript_final",   "payload": { "speaker": "customer", "text": "我看市面上有些中转便宜不少,你们能再松松吗?", "atSec": 11.8 } }

// 3) 意图(对齐 lib/types 的 IntentEvent)
{ "type": "intent", "payload": {
    "atSec": 11.8, "level": "medium", "needType": "价格异议",
    "note": "拿中转比价施压",
    "triggersRecommendationId": "r-1", "triggersScriptId": "s-3" } }

// 4) 推荐(对齐 lib/types 的 Recommendation,含证据链)
{ "type": "recommendation", "payload": {
    "id": "r-1", "type": "renew", "title": "包年锁价续约,化解预算顾虑",
    "targetModelId": "qwen-max", "reason": "客户担心成本与调价 —— 包年锁价给预算确定性。",
    "quoteRange": [180000, 210000],
    "evidenceChain": {
      "formula": "综合分 = 能力分 × 可用率 × 成本系数", "score": 96.4,
      "factors": [
        { "key": "capability", "label": "能力分", "value": 92, "display": "92",
          "source": { "label": "天翼云模型评测台", "collectedAt": "2026-05-30" } },
        { "key": "availability", "label": "可用率", "value": 0.998, "display": "99.8%",
          "source": { "label": "可用性监控 · 30 天", "collectedAt": "2026-06-08" } },
        { "key": "costFactor", "label": "成本系数", "value": 1.05, "display": "×1.05",
          "source": { "label": "定价知识库 · 包年", "collectedAt": "2026-06-01" } }
      ] } } }

// 5) 话术(对齐 lib/types 的 TalkScript)
{ "type": "script", "payload": {
    "id": "s-3", "scene": "objection", "title": "应对比价异议",
    "objection": "市面上有更便宜的中转",
    "content": "便宜多是逆向渠道、随时跳价或跑路…证据链每项来源都能摊给您看。" } }

// 6) 复盘摘要
{ "type": "summary", "payload": { "summary": "客户确认续约…", "todos": ["发送质检增值包方案"], "tags": ["成交信号", "已回流话术库"] } }

// 7) 错误
{ "type": "error", "payload": { "code": "asr_unavailable", "message": "ASR 连接失败" } }
```

> 前端按 `type` 分发:`transcript_*`→转写流、`intent`→意图徽标、`recommendation`/`script`→弹卡、`summary`→复盘卡。
> 这些 payload 形状与前端 `../zhishu/src/lib/types/index.ts` 完全一致,**前端组件零改动**。

---

## 4. 数据契约(必须对齐前端)

后端所有结构对齐 `../zhishu/src/lib/types/index.ts`,关键类型:

- **TranscriptLine**: `{ speaker: "customer"|"manager", text: string, atSec: number }`
- **IntentEvent**: `{ atSec, level: "high"|"medium"|"low", needType, note?, triggersRecommendationId?, triggersScriptId? }`
- **Recommendation**: `{ id, customerId?, type: "renew"|"upgrade"|"expand"|"switch"|"addon", title, targetModelId, targetPlanId?, reason, quoteRange:[number,number], evidenceChain }`
- **EvidenceChain**: `{ formula, score, factors: EvidenceFactor[] }`
- **EvidenceFactor**: `{ key, label, value:number, display?, weight?, source:{ label, collectedAt } }`
- **TalkScript**: `{ id, customerId?, scene: "opening"|"sellingPoint"|"objection"|"pricing"|"renewal", title, content, objection? }`

> 建议后端用 Pydantic 照抄这些字段名(camelCase 原样),FastAPI 直接序列化,避免前端做字段映射。

---

## 5. REST 接口(非实时部分,回放/历史)

通话模块除 WS 外,保留一个 REST(对齐前端 `lib/api` 的 `getCopilotSession`):
- `GET /copilot/{customerId}` → 返回一段完整 `CallSession`(剧本回放 / 历史复盘用)。
  结构见前端 `../zhishu/src/lib/demo/sessions.ts` 的 `CopilotScript`:
  `{ customerId, customerName, maxSec, transcript[], intents[], recommendations{}, scripts{}, summary }`。

其余平台接口见后端总契约:`/models`、`/workbench`、`/briefing/{id}`、`/announcements`、`/admin/dashboard`。

---

## 6. 现场演示稳健性(重要:别裸奔真实管线)

做成**三档可切换**,临场哪档稳用哪档。三档下游事件结构完全一致:

| 档 | 说明 | 风险 | 用途 |
|---|---|---|---|
| **剧本回放** | REST 拉 `CallSession`,前端定时器播(前端现有实现) | ~零 | 兜底,设备/网络异常立即切 |
| **预录音频管线** | 播一段事先录好的对话音频 → 喂真实 ASR→意图→推荐全链路 | 低 | **主力演示**:真 AI 在跑且可复现 |
| **现场真麦** | 现场说话实时跑 | 高(口音/噪音/网络) | 彩排稳了再上 |

后端配合点:WS 接口要能接受**音频文件流**(预录档)与**实时麦克风流**(真麦档),走同一套管线。

其它:网络备份(热点)、麦克风提前调试、ASR/模型额度提前充值、演示客户("云帆智造 c-1024")的预录音与剧本对齐。

---

## 7. 分阶段落地

1. **WS + ASR 打通**:浏览器音频 → 后端 → 流式 ASR → push `transcript_*` → 前端实时上字。(看到字 = 成功一半)
2. **意图识别**:对 final 句分类 → push `intent`。
3. **推荐/话术异步**:命中需求/异议 → 跑选型引擎 → push 带证据链的 `recommendation`/`script`。
4. **复盘摘要** + 预录音管线(兜底主力)。
5. 彩排现场真麦。

工作量大头:1(音频流 + ASR 联调)、2.2(说话人区分)。3/4 复用已有评分逻辑与前端 UI,较快。

---

## 8. 红线

- 真实 API Key(ASR / 大模型)只在后端,绝不下发前端。
- 数据不出境;只接已备案国产模型;客户名/企业名脱敏。
- 通话音频与转写按合规要求脱敏、留痕、可审计。
