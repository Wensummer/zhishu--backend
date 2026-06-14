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
            monthly_spend   REAL,
            telecom_products TEXT NOT NULL DEFAULT '[]',
            enterprise_info_json TEXT NOT NULL DEFAULT '{}'
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


# ============ 企业画像种子数据(JSON 格式,存入 customers.enterprise_info_json) ============

_ENTERPRISE_C1024 = {
    "profile": {"name": "云帆智造科技", "creditCode": "91320115MA25XXXXXX", "legalPerson": "张建国", "registeredCapital": "5000万元人民币", "establishDate": "2015-03-12", "businessStatus": "存续", "address": "江苏省南京市江宁区智能制造产业园A区8号", "businessScope": "智能制造技术研发;工业互联网平台建设;AI质检系统开发;自动化设备生产与销售;计算机软硬件技术开发、技术咨询、技术转让", "contactPerson": "周经理", "contactPhone": "138****5523"},
    "personnel": [{"name": "张建国", "title": "董事长兼总经理"}, {"name": "李华", "title": "技术总监"}, {"name": "周晓", "title": "采购经理"}, {"name": "王芳", "title": "财务负责人"}],
    "shareholders": [{"name": "张建国", "ratio": "55%", "amount": "2750万元"}, {"name": "南京智造产业投资基金", "ratio": "25%", "amount": "1250万元"}, {"name": "李华", "ratio": "12%", "amount": "600万元"}, {"name": "员工持股平台", "ratio": "8%", "amount": "400万元"}],
    "controller": {"name": "张建国", "ratio": "55%", "path": "直接持股55%"},
    "branches": [{"name": "云帆智造(苏州)科技有限公司", "ratio": "100%", "amount": "1000万元", "businessStatus": "存续"}, {"name": "云帆智造(深圳)研发中心", "ratio": "100%", "amount": "500万元", "businessStatus": "存续"}, {"name": "南京云帆工业互联网有限公司", "ratio": "60%", "amount": "300万元", "businessStatus": "存续"}],
    "honors": [{"name": "国家高新技术企业", "issuer": "科学技术部", "date": "2023-10"}, {"name": "江苏省专精特新中小企业", "issuer": "江苏省工信厅", "date": "2024-06"}, {"name": "ISO 9001质量管理体系认证", "issuer": "SGS", "date": "2024-03"}, {"name": "江苏省智能制造示范车间", "issuer": "江苏省工信厅", "date": "2025-01"}],
    "funding": [{"round": "天使轮", "amount": "2000万元", "date": "2020-08", "investors": "深创投"}, {"round": "A轮", "amount": "8000万元", "date": "2022-05", "investors": "达晨创投、真格基金"}, {"round": "B轮", "amount": "2亿元", "date": "2026-03", "investors": "红杉中国"}],
    "risks": [{"type": "裁判文书", "title": "买卖合同纠纷(原告)", "date": "2025-09-15", "amount": "42万元", "department": "南京市江宁区人民法院", "detail": "与供应商就设备货款纠纷,已庭外和解撤诉"}, {"type": "行政处罚", "title": "消防设施未定期检测", "date": "2025-06-20", "amount": "1.5万元", "department": "江宁区消防救援大队", "detail": "罚款1.5万元,已整改"}],
    "news": [{"title": "云帆智造AI质检系统获2026年度江苏省工业互联网示范项目", "url": "#", "date": "2026-05-28", "sentiment": "positive", "summary": "云帆智造自主研发的AI质检系统入选省级示范项目,将在全省制造业推广。"}, {"title": "云帆智造完成B轮融资 估值超20亿元", "url": "#", "date": "2026-03-15", "sentiment": "positive", "summary": "本轮融资由红杉中国领投,资金将用于AI大模型在工业场景的深度落地。"}, {"title": "云帆智造与南京理工大学共建智能制造联合实验室", "url": "#", "date": "2025-12-08", "sentiment": "positive", "summary": "校企合作聚焦工业视觉检测与AI质检算法研究。"}],
    "ipr": [{"type": "patent", "name": "基于深度学习的工业缺陷检测方法及系统", "regNo": "CN202510XXXXXX.X", "status": "授权", "applyDate": "2025-06-15"}, {"type": "patent", "name": "多模态数据融合的产品质量评估装置", "regNo": "CN202510XXXXXX.Y", "status": "实审", "applyDate": "2026-01-20"}, {"type": "trademark", "name": "云帆智造 YUNFAN", "regNo": "第9类", "status": "注册", "applyDate": "2024-08-01"}, {"type": "copyright", "name": "云帆AI质检管理平台 V3.0", "regNo": "软著2025XXXXXX", "status": "登记", "applyDate": "2025-09-10"}],
    "bids": [{"title": "江苏省制造业数字化转型公共服务平台建设项目", "publishDate": "2026-04-10", "amount": "680万元", "buyer": "江苏省工业和信息化厅"}, {"title": "南京经开区智慧工厂AI质检系统采购项目", "publishDate": "2025-11-20", "amount": "245万元", "buyer": "南京经济技术开发区管委会"}],
}
_ENTERPRISE_C1031 = {
    "profile": {"name": "锦书文化传媒", "creditCode": "91310115MA1KXXXXXX", "legalPerson": "林锦", "registeredCapital": "1000万元人民币", "establishDate": "2019-07-22", "businessStatus": "存续", "address": "上海市浦东新区张江高科技园区博云路58号", "businessScope": "文化艺术交流策划;数字内容制作;新媒体运营;广告设计、制作、代理、发布;影视策划;技术进出口", "contactPerson": "林总", "contactPhone": "139****2108"},
    "personnel": [{"name": "林锦", "title": "CEO"}, {"name": "陈思", "title": "COO"}, {"name": "张巍", "title": "技术总监"}],
    "shareholders": [{"name": "林锦", "ratio": "70%", "amount": "700万元"}, {"name": "上海文化产业发展基金", "ratio": "20%", "amount": "200万元"}, {"name": "陈思", "ratio": "10%", "amount": "100万元"}],
    "controller": {"name": "林锦", "ratio": "70%", "path": "直接持股70%"},
    "branches": [{"name": "锦书文化(北京)分公司", "ratio": "100%", "amount": "—", "businessStatus": "存续"}, {"name": "锦书文化(杭州)内容制作中心", "ratio": "100%", "amount": "200万元", "businessStatus": "存续"}],
    "honors": [{"name": "上海市文化企业十佳", "issuer": "上海市委宣传部", "date": "2026-05"}, {"name": "国家高新技术企业", "issuer": "科学技术部", "date": "2024-12"}, {"name": "ISO 27001信息安全管理体系认证", "issuer": "SGS", "date": "2025-06"}],
    "funding": [{"round": "种子轮", "amount": "500万元", "date": "2019-10", "investors": "个人投资者"}, {"round": "Pre-A轮", "amount": "2000万元", "date": "2021-07", "investors": "紫竹创投"}],
    "risks": [{"type": "经营异常", "title": "通过登记的住所无法联系", "date": "2023-04-10", "department": "浦东新区市场监督管理局", "detail": "已变更登记地址后移出异常名录"}],
    "news": [{"title": "锦书文化获2026年「上海文化企业十佳」称号", "url": "#", "date": "2026-05-10", "sentiment": "positive", "summary": "锦书文化凭借AIGC内容生产效率优势,入选上海市文化企业十佳。"}, {"title": "锦书文化AIGC内容平台上线,日产10万条营销文案", "url": "#", "date": "2026-02-18", "sentiment": "positive", "summary": "基于大模型的内容生成平台正式上线,客户内容生产效率提升3倍。"}],
    "ipr": [{"type": "trademark", "name": "锦书 JINSHU", "regNo": "第35类", "status": "注册", "applyDate": "2020-03-15"}, {"type": "trademark", "name": "锦书 JINSHU", "regNo": "第41类", "status": "注册", "applyDate": "2020-03-15"}, {"type": "copyright", "name": "锦书AIGC内容管理系统 V2.0", "regNo": "软著2025XXXXXX", "status": "登记", "applyDate": "2025-11-05"}],
    "bids": [{"title": "上海城市形象数字化传播内容制作项目", "publishDate": "2026-01-15", "amount": "180万元", "buyer": "上海市委宣传部"}],
}
_ENTERPRISE_C1042 = {
    "profile": {"name": "恒生金服数科", "creditCode": "91330100MA2XXXXXX", "legalPerson": "陈国栋", "registeredCapital": "2亿元人民币", "establishDate": "2017-01-08", "businessStatus": "存续", "address": "浙江省杭州市滨江区网商路599号", "businessScope": "金融科技领域技术开发;数据处理与存储服务;计算机系统集成;人工智能应用软件开发;企业征信服务;信息安全技术开发", "contactPerson": "吴总监", "contactPhone": "136****8801"},
    "personnel": [{"name": "陈国栋", "title": "董事长"}, {"name": "徐明", "title": "总经理"}, {"name": "吴涛", "title": "技术总监"}, {"name": "刘敏", "title": "合规总监"}, {"name": "郑红", "title": "财务总监"}],
    "shareholders": [{"name": "恒生电子股份有限公司", "ratio": "60%", "amount": "1.2亿元"}, {"name": "杭州金投集团", "ratio": "20%", "amount": "4000万元"}, {"name": "核心管理团队", "ratio": "15%", "amount": "3000万元"}, {"name": "其他股东", "ratio": "5%", "amount": "1000万元"}],
    "controller": {"name": "恒生电子股份有限公司", "ratio": "60%", "path": "通过恒生电子间接控制"},
    "branches": [{"name": "恒生金服(上海)科技有限公司", "ratio": "100%", "amount": "5000万元", "businessStatus": "存续"}, {"name": "恒生金服(北京)研发分公司", "ratio": "100%", "amount": "—", "businessStatus": "存续"}, {"name": "恒生金服(深圳)子公司", "ratio": "100%", "amount": "3000万元", "businessStatus": "存续"}, {"name": "杭州恒金信息技术有限公司", "ratio": "51%", "amount": "510万元", "businessStatus": "存续"}],
    "honors": [{"name": "国家高新技术企业", "issuer": "科学技术部", "date": "2020-12"}, {"name": "ISO 27001信息安全管理体系认证", "issuer": "SGS", "date": "2026-04"}, {"name": "CMMI L3软件能力成熟度认证", "issuer": "CMMI Institute", "date": "2024-08"}, {"name": "浙江省高新技术企业研究开发中心", "issuer": "浙江省科技厅", "date": "2024-12"}, {"name": "金融科技创新十佳案例", "issuer": "中国金融科技峰会", "date": "2025-11"}],
    "funding": [{"round": "天使轮", "amount": "5000万元", "date": "2017-06", "investors": "恒生电子、杭州金投"}, {"round": "A轮", "amount": "2亿元", "date": "2019-03", "investors": "国开金融、浙商创投"}],
    "risks": [],
    "news": [{"title": "恒生金服数科获ISO 27001信息安全管理体系认证", "url": "#", "date": "2026-04-22", "sentiment": "positive", "summary": "通过国际信息安全管理体系认证,数据安全能力达到国际标准。"}, {"title": "恒生金服数科与多家银行达成智能风控合作", "url": "#", "date": "2026-03-01", "sentiment": "positive", "summary": "与招商银行、浦发银行签署智能风控系统合作协议。"}, {"title": "浙江省金融科技协会授予恒生金服年度创新奖", "url": "#", "date": "2025-11-15", "sentiment": "positive", "summary": "恒生金服数科在金融大模型应用领域的创新成果获行业认可。"}],
    "ipr": [{"type": "patent", "name": "基于联邦学习的跨机构风控建模方法", "regNo": "CN202410XXXXXX.X", "status": "授权", "applyDate": "2024-08-20"}, {"type": "patent", "name": "金融知识图谱构建方法与系统", "regNo": "CN202510XXXXXX.Z", "status": "实审", "applyDate": "2025-03-10"}, {"type": "trademark", "name": "恒金风控", "regNo": "第36类", "status": "注册", "applyDate": "2023-06-01"}, {"type": "trademark", "name": "恒金数智", "regNo": "第9类", "status": "注册", "applyDate": "2024-01-15"}, {"type": "copyright", "name": "恒生金服智能风控平台 V4.0", "regNo": "软著2024XXXXXX", "status": "登记", "applyDate": "2024-12-01"}, {"type": "copyright", "name": "恒生金服合规审计系统 V2.0", "regNo": "软著2025XXXXXX", "status": "登记", "applyDate": "2025-07-20"}],
    "bids": [{"title": "招商银行智能风控系统二期建设项目", "publishDate": "2026-03-10", "amount": "1200万元", "buyer": "招商银行股份有限公司"}, {"title": "浙江省金融综合服务平台风险预警模块采购", "publishDate": "2025-10-15", "amount": "560万元", "buyer": "浙江省地方金融监督管理局"}, {"title": "浦发银行反欺诈模型升级项目", "publishDate": "2025-08-01", "amount": "850万元", "buyer": "上海浦东发展银行"}],
}
_ENTERPRISE_C1055 = {
    "profile": {"name": "蓝橙教育", "creditCode": "91320105MA1MXXXXXX", "legalPerson": "陈蓝", "registeredCapital": "500万元人民币", "establishDate": "2020-09-01", "businessStatus": "存续", "address": "江苏省南京市鼓楼区汉中门大街88号", "businessScope": "在线教育技术开发;教育软件销售;教育咨询服务;互联网信息服务;音视频制作与发行", "contactPerson": "陈老师", "contactPhone": "158****3421"},
    "personnel": [{"name": "陈蓝", "title": "创始人兼CEO"}, {"name": "孙蓓", "title": "运营总监"}, {"name": "赵刚", "title": "技术负责人"}],
    "shareholders": [{"name": "陈蓝", "ratio": "80%", "amount": "400万元"}, {"name": "孙蓓", "ratio": "15%", "amount": "75万元"}, {"name": "赵刚", "ratio": "5%", "amount": "25万元"}],
    "controller": {"name": "陈蓝", "ratio": "80%", "path": "直接持股80%"},
    "branches": [],
    "honors": [{"name": "江苏省科技型中小企业", "issuer": "江苏省科技厅", "date": "2023-05"}, {"name": "南京市创新型中小企业", "issuer": "南京市工信局", "date": "2024-03"}],
    "funding": [{"round": "种子轮", "amount": "300万元", "date": "2020-10", "investors": "个人投资者"}],
    "risks": [{"type": "经营异常", "title": "未按期公示年度报告", "date": "2025-07-01", "department": "江苏省市场监督管理局", "detail": "已补报并移出异常名录"}, {"type": "裁判文书", "title": "教育培训合同纠纷(被告)", "date": "2025-04-20", "amount": "8万元", "department": "南京市鼓楼区人民法院", "detail": "用户退费纠纷,经调解达成退费协议"}],
    "news": [{"title": "「双减」政策持续影响,在线教育行业进入存量竞争", "url": "#", "date": "2026-05-06", "sentiment": "negative", "summary": "行业整体收缩,蓝橙教育也在调整业务线,关停了部分学科辅导板块。"}, {"title": "蓝橙教育转型素质教育,推出AI编程课程", "url": "#", "date": "2025-10-20", "sentiment": "positive", "summary": "积极响应政策导向,新上线AI编程与机器人教育课程,探索素质教育新方向。"}],
    "ipr": [{"type": "trademark", "name": "蓝橙 LANCHE", "regNo": "第41类", "status": "注册", "applyDate": "2021-05-10"}, {"type": "copyright", "name": "蓝橙在线课堂系统 V3.0", "regNo": "软著2023XXXXXX", "status": "登记", "applyDate": "2023-08-15"}, {"type": "copyright", "name": "蓝橙AI编程教学平台 V1.0", "regNo": "软著2025XXXXXX", "status": "登记", "applyDate": "2025-11-20"}],
    "bids": [],
}
_ENTERPRISE_C2003 = {
    "profile": {"name": "途新出行", "creditCode": "91310112MA1GXXXXXX", "legalPerson": "赵新", "registeredCapital": "3000万元人民币", "establishDate": "2022-04-18", "businessStatus": "存续", "address": "上海市闵行区紫竹科学园区紫星路588号", "businessScope": "网络预约出租汽车经营服务;智能出行平台开发;车载智能终端研发;大数据分析应用;人工智能技术开发", "contactPerson": "赵经理", "contactPhone": "177****6699"},
    "personnel": [{"name": "赵新", "title": "创始人兼CEO"}, {"name": "王磊", "title": "CTO"}, {"name": "张悦", "title": "运营VP"}],
    "shareholders": [{"name": "赵新", "ratio": "60%", "amount": "1800万元"}, {"name": "顺为资本", "ratio": "25%", "amount": "750万元"}, {"name": "核心团队期权池", "ratio": "15%", "amount": "450万元"}],
    "controller": {"name": "赵新", "ratio": "60%", "path": "直接持股60%"},
    "branches": [{"name": "途新出行(杭州)技术研发中心", "ratio": "100%", "amount": "500万元", "businessStatus": "存续"}],
    "honors": [{"name": "上海市科技型中小企业", "issuer": "上海市科委", "date": "2024-07"}],
    "funding": [{"round": "天使轮", "amount": "3000万元", "date": "2026-01", "investors": "顺为资本"}],
    "risks": [],
    "news": [{"title": "途新出行获网约车全国运营牌照", "url": "#", "date": "2026-05-20", "sentiment": "positive", "summary": "途新出行获得交通运输部颁发的全国网约车运营资质,业务版图即将扩张。"}, {"title": "途新出行完成天使轮融资3000万元", "url": "#", "date": "2026-01-10", "sentiment": "positive", "summary": "由顺为资本领投,资金用于智能调度系统和AI客服平台建设。"}, {"title": "途新出行与高德地图达成战略合作", "url": "#", "date": "2025-11-05", "sentiment": "positive", "summary": "双方将在路线规划、实时路况和智能推荐方面展开深度合作。"}],
    "ipr": [{"type": "patent", "name": "基于供需预测的网约车智能调度方法", "regNo": "CN202510XXXXXX.W", "status": "实审", "applyDate": "2025-09-15"}, {"type": "trademark", "name": "途新出行 TUXING", "regNo": "第39类", "status": "注册", "applyDate": "2024-06-01"}, {"type": "copyright", "name": "途新出行调度管理平台 V2.0", "regNo": "软著2025XXXXXX", "status": "登记", "applyDate": "2025-06-30"}],
    "bids": [{"title": "上海市闵行区智慧出行综合服务平台采购", "publishDate": "2026-03-01", "amount": "320万元", "buyer": "上海市闵行区交通委员会"}],
}


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
        ("c-1024", "云帆智造科技", "智能制造", 0, "通义千问-Max",  "包年企业版",  38000,  "2026-07-15", "renew",  json.dumps(["高活跃", "对延迟敏感"], ensure_ascii=False), "m-01", "周经理", 24800, json.dumps(["天翼云专线", "天翼云会议", "天翼云安全·WAF"], ensure_ascii=False), json.dumps(_ENTERPRISE_C1024, ensure_ascii=False)),
        ("c-1031", "锦书文化传媒", "内容/营销", 0, "DeepSeek-V3",  "按量标准版",  6200,   "2026-06-28", "upgrade", json.dumps(["用量上涨", "可加推 Agent"], ensure_ascii=False), "m-01", "林总", 15600, json.dumps(["天翼云CDN", "天翼云媒体存储", "天翼云安全·DDoS高防"], ensure_ascii=False), json.dumps(_ENTERPRISE_C1031, ensure_ascii=False)),
        ("c-1042", "恒生金服数科", "金融科技", 0, "文心一言-4.0", "包年企业版", 120000, "2026-09-30", "expand",  json.dumps(["多部门扩容", "合规要求高"], ensure_ascii=False), "m-01", "吴总监", 86000, json.dumps(["天翼云SSL证书", "天翼云容灾备份", "天翼云数据库RDS"], ensure_ascii=False), json.dumps(_ENTERPRISE_C1042, ensure_ascii=False)),
        ("c-1055", "蓝橙教育",     "在线教育", 0, "智谱 GLM-4",   "按量标准版",  800,    "2026-06-12", "silent",  json.dumps(["用量下滑", "余额不足"], ensure_ascii=False), "m-01", "陈老师", 3200, json.dumps(["天翼云轻量服务器", "天翼云企业邮箱"], ensure_ascii=False), json.dumps(_ENTERPRISE_C1055, ensure_ascii=False)),
        ("c-2003", "途新出行",     "出行/物流", 1, None, None, None, None, "newLead", json.dumps(["官网咨询", "待画像"], ensure_ascii=False), "m-01", "赵经理", None, json.dumps(["天翼云企业宽带", "天翼云总机"], ensure_ascii=False), json.dumps(_ENTERPRISE_C2003, ensure_ascii=False)),
    ]
    for c in customers:
        conn.execute(
            "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", c
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
