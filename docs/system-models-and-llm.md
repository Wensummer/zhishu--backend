# 智枢 · 系统模型配置 + 接入 LLM/ASR API · 后端方案

> 「系统模型配置」= 平台**自身各能力位**用哪个模型(对内编排),区别于 `/admin/products` 管理的
> **对外可售模型池**。前端页面已完成(`/admin/system-models`),走 `lib/api`,后端需提供存取接口,
> 并让各运行时服务**真正按这份配置去调对应模型**。

---

## 1. 能力位(5 个)

| slot key | 能力位 | 候选来源 | 说明 |
|---|---|---|---|
| `asr` | 语音转写 | 语音模型(ASR) | 通话 Copilot 实时转写 |
| `chatbot` | 配置答疑 | 对话模型池 | 答疑助手 |
| `intent` | 意图识别 | 对话模型池 | 通话快路径分类,宜快而省 |
| `summary` | 复盘摘要 | 对话模型池 | 通话结束生成摘要 |
| `selection` | 选型 RAG | 对话模型池 | 推荐引擎(产出证据链) |

## 2. 接口契约(对齐前端 lib/types)

```jsonc
// GET /admin/system-models  → SystemModelConfig
{
  "bindings": {
    "asr": "asr-tianyi",
    "chatbot": "qwen-plus",
    "intent": "qwen-plus",
    "summary": "qwen-max",
    "selection": "deepseek-v3"
  },
  "updatedAt": "2026-06-10"
}

// PUT /admin/system-models  (body 同上)  → 保存后的 SystemModelConfig
// 要求:校验 modelId 是否存在/可用;落库;更新 updatedAt;敏感操作写审计留痕。

// GET /admin/asr-models  → AsrModel[]
[
  { "id": "asr-tianyi", "name": "天翼云实时语音转写", "vendor": "天翼云", "filed": true, "realtime": true, "latencyMs": 320 }
]
```

字段定义见前端 `../zhishu/src/lib/types/index.ts` 的 `SystemModelConfig` / `AsrModel` / `CapabilitySlotKey`。
对话模型候选来自 `GET /models`(对外模型池),前端已分别拉取。

### 模型注册表的增删改(真正"新增/修改模型"所需)

前端「系统模型配置」页有「新增模型」按钮:演示阶段新增的模型保存在前端本地状态(刷新即丢);
**要真持久化**(刷新/重启仍在、且能被各服务调用),后端需提供模型注册表的 CRUD:

```jsonc
// 语音模型(ASR)
POST   /admin/asr-models         body: AsrModel(无 id,后端生成)  → 新建的 AsrModel
PUT    /admin/asr-models/{id}    body: AsrModel                    → 更新后的 AsrModel
DELETE /admin/asr-models/{id}                                      → 204

// 对话模型(若允许在此新增,通常与 /admin/products 模型池打通,二选一来源)
POST   /admin/models             body: Model(无 id)               → 新建的 Model
PUT    /admin/models/{id}        body: Model
DELETE /admin/models/{id}                                          → 204
```

要点:
- 新增/编辑模型时,**同时要在「模型注册表」补上接入信息**(provider、endpoint、key 引用),否则只是列表里有名字、实际调不通。建议新增模型的表单/接口里就带上这些接入字段(前端 demo 暂未收集,真做时补)。
- 删除/停用绑定中的模型要校验:被某能力位占用的模型不允许直接删,需先改绑定。
- 所有增删改写审计留痕。

## 3. 配置如何驱动运行时(关键)

配置不是摆设,各服务在调模型前**读这份配置解析出 slot → 模型**:

```
请求(如答疑 chatbot)
  → 读 SystemModelConfig.bindings["chatbot"]  → modelId
  → 模型注册表 ModelRegistry[modelId] → { provider, endpoint, credentialRef }
  → 用对应凭证调该 provider 的 API
```

建议后端维护一张**模型注册表**(modelId → 接入信息),与可售模型池解耦:

```python
# 形如(放配置/DB,不要硬编码 Key)
REGISTRY = {
  "qwen-max":   {"provider": "tianyi", "model": "qwen-max",  "endpoint": "...", "key_env": "TIANYI_API_KEY"},
  "deepseek-v3":{"provider": "tianyi", "model": "deepseek-v3","endpoint": "...", "key_env": "TIANYI_API_KEY"},
  "asr-tianyi": {"provider": "tianyi_asr", "ws": "wss://...", "key_env": "TIANYI_ASR_KEY"},
}
```

切换能力位 = 改 `bindings` → 服务下次调用即用新模型,**无需改代码、无需重启**(配置实时读取)。

---

## 4. 如何真正接入 LLM API(对话类能力位)

天翼云模型池多为 **OpenAI 兼容** 接口,直接用 openai SDK 即可。

### 4.1 凭证与配置(红线:Key 只在服务端)
```bash
# 环境变量 / 密钥管理(.env、KMS、k8s secret),绝不进代码仓库、绝不下发前端
TIANYI_API_KEY=sk-...
TIANYI_BASE_URL=https://<天翼云模型网关>/v1
```

### 4.2 调用(FastAPI 示例)
```python
import os
from openai import OpenAI
from app.config import get_system_config, REGISTRY  # 你的配置读取

def client_for(model_id: str) -> tuple[OpenAI, str]:
    reg = REGISTRY[model_id]
    client = OpenAI(api_key=os.environ[reg["key_env"]], base_url=reg["endpoint"])
    return client, reg["model"]

def chat(slot: str, messages: list[dict], stream: bool = False):
    cfg = get_system_config()                 # GET /admin/system-models 的同一份
    model_id = cfg["bindings"][slot]          # 如 slot="chatbot"
    client, model = client_for(model_id)
    return client.chat.completions.create(model=model, messages=messages, stream=stream)
```

### 4.3 各能力位怎么用
- **chatbot**:把答疑问题 + 技术 RAG 检索结果拼进 messages → `chat("chatbot", ...)`,流式回前端。
- **intent**:通话每句 final → `chat("intent", ...)`,要求输出结构化意图(JSON),宜选快/省模型。
- **summary**:通话结束把整段 transcript → `chat("summary", ...)` 生成摘要。
- **selection**:RAG 取模型/定价知识 → 评分(综合分 = 能力分 × 可用率 × 成本系数)→ 用模型润色推荐文案,
  **务必产出完整 evidenceChain**(公式 + 分项 + 来源 + 采集时间)。

### 4.4 工程要点
- **流式**:chatbot / copilot 摘要用 `stream=True`,经 SSE/WebSocket 推前端,体验更好。
- **超时与重试**:网络/限流(429)做指数退避;失败时按配置回退到备用模型(可选)。
- **结构化输出**:intent/selection 让模型返 JSON,服务端校验(对齐 lib/types),失败重试或规则兜底。
- **可观测**:记录每次调用的 model、tokens、耗时 → 反哺横评/状态页/用量计费。
- **成本**:命中缓存走缓存折扣;intent 这类高频位选便宜模型。

---

## 5. 如何接入 ASR API(语音能力位)

- `bindings["asr"]` → 选定的 ASR(如天翼云/讯飞实时转写)。
- 与对话模型不同:ASR 是 **WebSocket 流式**,后端把通话音频帧转发给 ASR,拿到 partial/final 文本,
  再经通话 WS 推前端(详见同目录 `copilot-realtime.md` 的事件协议)。
- 凭证同样只在服务端;音频与转写按合规脱敏、留痕。

---

## 6. 落地顺序

1. 配置存取:`GET/PUT /admin/system-models` + `GET /admin/asr-models`(可先返回固定列表)。
2. 模型注册表 + `client_for()` + `chat(slot, ...)` 封装。
3. 先把 **chatbot** 接通(最容易验证:问一句有真回答)。
4. 再接 **selection / summary / intent**,最后 **asr**(配合 copilot-realtime)。

## 7. 红线
- API Key(LLM/ASR)只在服务端,绝不下发前端;数据不出境;只接已备案国产模型。
- 改配置、轮换密钥等敏感操作写审计留痕。
