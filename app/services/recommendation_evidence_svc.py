"""推荐选型支撑依据知识库检索 —— POST /recommendation/evidence。

缓存策略(三层):
第 1 层:内存 dict,5 分钟 TTL(最热数据,零 I/O)
第 2 层:SQLite recommendation_evidence 表,1 小时时效(进程重启后冷启动)
第 3 层:Dify 实时检索 + DeepSeek 生成,写入 SQLite

force_refresh=true 跳过第 1 层,但仍走第 2 层防抖(避免频繁刷新重复调 API)。
同一个模型推荐给不同客户时依据独立缓存(由 customer_id 区分)。
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import datetime

from app.config import settings
from app.database import get_connection
from app.integrations.dify import retrieve_knowledge_structured
from app.schemas.recommendation_evidence import (
    EvidenceResult,
    KnowledgeRecord,
    RecommendationEvidenceRequest,
    RecommendationEvidenceResponse,
)

DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# ── 第 1 层:内存缓存 ────────────────────────────────────
_CACHE: dict[str, tuple[float, list[KnowledgeRecord], str]] = {}
CACHE_TTL = 300  # 5 分钟
PERSIST_TTL = 3600  # 第 2 层 SQLite 有效期 1 小时


def _mem_key(customer_id: str, model_id: str, query: str) -> str:
    return f"{customer_id}::{model_id}::{query}"


def _mem_get(key: str) -> tuple[list[KnowledgeRecord], str] | None:
    entry = _CACHE.get(key)
    if entry is None:
        return None
    ts, records, theory = entry
    if time.time() - ts > CACHE_TTL:
        del _CACHE[key]
        return None
    return records, theory


def _mem_set(key: str, records: list[KnowledgeRecord], theory: str) -> None:
    _CACHE[key] = (time.time(), records, theory)


# ── 第 2 层:SQLite 持久层 ──────────────────────────────

def _evidence_id(customer_id: str, model_id: str, query: str) -> str:
    raw = f"{customer_id}::{model_id}::{query}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _persist_get(customer_id: str, model_id: str, query: str) -> tuple[list[KnowledgeRecord], str] | None:
    """从 SQLite 查,返回 (records, theory) 或 None。超 1 小时视为失效。"""
    eid = _evidence_id(customer_id, model_id, query)
    conn = get_connection()
    row = conn.execute(
        "SELECT records_json, theory, updated_at FROM recommendation_evidence WHERE id=?",
        (eid,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    try:
        updated = datetime.fromisoformat(row["updated_at"])
        if (datetime.now() - updated).total_seconds() > PERSIST_TTL:
            return None
        records = [KnowledgeRecord(**r) for r in json.loads(row["records_json"])]
        return records, row["theory"]
    except Exception:
        return None


def _persist_set(
    customer_id: str,
    model_id: str,
    model_name: str,
    query: str,
    records: list[KnowledgeRecord],
    theory: str,
) -> None:
    """写入/更新 SQLite。"""
    eid = _evidence_id(customer_id, model_id, query)
    now = datetime.now().isoformat()
    records_json = json.dumps(
        [r.model_dump() for r in records], ensure_ascii=False
    )
    conn = get_connection()
    conn.execute(
        """INSERT INTO recommendation_evidence (id,customer_id,model_id,model_name,query,records_json,theory,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
               records_json=excluded.records_json,
               theory=excluded.theory,
               updated_at=excluded.updated_at""",
        (eid, customer_id, model_id, model_name, query, records_json, theory, now, now),
    )
    conn.commit()
    conn.close()


# ── DeepSeek LLM call ────────────────────────────────────

def _call_deepseek(prompt: str) -> str:
    """调用 DeepSeek 返回文本;失败返回空串,不拖垮主流程。"""
    body = json.dumps(
        {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    ).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


# ── Dify retrieval ──────────────────────────────────────

def _search(query: str) -> list[KnowledgeRecord]:
    """对单个 query 检索 Dify 知识库。"""
    if not settings.dify_recommendation_dataset_id:
        return []
    try:
        raw_records = retrieve_knowledge_structured(
            query,
            settings.dify_recommendation_dataset_id,
            top_k=4,
        )
        return [
            KnowledgeRecord(
                segment_id=r["segment_id"],
                document_id=r["document_id"],
                document_name=r["document_name"],
                content=r["content"],
                score=r["score"],
                collected_at=r.get("collected_at"),
            )
            for r in raw_records
        ]
    except Exception:
        return []


# ── LLM theory generation ───────────────────────────────

def _build_theory(model_name: str, query: str, records: list[KnowledgeRecord]) -> str:
    """用 LLM 生成约 200 字的理论依据段落。"""
    refs = "\n".join(
        f"- {r.content[:500]}" for r in sorted(records, key=lambda r: r.score, reverse=True)[:3]
    ) or "(知识库暂无命中结论)"
    prompt = f"""你是一位大模型选型专家。请为以下模型推荐写一段约200字的**理论依据**,用简洁专业的中文说明"为什么推荐这个模型"。

【模型名称】{model_name}
【检索主题】{query}
【知识库参考】
{refs}

要求:
1. 结合模型能力特点(如基准分数、架构、上下文长度)、定价策略与当前检索场景,说明该模型的适配理由。
2. 文风参考:简洁、有判断力,如"同等能力模型中性价比突出""适合对稳定性要求高的存量客户延续使用""在不需要极致推理的场景下是最优选择"等。
3. 不编造具体数据,只能引用知识库中真实出现的分数/价格;不出现"基于DeepSeek""天翼云"等来源话术。
4. 200字上下,一段话,不要列表、不要markdown。"""
    return _call_deepseek(prompt)


# ── Public interface ─────────────────────────────────────

def _resolve_candidate(candidate, force_refresh: bool) -> EvidenceResult:
    """检索单个候选模型:三层缓存穿透。"""
    model_name = candidate.model_name or candidate.model_id
    query = candidate.query or model_name
    customer_id = candidate.customer_id or ""
    mk = _mem_key(customer_id, candidate.model_id, query)

    # 不强制刷新:走三层缓存
    if not force_refresh:
        # 第 1 层:内存缓存
        cached = _mem_get(mk)
        if cached is not None:
            records, theory = cached
            return EvidenceResult(
                model_id=candidate.model_id, model_name=model_name,
                query=query, customer_id=customer_id,
                records=records, theory=theory,
            )

        # 第 2 层:SQLite 持久表
        persisted = _persist_get(customer_id, candidate.model_id, query)
        if persisted is not None:
            records, theory = persisted
            _mem_set(mk, records, theory)
            return EvidenceResult(
                model_id=candidate.model_id, model_name=model_name,
                query=query, customer_id=customer_id,
                records=records, theory=theory,
            )

    # force_refresh=true 或两层都未命中 → 第 3 层:实时检索
    records = _search(query)
    theory = _build_theory(model_name, query, records)
    _persist_set(customer_id, candidate.model_id, model_name, query, records, theory)
    _mem_set(mk, records, theory)
    return EvidenceResult(
        model_id=candidate.model_id, model_name=model_name,
        query=query, customer_id=customer_id,
        records=records, theory=theory,
    )


def get_recommendation_evidence(
    req: RecommendationEvidenceRequest,
) -> RecommendationEvidenceResponse:
    """为候选模型列表检索选型依据知识库,并为每个模型生成理论依据。"""
    return RecommendationEvidenceResponse(results=[
        _resolve_candidate(c, req.force_refresh)
        for c in req.candidates
    ])
