"""管理数据 CRUD API + 数据管理页面。

提供对 SQLite 各表的通用增删改查,供内嵌管理页面使用。
"""
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

from app.database import get_connection

router = APIRouter()

# 哪些表暴露给管理页面及其展示名
MANAGED_TABLES: dict[str, str] = {
    "models": "模型池",
    "pricing_plans": "套餐/定价",
    "customers": "客户列表",
    "announcements": "公告",
    "talk_scripts": "话术模板",
    "system_config": "系统配置",
    "billing_records": "计费明细",
    "customer_usage": "用量趋势",
    "recommendations": "推荐选型",
    "copilot_sessions": "通话会话",
    "session_transcripts": "通话转写",
    "session_intents": "意图事件",
    "dashboard_stats": "大屏·统计卡",
    "dashboard_efficiency": "大屏·效率趋势",
    "dashboard_funnel": "大屏·漏斗",
    "dashboard_trust_metrics": "大屏·信任指标",
}

# 各表可编辑的字段（排除主键的编辑指引用）。
# type: text / number / long(长文本,弹窗编辑)
TABLE_SCHEMA: dict[str, list[dict[str, str]]] = {
    "models": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "name", "label": "模型名称", "type": "text"},
        {"col": "vendor", "label": "厂商", "type": "text"},
        {"col": "capability_tier", "label": "能力等级", "type": "text"},
        {"col": "capability_score", "label": "能力分", "type": "number"},
        {"col": "price_input_per1k", "label": "输入单价(元/千token)", "type": "number"},
        {"col": "price_output_per1k", "label": "输出单价(元/千token)", "type": "number"},
        {"col": "cache_discount", "label": "缓存折扣", "type": "number"},
        {"col": "ttft_ms", "label": "首token延迟(ms)", "type": "number"},
        {"col": "tpot_ms", "label": "单token耗时(ms)", "type": "number"},
        {"col": "availability", "label": "可用率", "type": "number"},
        {"col": "channel_purity", "label": "渠道纯度", "type": "number"},
        {"col": "use_cases", "label": "适配场景(JSON数组)", "type": "long"},
        {"col": "filed", "label": "已备案(0/1)", "type": "number"},
    ],
    "pricing_plans": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "model_id", "label": "模型ID", "type": "text"},
        {"col": "name", "label": "套餐名称", "type": "text"},
        {"col": "tier", "label": "类型(toB/toC)", "type": "text"},
        {"col": "billing_mode", "label": "计费模式(payg/package)", "type": "text"},
        {"col": "list_price", "label": "标准价(元)", "type": "number"},
        {"col": "negotiable_min", "label": "议价下限", "type": "number"},
        {"col": "negotiable_max", "label": "议价上限", "type": "number"},
        {"col": "quota_tokens", "label": "套餐含量(token)", "type": "number"},
    ],
    "customers": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "name", "label": "企业名称", "type": "text"},
        {"col": "industry", "label": "行业", "type": "text"},
        {"col": "is_new", "label": "是否新客(0/1)", "type": "number"},
        {"col": "current_model_id", "label": "当前模型", "type": "text"},
        {"col": "current_plan_id", "label": "当前套餐", "type": "text"},
        {"col": "balance", "label": "余额(元)", "type": "number"},
        {"col": "expire_at", "label": "到期时间", "type": "text"},
        {"col": "stage", "label": "商机阶段", "type": "text"},
        {"col": "tags", "label": "标签(JSON数组)", "type": "long"},
        {"col": "owner_manager_id", "label": "客户经理ID", "type": "text"},
        {"col": "contact", "label": "联系人", "type": "text"},
        {"col": "monthly_spend", "label": "月消费(元)", "type": "number"},
        {"col": "telecom_products", "label": "其他电信产品(JSON数组)", "type": "long"},
        {"col": "enterprise_info_json", "label": "企业画像(JSON)", "type": "long"},
    ],
    "announcements": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "kind", "label": "类型", "type": "text"},
        {"col": "title", "label": "标题", "type": "text"},
        {"col": "body", "label": "内容", "type": "long"},
        {"col": "model_id", "label": "关联模型ID", "type": "text"},
        {"col": "published_at", "label": "发布时间", "type": "text"},
        {"col": "resolved_at", "label": "解决时间", "type": "text"},
    ],
    "talk_scripts": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "stage", "label": "阶段", "type": "text"},
        {"col": "scene", "label": "场景", "type": "text"},
        {"col": "title", "label": "标题", "type": "text"},
        {"col": "content", "label": "话术内容", "type": "long"},
        {"col": "objection", "label": "异议内容", "type": "long"},
    ],
    "system_config": [
        {"col": "key", "label": "配置键", "type": "text"},
        {"col": "value", "label": "配置值(JSON)", "type": "long"},
    ],
    "customer_usage": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "customer_id", "label": "客户ID", "type": "text"},
        {"col": "date", "label": "日期", "type": "text"},
        {"col": "value", "label": "用量值", "type": "number"},
    ],
    "recommendations": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "customer_id", "label": "客户ID", "type": "text"},
        {"col": "rec_type", "label": "推荐类型", "type": "text"},
        {"col": "title", "label": "推荐标题", "type": "text"},
        {"col": "target_model_id", "label": "目标模型", "type": "text"},
        {"col": "target_plan_id", "label": "目标套餐", "type": "text"},
        {"col": "reason", "label": "推荐理由", "type": "long"},
        {"col": "quote_min", "label": "报价下限", "type": "number"},
        {"col": "quote_max", "label": "报价上限", "type": "number"},
        {"col": "evidence_json", "label": "证据链(JSON)", "type": "long"},
        {"col": "sort_order", "label": "排序", "type": "number"},
    ],
    "copilot_sessions": [
        {"col": "id", "label": "ID", "type": "text"},
        {"col": "customer_id", "label": "客户ID", "type": "text"},
        {"col": "summary", "label": "会话摘要", "type": "long"},
        {"col": "max_sec", "label": "时长(秒)", "type": "number"},
    ],
    "session_transcripts": [
        {"col": "id", "label": "ID", "type": "number"},
        {"col": "session_id", "label": "会话ID", "type": "text"},
        {"col": "speaker", "label": "说话人", "type": "text"},
        {"col": "text", "label": "内容", "type": "long"},
        {"col": "at_sec", "label": "时间(秒)", "type": "number"},
        {"col": "sort_order", "label": "排序", "type": "number"},
    ],
    "session_intents": [
        {"col": "id", "label": "ID", "type": "number"},
        {"col": "session_id", "label": "会话ID", "type": "text"},
        {"col": "at_sec", "label": "时间(秒)", "type": "number"},
        {"col": "level", "label": "意图等级", "type": "text"},
        {"col": "need_type", "label": "需求类型", "type": "text"},
        {"col": "note", "label": "提示语", "type": "long"},
        {"col": "triggers_recommendation_id", "label": "触发推荐ID", "type": "text"},
        {"col": "triggers_script_id", "label": "触发话术ID", "type": "text"},
    ],
}

# 主键字段名
TABLE_PK: dict[str, str] = {
    "models": "id",
    "pricing_plans": "id",
    "customers": "id",
    "announcements": "id",
    "talk_scripts": "id",
    "system_config": "key",
    "billing_records": "id",
    "customer_usage": "id",
    "recommendations": "id",
    "copilot_sessions": "id",
    "session_transcripts": "rowid",
    "session_intents": "rowid",
    "dashboard_stats": "rowid",
    "dashboard_efficiency": "rowid",
    "dashboard_funnel": "rowid",
    "dashboard_trust_metrics": "key",
}


TABLE_CATEGORY: dict[str, str] = {
    "models": "基础数据",
    "pricing_plans": "基础数据",
    "customers": "业务数据",
    "announcements": "业务数据",
    "talk_scripts": "业务数据",
    "system_config": "业务数据",
    "billing_records": "业务数据",
    "customer_usage": "业务数据",
    "recommendations": "业务数据",
    "copilot_sessions": "业务数据",
    "session_transcripts": "业务数据",
    "session_intents": "业务数据",
    "dashboard_stats": "运营大屏",
    "dashboard_efficiency": "运营大屏",
    "dashboard_funnel": "运营大屏",
    "dashboard_trust_metrics": "运营大屏",
}


@router.get("/admin/data/tables", response_class=JSONResponse, response_model=None)
def list_tables():
    return [
        {"key": k, "label": v, "type": TABLE_CATEGORY.get(k, "其他"), "columns": TABLE_SCHEMA.get(k, [])}
        for k, v in MANAGED_TABLES.items()
    ]


@router.get("/admin/data/{table_name}", response_class=JSONResponse, response_model=None)
def get_table_data(table_name: str):
    if table_name not in MANAGED_TABLES:
        raise HTTPException(404, f"未知表: {table_name}")
    conn = get_connection()
    rows = conn.execute(f"SELECT * FROM [{table_name}]").fetchall()
    conn.close()
    return [dict(r) for r in rows]


class RowUpsert(BaseModel):
    row: dict[str, Any]


@router.post("/admin/data/{table_name}", response_class=JSONResponse, response_model=None)
def upsert_row(table_name: str, body: RowUpsert):
    if table_name not in MANAGED_TABLES:
        raise HTTPException(404, f"未知表: {table_name}")
    pk = TABLE_PK[table_name]
    row = body.row
    conn = get_connection()

    cols = list(row.keys())
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols)

    sql = (
        f"INSERT INTO [{table_name}] ({','.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT({pk}) DO UPDATE SET {updates}"
    )
    try:
        conn.execute(sql, [row[c] for c in cols])
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(400, f"写入失败: {e}")
    conn.close()
    return {"ok": True, pk: row[pk]}


@router.delete("/admin/data/{table_name}/{row_id}", response_class=JSONResponse, response_model=None)
def delete_row(table_name: str, row_id: str):
    if table_name not in MANAGED_TABLES:
        raise HTTPException(404, f"未知表: {table_name}")
    pk = TABLE_PK[table_name]
    conn = get_connection()
    conn.execute(f"DELETE FROM [{table_name}] WHERE {pk}=?", (row_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/admin/data", response_class=HTMLResponse, include_in_schema=False)
def admin_data_page() -> str:
    """内嵌数据管理页面。"""
    return ADMIN_HTML


ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>智枢 · 数据管理</title>
<style>
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --card: 0 0% 100%;
  --card-foreground: 222.2 84% 4.9%;
  --muted: 210 40% 96.1%;
  --muted-foreground: 215.4 16.3% 46.9%;
  --primary: 201 96% 32%;
  --primary-foreground: 210 40% 98%;
  --secondary: 210 40% 96.1%;
  --secondary-foreground: 222.2 47.4% 11.2%;
  --accent: 210 40% 96.1%;
  --accent-foreground: 222.2 47.4% 11.2%;
  --destructive: 0 84.2% 60.2%;
  --destructive-foreground: 210 40% 98%;
  --success: 142 71% 45%;
  --border: 214.3 31.8% 91.4%;
  --input: 214.3 31.8% 91.4%;
  --ring: 201 96% 32%;
  --radius: 0.65rem;
}

.hsl-bg { background: hsl(var(--background)); }
.hsl-text { color: hsl(var(--foreground)); }

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  padding: 0;
  min-height: 100vh;
}

/* === 顶栏 === */
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid hsl(var(--border));
  background: hsl(var(--card));
}
.page-header .logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: calc(var(--radius) - 2px);
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 16px;
  font-weight: 700;
}
.page-header h1 {
  font-size: 17px;
  font-weight: 600;
  color: hsl(var(--foreground));
  letter-spacing: -0.01em;
}
.page-header .sub {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-left: auto;
}

/* === 主体 === */
.main { padding: 20px 24px; }

/* === 侧栏布局 === */
.layout { display: flex; gap: 0; min-height: calc(100vh - 57px); }
.sidebar { width: 180px; flex-shrink: 0; border-right: 1px solid hsl(var(--border)); padding: 12px 0; overflow-y: auto; background: hsl(var(--card)); }
.sidebar-group { font-size: 10px; font-weight: 700; color: hsl(var(--muted-foreground)); letter-spacing: 0.06em; padding: 12px 16px 4px; text-transform: uppercase; opacity: 0.5; }
.sidebar-tab { display: block; width: 100%; text-align: left; padding: 7px 16px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; background: transparent; color: hsl(var(--muted-foreground)); font-family: inherit; transition: background 0.1s, color 0.1s; border-right: 2px solid transparent; }
.sidebar-tab:hover { background: hsl(var(--accent)); color: hsl(var(--foreground)); }
.sidebar-tab.active { color: hsl(var(--primary)); background: hsl(var(--primary) / 0.08); border-right-color: hsl(var(--primary)); }
.content { flex: 1; padding: 20px 24px; overflow-x: hidden; }

/* === 工具栏 === */
.toolbar {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.toolbar button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 14px;
  height: 34px;
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.toolbar button:hover { background: hsl(var(--accent)); }
.toolbar .btn-primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}
.toolbar .btn-primary:hover { opacity: 0.9; }
.toolbar .btn-destructive {
  background: hsl(var(--destructive));
  color: hsl(var(--destructive-foreground));
  border-color: hsl(var(--destructive));
}
.toolbar .btn-destructive:hover { opacity: 0.9; }
.toolbar .status {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-left: 12px;
}
.toolbar .status-ok { color: hsl(var(--success)); }
.toolbar .status-err { color: hsl(var(--destructive)); }

/* === 长文本预览 === */
.long-preview {
  cursor: pointer;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 3px 6px;
  border-radius: calc(var(--radius) - 2px);
  border: 1px dashed hsl(var(--border));
  font-size: 13px;
  line-height: 1.4;
  transition: border-color 0.15s, background 0.15s;
}
.long-preview:hover {
  border-color: hsl(var(--ring));
  background: hsl(var(--accent));
}

/* === 弹窗 === */
.modal-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0,0,0,0.4);
  align-items: center;
  justify-content: center;
}
.modal-overlay.show { display: flex; }
.modal-box {
  background: hsl(var(--card));
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  box-shadow: 0 16px 48px rgba(0,0,0,0.15);
  width: 640px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid hsl(var(--border));
}
.modal-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--foreground));
}
.modal-close {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: calc(var(--radius) - 2px);
  font-size: 16px;
  color: hsl(var(--muted-foreground));
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-close:hover { background: hsl(var(--accent)); color: hsl(var(--foreground)); }
.modal-body { padding: 18px; overflow-y: auto; flex: 1; }
.modal-body textarea {
  width: 100%;
  min-height: 200px;
  padding: 10px 12px;
  border: 1px solid hsl(var(--input));
  border-radius: calc(var(--radius) - 2px);
  font-size: 13px;
  font-family: 'Menlo', 'Consolas', 'Courier New', monospace;
  line-height: 1.6;
  resize: vertical;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  outline: none;
}
.modal-body textarea:focus {
  border-color: hsl(var(--ring));
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.15);
}
.modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  padding: 12px 18px;
  border-top: 1px solid hsl(var(--border));
}
.modal-footer button {
  padding: 7px 18px;
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  transition: background 0.15s;
}
.modal-footer button:hover { background: hsl(var(--accent)); }
.modal-footer .btn-primary {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  border-color: hsl(var(--primary));
}
.modal-footer .btn-primary:hover { opacity: 0.9; }

/* === 表格 === */
.table-wrap {
  overflow-x: auto;
  background: hsl(var(--card));
  border-radius: var(--radius);
  border: 1px solid hsl(var(--border));
  max-height: calc(100vh - 220px);
}
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
  table-layout: fixed;
}
th, td {
  padding: 8px 14px;
  text-align: left;
  border-bottom: 1px solid hsl(var(--border));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
th {
  background: hsl(var(--muted));
  font-weight: 600;
  position: sticky;
  top: 0;
  user-select: none;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
  letter-spacing: 0.02em;
}
th .th-label {
  cursor: pointer;
  padding: 2px 0;
}
th:hover { color: hsl(var(--foreground)); }
th .resizer {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  cursor: col-resize;
  z-index: 10;
}
th .resizer:hover,
th .resizer.resizing {
  background: hsl(var(--ring) / 0.4);
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: hsl(var(--accent) / 0.5); }
td input {
  border: 1px solid transparent;
  padding: 3px 6px;
  border-radius: calc(var(--radius) - 2px);
  width: 100%;
  font-size: 13px;
  font-family: inherit;
  background: transparent;
  color: inherit;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}
td input:focus {
  border-color: hsl(var(--ring));
  outline: none;
  background: hsl(var(--background));
  box-shadow: 0 0 0 2px hsl(var(--ring) / 0.15);
}
td .pk {
  font-weight: 600;
  color: hsl(var(--primary));
  background: transparent;
  border-color: transparent;
  cursor: default;
}
.row-new td { background: hsl(142 71% 45% / 0.06); }
.row-new td input { background: transparent; }
.del-cb { width: 16px; height: 16px; cursor: pointer; accent-color: hsl(var(--primary)); }

/* === 空状态 === */
.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: hsl(var(--muted-foreground));
  font-size: 14px;
}
</style>
</head>
<body>
<div class="page-header">
  <div class="logo-icon">智</div>
  <h1>数据管理</h1>
  <span class="sub">内部管理 · 修改实时写库</span>
</div>
<div class="layout">
  <div class="sidebar" id="sidebar"></div>
  <div class="content">
    <div class="toolbar">
      <button class="btn-primary" onclick="addRow()">+ 新增行</button>
      <button onclick="saveAll()">✓ 保存全部</button>
      <button class="btn-destructive" onclick="deleteSelected()">× 删除选中</button>
      <span class="status" id="status"></span>
    </div>
    <div class="table-wrap">
      <table id="table">
        <tbody id="tbody"></tbody>
      </table>
  </div>
</div>

<!-- 长文本编辑弹窗 -->
<div class="modal-overlay" id="modal">
  <div class="modal-box">
    <div class="modal-header">
      <h3 id="modal-title">编辑内容</h3>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body">
      <textarea id="modal-textarea"></textarea>
    </div>
    <div class="modal-footer">
      <button onclick="closeModal()">取消</button>
      <button class="btn-primary" onclick="confirmModal()">确定</button>
    </div>
  </div>
</div>

<script>
let currentTable = '';
let tables = [];
let schema = {};
let deletedIds = [];
let sortDir = {};
let sortCol = null;
let currentData = [];
// 弹窗状态
let modalCol = null;
let modalRowIdx = null;

async function load() {
  const r = await fetch('/admin/data/tables');
  tables = await r.json();
  const sidebar = document.getElementById('sidebar');
  const groups = {};
  const groupOrder = [];
  for (const t of tables) {
    const g = t.type || '其他';
    if (!groups[g]) { groups[g] = []; groupOrder.push(g); }
    groups[g].push(t);
  }
  sidebar.innerHTML = '';
  for (const g of groupOrder) {
    sidebar.insertAdjacentHTML('beforeend', `<div class="sidebar-group">${g}</div>`);
    for (const t of groups[g]) {
      sidebar.insertAdjacentHTML('beforeend',
        `<button class="sidebar-tab${t.key === currentTable ? ' active' : ''}" onclick="switchTable('${t.key}')">${t.label}</button>`
      );
    }
  }
  if (!currentTable && tables.length) await switchTable(tables[0].key);
}

async function switchTable(key) {
  currentTable = key;
  deletedIds = [];
  sortCol = null;
  sortDir = {};
  const t = tables.find(x => x.key === key);
  schema = t ? t.columns : [];
  document.querySelectorAll('.sidebar-tab').forEach(el => el.classList.toggle('active', el.getAttribute('onclick')?.includes(key) ?? false));
  await renderTable();
}

async function renderTable() {
  const r = await fetch('/admin/data/' + currentTable);
  currentData = await r.json();
  const tbody = document.getElementById('tbody');
  if (!schema.length && currentData.length) {
    schema = Object.keys(currentData[0]).map(c => ({ col: c, label: c, type: 'text' }));
  }
  tbody.innerHTML = renderTableBody();
  renderHeader();
  setStatus(`${currentData.length} 行`);
}

function renderTableBody() {
  if (!currentData.length) {
    return `<tr><td colspan="${schema.length + 1}" class="empty-state">暂无数据</td></tr>`;
  }
  return currentData.map((row, i) => renderRow(row, i)).join('');
}

function renderHeader() {
  const table = document.getElementById('table');
  let thead = table.querySelector('thead');
  if (!thead) { thead = document.createElement('thead'); table.insertBefore(thead, table.firstChild); }
  thead.innerHTML = `<tr>${
    schema.map((c, i) => {
      const dir = sortCol === c.col ? (sortDir[c.col] === 'asc' ? ' ▲' : ' ▼') : '';
      return `<th data-col-index="${i}" style="width:${getColWidth(c.col)}">
        <span class="th-label" onclick="sortBy('${c.col}')">${c.label}${dir}</span>
        <div class="resizer" onmousedown="startResize(event, ${i})"></div>
      </th>`;
    }).join('')
  }<th style="width:36px;text-align:center"> </th></tr>`;
}

function renderRow(row, idx) {
  const pk = getPk();
  const pkVal = row[pk] ?? '';
  return `<tr data-pk="${pkVal}" data-idx="${idx}">${schema.map((c, ci) => {
    const v = row[c.col] ?? '';
    const isPk = c.col === pk;
    if (c.type === 'long') {
      const preview = String(v).length > 40 ? String(v).slice(0, 40) + '…' : String(v);
      return `<td><div class="long-preview" data-col="${c.col}" data-idx="${idx}" onclick="openModal(${idx}, '${c.col}', '${esc(String(v))}')" title="${esc(String(v))}">${esc(preview)}</div></td>`;
    }
    const vStr = typeof v === 'object' ? JSON.stringify(v) : String(v);
    return `<td><input class="${isPk ? 'pk' : ''}" data-col="${c.col}" value="${esc(vStr)}" ${isPk ? 'readonly' : ''}></td>`;
  }).join('')}<td style="text-align:center"><input type="checkbox" class="del-cb" data-pk="${pkVal}"></td></tr>`;
}

function addRow() {
  const emptyRow = {};
  schema.forEach(c => { emptyRow[c.col] = ''; });
  currentData.push(emptyRow);
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = currentData.map((row, i) => renderRow(row, i)).join('');
  setStatus('已添加新行,填写后点击"保存全部"');
}

function deleteSelected() {
  const cbs = document.querySelectorAll('.del-cb:checked');
  const toRemove = new Set();
  cbs.forEach(cb => {
    const pk = cb.getAttribute('data-pk');
    if (pk && !pk.startsWith('__new_')) { deletedIds.push(pk); }
    toRemove.add(pk);
  });
  if (toRemove.size === 0) { setStatus('请勾选要删除的行', 'err'); return; }
  currentData = currentData.filter(r => !toRemove.has(r[getPk()] ?? ''));
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = currentData.map((row, i) => renderRow(row, i)).join('');
  setStatus(`待删除: ${deletedIds.length} 行, 点击"保存全部"生效`);
}

async function saveAll() {
  const btn = document.querySelector('.btn-primary');
  btn.disabled = true;
  const origText = btn.textContent;
  btn.textContent = '保存中...';

  let ok = 0, fail = 0;

  // 删除
  for (const id of deletedIds) {
    try {
      const r = await fetch(`/admin/data/${currentTable}/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (r.ok) ok++; else fail++;
    } catch(e) { fail++; }
  }
  deletedIds = [];

  // 增/改
  for (const row of currentData) {
    try {
      const r = await fetch(`/admin/data/${currentTable}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ row }),
      });
      if (r.ok) ok++; else fail++;
    } catch(e) { fail++; }
  }

  btn.disabled = false;
  btn.textContent = origText;
  setStatus(`保存完成: ${ok} 成功, ${fail} 失败`, fail ? 'err' : 'ok');
  await renderTable();
}

function sortBy(col) {
  const dir = sortDir[col] === 'asc' ? 'desc' : 'asc';
  sortDir = { [col]: dir };
  sortCol = col;
  currentData.sort((a, b) => {
    const va = a[col] ?? '';
    const vb = b[col] ?? '';
    const na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) return dir === 'asc' ? na - nb : nb - na;
    return dir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = currentData.map((row, i) => renderRow(row, i)).join('');
  renderHeader();
}

function getPk() {
  const m = {models:'id',pricing_plans:'id',customers:'id',announcements:'id',talk_scripts:'id',system_config:'key',billing_records:'id',customer_usage:'id',recommendations:'id',copilot_sessions:'id',session_transcripts:'rowid',session_intents:'rowid',dashboard_stats:'rowid',dashboard_efficiency:'rowid',dashboard_funnel:'rowid',dashboard_trust_metrics:'key'};
  return m[currentTable] || 'id';
}

// === 长文本弹窗 ===
function openModal(rowIdx, col, val) {
  modalRowIdx = rowIdx;
  modalCol = col;
  document.getElementById('modal-title').textContent = '编辑: ' + (schema.find(c => c.col === col)?.label || col);
  document.getElementById('modal-textarea').value = val;
  document.getElementById('modal').classList.add('show');
  setTimeout(() => document.getElementById('modal-textarea').focus(), 100);
}

function closeModal() {
  document.getElementById('modal').classList.remove('show');
  modalCol = null;
  modalRowIdx = null;
}

function confirmModal() {
  const val = document.getElementById('modal-textarea').value;
  if (modalRowIdx !== null && modalCol) {
    currentData[modalRowIdx][modalCol] = val;
    const tbody = document.getElementById('tbody');
    tbody.innerHTML = currentData.map((row, i) => renderRow(row, i)).join('');
    setStatus('已修改,点击"保存全部"生效');
  }
  closeModal();
}

// ESC 关闭弹窗
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeModal();
});

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function setStatus(msg, type) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status' + (type ? ' status-' + type : '');
}

// === 列宽拖拽 ===
const COL_WIDTH_KEY = 'zhishu_admin_col_widths';
let colWidths = {};

function loadColWidths() {
  try { colWidths = JSON.parse(localStorage.getItem(COL_WIDTH_KEY)) || {}; } catch(e) { colWidths = {}; }
}
function saveColWidths() {
  try { localStorage.setItem(COL_WIDTH_KEY, JSON.stringify(colWidths)); } catch(e) {}
}
function getColWidth(col) {
  return colWidths[col] || 'auto';
}

function startResize(e, colIndex) {
  e.preventDefault();
  const th = e.target.closest('th');
  const startX = e.clientX;
  const startW = th.offsetWidth;

  function onMove(ev) {
    const diff = ev.clientX - startX;
    const newW = Math.max(60, startW + diff);
    th.style.width = newW + 'px';
    th.style.maxWidth = newW + 'px';
    // 更新同列所有 td 的宽度
    const col = schema[colIndex]?.col;
    if (col) {
      colWidths[col] = newW + 'px';
    }
  }

  function onUp() {
    saveColWidths();
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
    document.body.style.cursor = '';
    th.querySelector('.resizer')?.classList.remove('resizing');
  }

  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
  document.body.style.cursor = 'col-resize';
  th.querySelector('.resizer')?.classList.add('resizing');
}

loadColWidths();
load();
</script>
</body>
</html>"""
