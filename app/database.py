"""SQLite 数据库连接 + 建表 + 种子数据。

零外部依赖(Python 内置 sqlite3)。数据库文件在 data_store/zhishu.db。
"""
import json
import os
import sqlite3

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_store")
DB_PATH = os.path.join(DB_DIR, "zhishu.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """建表(幂等) + 种子数据(空库时写入)。"""
    conn = get_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS models (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            vendor        TEXT NOT NULL,
            capability_tier TEXT NOT NULL,
            capability_score REAL NOT NULL,
            price_input_per1k  REAL NOT NULL,
            price_output_per1k  REAL NOT NULL,
            cache_discount    REAL NOT NULL,
            ttft_ms       REAL NOT NULL,
            tpot_ms       REAL NOT NULL,
            availability  REAL NOT NULL,
            channel_purity REAL NOT NULL,
            use_cases     TEXT NOT NULL,
            filed         INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pricing_plans (
            id            TEXT PRIMARY KEY,
            model_id      TEXT NOT NULL,
            name          TEXT NOT NULL,
            tier          TEXT NOT NULL,
            billing_mode  TEXT NOT NULL,
            list_price    REAL NOT NULL,
            negotiable_min REAL NOT NULL,
            negotiable_max REAL NOT NULL,
            quota_tokens  INTEGER
        );

        CREATE TABLE IF NOT EXISTS customers (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            industry        TEXT NOT NULL,
            is_new          INTEGER NOT NULL DEFAULT 0,
            current_model_id TEXT,
            current_plan_id  TEXT,
            balance         REAL,
            expire_at       TEXT,
            stage           TEXT NOT NULL,
            tags            TEXT NOT NULL,
            owner_manager_id TEXT NOT NULL,
            contact         TEXT,
            monthly_spend   REAL
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id           TEXT PRIMARY KEY,
            kind         TEXT NOT NULL,
            title        TEXT NOT NULL,
            body         TEXT NOT NULL,
            model_id     TEXT,
            published_at TEXT NOT NULL,
            resolved_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS system_config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS talk_scripts (
            id        TEXT PRIMARY KEY,
            stage     TEXT NOT NULL,
            scene     TEXT NOT NULL,
            title     TEXT NOT NULL,
            content   TEXT NOT NULL,
            objection TEXT
        );

        CREATE TABLE IF NOT EXISTS billing_records (
            id            TEXT PRIMARY KEY,
            date          TEXT NOT NULL,
            model         TEXT NOT NULL,
            model_id      TEXT NOT NULL,
            api_key_name  TEXT NOT NULL,
            tokens        INTEGER NOT NULL,
            input_tokens  INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            amount        REAL NOT NULL,
            unit_price    REAL NOT NULL,
            billing_mode  TEXT NOT NULL,
            customer_id   TEXT
        );

        CREATE TABLE IF NOT EXISTS dashboard_stats (
            rowid       INTEGER PRIMARY KEY AUTOINCREMENT,
            label       TEXT NOT NULL,
            value       TEXT NOT NULL,
            hint        TEXT NOT NULL,
            trend       TEXT NOT NULL,
            icon        TEXT NOT NULL,
            series_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dashboard_efficiency (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            date  TEXT NOT NULL,
            value REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dashboard_funnel (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            value REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dashboard_trust_metrics (
            key         TEXT PRIMARY KEY,
            label       TEXT NOT NULL,
            value       REAL NOT NULL,
            unit        TEXT,
            baseline    REAL,
            target      REAL,
            series_json TEXT
        );

        CREATE TABLE IF NOT EXISTS customer_usage (
            id          TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            date        TEXT NOT NULL,
            value       REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id              TEXT PRIMARY KEY,
            customer_id     TEXT,
            rec_type        TEXT NOT NULL,
            title           TEXT NOT NULL,
            target_model_id TEXT NOT NULL,
            target_plan_id  TEXT,
            reason          TEXT NOT NULL,
            quote_min       REAL NOT NULL,
            quote_max       REAL NOT NULL,
            evidence_json   TEXT NOT NULL,
            sort_order      INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS copilot_sessions (
            id          TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            summary     TEXT NOT NULL DEFAULT '',
            max_sec     REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS session_transcripts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            speaker     TEXT NOT NULL,
            text        TEXT NOT NULL,
            at_sec      REAL NOT NULL,
            sort_order  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS session_intents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            at_sec      REAL NOT NULL,
            level       TEXT NOT NULL,
            need_type   TEXT NOT NULL,
            note        TEXT,
            triggers_recommendation_id TEXT,
            triggers_script_id TEXT
        );
    """)

    # === 种子数据：仅在空库时写入 ===
    row = conn.execute("SELECT COUNT(*) AS cnt FROM models").fetchone()
    if row and row["cnt"] > 0:
        conn.close()
        return

    _seed(conn)
    conn.commit()
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    """写入从当前 mock 数据移植的种子数据。"""
    # ---------- 模型池 ----------
    models = [
        ("qwen-max",     "通义千问-Max",   "阿里云百炼",  "S", 94, 0.04,  0.12,  0.4,  420, 28, 0.998, 1,    json.dumps(["复杂推理", "长文档", "Agent"], ensure_ascii=False), 1),
        ("qwen-plus",    "通义千问-Plus",  "阿里云百炼",  "A", 88, 0.008, 0.02,  0.4,  360, 22, 0.997, 1,    json.dumps(["通用对话", "高并发", "性价比"], ensure_ascii=False), 1),
        ("ernie-4",      "文心一言-4.0",   "百度智能云",  "S", 92, 0.03,  0.09,  0.3,  480, 30, 0.995, 1,    json.dumps(["知识问答", "金融合规", "长文档"], ensure_ascii=False), 1),
        ("deepseek-v3",  "DeepSeek-V3",    "深度求索",    "A", 90, 0.002, 0.008, 0.5,  520, 26, 0.992, 1,    json.dumps(["代码", "性价比", "通用对话"], ensure_ascii=False), 1),
        ("deepseek-r1",  "DeepSeek-R1",    "深度求索",    "S", 93, 0.004, 0.016, 0.5,  900, 34, 0.99,  1,    json.dumps(["深度推理", "数学", "代码"], ensure_ascii=False), 1),
        ("glm-4",        "智谱 GLM-4",     "智谱 AI",     "A", 87, 0.05,  0.05,  0.3,  400, 24, 0.996, 1,    json.dumps(["通用对话", "工具调用", "多模态"], ensure_ascii=False), 1),
        ("moonshot-128k", "Kimi-128K",     "月之暗面",    "A", 86, 0.06,  0.06,  0.2,  560, 27, 0.994, 1,    json.dumps(["超长上下文", "文档分析", "RAG"], ensure_ascii=False), 1),
        ("baichuan-4",   "百川-4",         "百川智能",    "B", 82, 0.01,  0.03,  0.25, 440, 25, 0.991, 1,    json.dumps(["通用对话", "性价比"], ensure_ascii=False), 1),
    ]
    conn.executemany(
        "INSERT INTO models VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", models
    )

    # ---------- 套餐 ----------
    plans = [
        ("plan-qwen-max-ent",  "qwen-max",    "包年企业版",     "toB", "package", 240000, 180000, 210000, 8000000),
        ("plan-qwen-max-payg", "qwen-max",    "按量企业版",     "toB", "payg",   0.12,   0.08,   0.15,   None),
        ("plan-qwen-plus-ent", "qwen-plus",   "包年企业版",     "toB", "package", 96000,  72000,  84000,  4000000),
        ("plan-qwen-plus-std", "qwen-plus",   "按量标准版",     "toB", "payg",   0.02,   0.015,  0.03,   None),
        ("plan-ernie-ent",     "ernie-4",     "包年企业版",     "toB", "package", 360000, 280000, 320000, 10000000),
        ("plan-deepseek-std",  "deepseek-v3", "按量标准版",     "toB", "payg",   0.008,  0.005,  0.012,  None),
        ("plan-deepseek-ent",  "deepseek-v3", "包年企业版",     "toB", "package", 60000,  48000,  55000,  3000000),
        ("plan-glm4-std",      "glm-4",       "按量标准版",     "toB", "payg",   0.05,   0.035,  0.06,   None),
    ]
    conn.executemany(
        "INSERT INTO pricing_plans VALUES (?,?,?,?,?,?,?,?,?)", plans
    )

    # ---------- 客户 ----------
    customers = [
        ("c-1024", "云帆智造科技", "智能制造", 0, "通义千问-Max",  "包年企业版",  38000,  "2026-07-15", "renew",  json.dumps(["高活跃", "对延迟敏感"], ensure_ascii=False), "m-01", "周经理", 24800),
        ("c-1031", "锦书文化传媒", "内容/营销", 0, "DeepSeek-V3",  "按量标准版",  6200,   "2026-06-28", "upgrade", json.dumps(["用量上涨", "可加推 Agent"], ensure_ascii=False), "m-01", "林总", 15600),
        ("c-1042", "恒生金服数科", "金融科技", 0, "文心一言-4.0", "包年企业版", 120000, "2026-09-30", "expand",  json.dumps(["多部门扩容", "合规要求高"], ensure_ascii=False), "m-01", "吴总监", 86000),
        ("c-1055", "蓝橙教育",     "在线教育", 0, "智谱 GLM-4",   "按量标准版",  800,    "2026-06-12", "silent",  json.dumps(["用量下滑", "余额不足"], ensure_ascii=False), "m-01", "陈老师", 3200),
        ("c-2003", "途新出行",     "出行/物流", 1, None, None, None, None, "newLead", json.dumps(["官网咨询", "待画像"], ensure_ascii=False), "m-01", "赵经理", None),
    ]
    for c in customers:
        conn.execute(
            "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", c
        )

    # ---------- 公告 ----------
    announcements = [
        ("a-1", "priceChange", "DeepSeek-V3 输出价下调 12%", "自 2026-06-15 起生效,提前 7 天公示。老客户合同锁价不受影响。", "deepseek-v3", "2026-06-08", None),
        ("a-2", "incident",    "DeepSeek-R1 短时延迟升高",   "06-06 14:20 ~ 15:05 TTFT 升高约 300ms,已扩容恢复,期间无请求失败。", "deepseek-r1", "2026-06-06", "2026-06-06"),
        ("a-3", "shelf",       "新增上架 Kimi-128K 超长上下文", "适配长文档 / RAG 场景,已纳入横评与选型引擎。", "moonshot-128k", "2026-06-01", None),
        ("a-4", "maintenance", "文心一言-4.0 例行维护",       "05-30 02:00 ~ 02:30 滚动维护,采用灰度切换,服务不中断。", "ernie-4", "2026-05-30", "2026-05-30"),
    ]
    conn.executemany(
        "INSERT INTO announcements VALUES (?,?,?,?,?,?,?)", announcements
    )

    # ---------- 话术模板 ----------
    scripts = [
        ("s-renew-opening",     "renew",   "opening",     "续约切入",       "{contact}您好,这季度贵司调用量涨了约 40%,稳定性一直保持在 99.8%。续约前我把用量和选型给您过一遍,顺便锁个价,避免后面调价影响预算。", None),
        ("s-renew-selling",    "renew",   "sellingPoint","合规 + 锁价",   "我们是天翼云备案直连、渠道纯度可出证明,合同锁价 + 调价提前公示,发票对公正规 —— 这几点是中转站给不了的,贵司做预算和审计都省心。", None),
        ("s-renew-objection",  "renew",   "objection",   "价格异议",     "便宜的多是逆向渠道、随时可能跳价或跑路,日志里还可能掺别的模型。我们贵在确定性:锁价、SLA、7×24 和数据不出境。需要的话我把证据链摊给您看每一分数据的来源。", "市面上有更便宜的中转"),
        ("s-upgrade-opening",  "upgrade", "opening",     "用量升级诊断",  "{contact}您好,这几个月贵司调用量增长明显,当前套餐的配额可能快不够用了。我帮您看看是不是升级到更高规格更划算,避免超量后单价反而更贵。", None),
        ("s-upgrade-selling",  "upgrade", "sellingPoint","高规格解锁能力","升级后不仅能获得更大并发配额,还能解锁高级能力——更低首 token 延迟、更高上下文窗口、优先调度权。这些对您业务体验的提升是立竿见影的,而且综合下来单位成本反而更低。", None),
        ("s-upgrade-objection","upgrade", "objection",   "升级成本顾虑",  "短期看月费确实上浮了,但按当前增速,下季度您很可能就会触发现有限额,届时的超量费用比升级费高出 30% 以上。升级相当于提前锁一个更低的单价,跑得越多省得越多。", "升级后成本更高了"),
        ("s-expand-opening",   "expand",  "opening",     "多部门扩容方案","{contact}您好,我们看到贵司多个部门都在使用模型能力,当前共享额度可能不够分。我帮您设计一个多部门独立配额 + 统一管控的方案,每个部门用多少、花多少一目了然。", None),
        ("s-expand-selling",   "expand",  "sellingPoint","独立配额 + 统一管控","我们可以按部门设置独立额度、独立预算、独立调用链监控,但统一走您的企业账户结算。各部门互不影响,您随时能看到全盘的用量大盘和成本分布,审计对账一次过。", None),
        ("s-expand-objection", "expand",  "objection",   "跨部门管理复杂度","理解您的顾虑,我们有一键模板方案:您确定总预算和各部门占比后,我们帮配好独立密钥和监控看板。每个部门拿到开箱即用的密钥,不用他们额外配合,您在后管平台就能看到全貌。", "跨部门协调太麻烦,业务部门不好配合"),
        ("s-silent-opening",   "silent",  "opening",     "用量下滑诊断",  "{contact}您好,看到贵司近两个月用量有所下滑,想跟您了解一下是不是当前的方案不太匹配了。我们可以一起看看问题出在哪,调整个更适合的方案。", None),
        ("s-silent-selling",   "silent",  "sellingPoint","轻量套餐 + 按量灵活","如果包年包月的压力太大,可以切到按量付费,用多少付多少,没有硬性最低消费。另外我们还有轻量入门套餐,月费不到原来一半,核心能力保留,等业务恢复再升回去也方便。", None),
        ("s-silent-objection", "silent",  "objection",   "预算不足",     "完全理解,预算收紧时我们都经历过。要不这样——我帮您开一个最低成本的保号方案,月付几十块保留账号和数据配置,这样等预算恢复时可以直接复用,不用重新对接。总比到时候重新接入省事得多。", "预算砍了,暂时不需要了"),
        ("s-newlead-opening",  "newLead", "opening",     "行业切入建立信任","{contact}您好,我是天翼云的客户经理。了解到贵司在{industry}领域有 AI 能力需求,我们刚帮同行业的几家企业做了落地。方便的话我介绍一下我们能做什么、和市面上的方案有什么不同。", None),
        ("s-newlead-selling",  "newLead", "sellingPoint","零风险试用 + POC 支持","我们为前期客户提供零风险的试用方案——首月充值金额全额抵扣次月费用,效果不满意可以退费。另外我们还提供免费 POC 环境,您可以先把真实场景跑一遍,看到效果再做决定。", None),
        ("s-newlead-objection","newLead", "objection",   "已有供应商",   "理解,切换供应商确实要慎重。不过我们和别家最大的区别是:天翼云是直连备案模型,渠道纯度可出证明、可开正规增值税发票、数据不出境。您可以先拿一个非核心业务过来 POC,不用任何承诺,跑完对比一下延迟和稳定性,数据说话。", "我们已经在用别家的了"),
    ]
    conn.executemany(
        "INSERT INTO talk_scripts VALUES (?,?,?,?,?,?)", scripts
    )

    # ---------- 系统配置 ----------
    config = json.dumps({
        "asr": "asr-tianyi",
        "chatbot": "qwen-plus",
        "intent": "qwen-plus",
        "summary": "qwen-max",
        "selection": "deepseek-v3",
    }, ensure_ascii=False)
    conn.execute(
        "INSERT INTO system_config VALUES (?,?)",
        ("system_model_bindings", config)
    )

    # ---------- 管理大屏 ----------
    dashboard_stats = [
        ("客户经理人效(单人月签约)", "31", "较基线 +13", "up", "efficiency", json.dumps([18, 19, 21, 24, 27, 31])),
        ("续费率", "91%", "目标 93%", "up", "renew", json.dumps([82, 85, 86, 88, 90, 91])),
        ("推荐采纳率", "68%", "较基线 +23%", "up", "adoption", json.dumps([45, 50, 55, 60, 64, 68])),
        ("选型相关客诉率", "3%", "较基线 -5%(越低越好)", "down", "complaint", json.dumps([8, 7, 6, 5, 4, 3])),
    ]
    conn.executemany(
        "INSERT INTO dashboard_stats (label,value,hint,trend,icon,series_json) VALUES (?,?,?,?,?,?)",
        dashboard_stats
    )

    efficiency = [("1月", 18), ("2月", 19), ("3月", 21), ("4月", 24), ("5月", 27), ("6月", 31)]
    conn.executemany("INSERT INTO dashboard_efficiency (date,value) VALUES (?,?)", efficiency)

    funnel = [("线索", 320), ("商机", 168), ("报价", 92), ("成交", 47)]
    conn.executemany("INSERT INTO dashboard_funnel (label,value) VALUES (?,?)", funnel)

    trust_metrics = [
        ("renewRate", "续费率", 0.91, "%", 0.82, 0.93, json.dumps([{"date":"1月","value":82},{"date":"2月","value":85},{"date":"3月","value":86},{"date":"4月","value":88},{"date":"5月","value":90},{"date":"6月","value":91}])),
        ("expandRate", "扩容率", 0.34, "%", 0.21, 0.4, None),
        ("adoptionRate", "推荐采纳率", 0.68, "%", 0.45, 0.75, None),
        ("complaintRate", "选型相关客诉率", 0.03, "%", 0.08, 0.02, None),
    ]
    conn.executemany(
        "INSERT INTO dashboard_trust_metrics (key,label,value,unit,baseline,target,series_json) VALUES (?,?,?,?,?,?,?)",
        trust_metrics
    )

    # ---------- 用量趋势(演示数据) ----------
    _usage_data = {
        "c-1024": [(182, 196, 175, 224, 268, 312), ("1月","2月","3月","4月","5月","6月")],
        "c-1031": [(42, 58, 74, 105, 148, 196), ("1月","2月","3月","4月","5月","6月")],
        "c-1042": [(420, 480, 560, 720, 910, 1150), ("1月","2月","3月","4月","5月","6月")],
        "c-1055": [(88, 76, 52, 38, 28, 22), ("1月","2月","3月","4月","5月","6月")],
    }
    for cid, (vals, labels) in _usage_data.items():
        for i, (v, l) in enumerate(zip(vals, labels)):
            conn.execute(
                "INSERT OR IGNORE INTO customer_usage VALUES (?,?,?,?)",
                (f"usage-{cid}-{i}", cid, l, v)
            )

    # ---------- 推荐选型(演示数据) ----------
    conn.execute(
        """INSERT OR IGNORE INTO recommendations
           (id, customer_id, rec_type, title, target_model_id, target_plan_id,
            reason, quote_min, quote_max, evidence_json, sort_order)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ("r-1", "c-1024", "renew",
         "续约「通义千问-Max 包年企业版」并锁价", "通义千问-Max", "包年企业版",
         "近 3 个月用量稳定上行、可用率 99.8%,当前型号最配其低延迟需求;包年锁价规避调价波动。",
         180000, 210000, json.dumps({
             "formula": "综合分 = 能力分 × 可用率 × 成本系数", "score": 96.4,
             "factors": [
                 {"key":"capability","label":"能力分","value":92,"display":"92","source":{"label":"天翼云模型评测台 / 2026Q2 基准集","collectedAt":"2026-05-30"}},
                 {"key":"availability","label":"可用率","value":0.998,"display":"99.8%","source":{"label":"可用性监控 · 30 天滚动","collectedAt":"2026-06-08"}},
                 {"key":"costFactor","label":"成本系数","value":1.05,"display":"×1.05","source":{"label":"定价知识库 · 包年折扣","collectedAt":"2026-06-01"}},
             ],
         }, ensure_ascii=False), 0)
    )
    conn.execute(
        """INSERT OR IGNORE INTO recommendations
           (id, customer_id, rec_type, title, target_model_id, target_plan_id,
            reason, quote_min, quote_max, evidence_json, sort_order)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ("r-2", "c-1024", "addon",
         "加推「行业 MCP + 质检 Agent」增值包", "通义千问-Max", None,
         "制造质检场景用量集中,叠加行业 MCP 可提升落地效果,属高价值增量,采纳率历史偏高。",
         36000, 52000, json.dumps({
             "formula": "综合分 = 场景匹配 × 落地确定性 × 增值系数", "score": 88.2,
             "factors": [
                 {"key":"fit","label":"场景匹配","value":0.94,"display":"94%","source":{"label":"客户用量画像 · 质检类调用占比","collectedAt":"2026-06-07"}},
                 {"key":"certainty","label":"落地确定性","value":0.92,"display":"92%","source":{"label":"同行业落地案例库","collectedAt":"2026-05-20"}},
                 {"key":"valueFactor","label":"增值系数","value":1.02,"display":"×1.02","source":{"label":"增值产品策略","collectedAt":"2026-06-01"}},
             ],
         }, ensure_ascii=False), 1)
    )

    # ---------- 通话会话 + 转写 + 意图(演示数据) ----------
    conn.execute(
        """INSERT OR IGNORE INTO copilot_sessions VALUES (?,?,?,?)""",
        ("sess-c-1024", "c-1024",
         "客户确认续约「通义千问-Max 包年企业版」,接受包年锁价;对质检 Agent 增值包有明确兴趣,需补发方案。比价异议已用合规 + 锁价话术化解。",
         34)
    )
    _transcripts = [
        ("manager", "周经理您好,这季度贵司调用量涨了约 40%,稳定性一直 99.8%,今天想和您过一下续约。", 0, 0),
        ("customer", "嗯,量确实涨了。不过最近财务在压成本,续约这块预算卡得紧。", 3, 1),
        ("manager", "理解,我们可以包年锁价,后面调价不影响您,预算更好做。", 7, 2),
        ("customer", "说到这个,我看市面上有些中转便宜不少,你们价格能不能再松松?", 11, 3),
        ("manager", "便宜的多是逆向渠道、随时跳价甚至跑路。我们是备案直连、渠道纯度可出证明,还能开正规发票。", 16, 4),
        ("customer", "发票和合规这块我们确实必须要。对了,我们质检那边想试试更智能的方案。", 21, 5),
        ("manager", "正好,我们有行业 MCP + 质检 Agent 的增值包,同行业落地效果不错,我回头给您发个方案。", 26, 6),
        ("customer", "可以,那续约我们走起,增值包也发我看看。", 31, 7),
    ]
    for sp, txt, at, ord in _transcripts:
        conn.execute(
            "INSERT OR IGNORE INTO session_transcripts (session_id, speaker, text, at_sec, sort_order) VALUES (?,?,?,?,?)",
            ("sess-c-1024", sp, txt, at, ord)
        )
    _intents = [
        (3, "medium", "成本敏感", "客户提到财务压成本,预算紧", None, None),
        (11, "medium", "价格异议", "拿中转比价施压", "r-1", "s-renew-objection"),
        (21, "high", "质检新需求", "主动抛出质检智能化诉求", "r-2", None),
        (31, "high", "成交信号", "确认续约 + 索要增值包方案", None, None),
    ]
    for at, lvl, need, note, trig_rec, trig_scr in _intents:
        conn.execute(
            "INSERT OR IGNORE INTO session_intents (session_id, at_sec, level, need_type, note, triggers_recommendation_id, triggers_script_id) VALUES (?,?,?,?,?,?,?)",
            ("sess-c-1024", at, lvl, need, note, trig_rec, trig_scr)
        )

    # ---------- 计费明细(演示数据) ----------
    import random as _rand
    from datetime import datetime as _dt, timedelta as _td
    _model_names_b = [r["name"] for r in conn.execute("SELECT name FROM models").fetchall()]
    _now_b = _dt.now()
    # C 端
    for i in range(30):
        d = _now_b - _td(days=i)
        m = _rand.choice(_model_names_b)
        inp = _rand.randint(5000, 50000)
        out = _rand.randint(2000, 30000)
        up = round(_rand.uniform(0.01, 0.09), 4)
        amt = round(((inp + out) / 1000) * up, 2)
        conn.execute(
            "INSERT OR IGNORE INTO billing_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"bill-c-{i}", d.strftime("%Y-%m-%d"), m, m, _rand.choice(["默认 Key", "个人 Key-01", "个人 Key-02"]),
             inp + out, inp, out, amt, up, "payg", None)
        )
    # 企业客户
    _ek = {"c-1024": ["生产环境 Key", "测试环境 Key", "质检 Agent Key"],
           "c-1031": ["主 Key", "内容生产 Key"],
           "c-1042": ["核心交易 Key", "合规审计 Key", "数据分析 Key", "风控 Key"],
           "c-1055": ["通用 Key"]}
    for cid, keys in _ek.items():
        days = 90 if cid == "c-1042" else 60
        for i in range(days):
            d = _now_b - _td(days=i)
            m = _rand.choice(_model_names_b)
            inp = _rand.randint(20000, 200000)
            out = _rand.randint(10000, 120000)
            up = round(_rand.uniform(0.01, 0.09), 4)
            amt = round(((inp + out) / 1000) * up, 2)
            conn.execute(
                "INSERT OR IGNORE INTO billing_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"bill-{cid}-{i}", d.strftime("%Y-%m-%d"), m, m, _rand.choice(keys),
                 inp + out, inp, out, amt, up, "payg", cid)
            )
