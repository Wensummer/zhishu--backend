"""Dify 知识库检索客户端(后端版)。

只做一件事:给定 query + dataset_id,从 Dify 语义检索回若干文本段落。
用途:话术生成时检索话术库 #3 的模板。失败不抛错(返回空),不拖垮主流程。

注:选型/定价是结构化数据走引擎,不走这里;这里只服务"文字走向量"的话术/技术库。
"""
import json
import urllib.request

from app.config import settings


def retrieve_knowledge(query: str, dataset_id: str, top_k: int = 3) -> list[str]:
    """语义检索,返回命中段落的正文列表(按相关度排序)。Dify 不可用时返回 []。"""
    if not settings.dify_dataset_api_key or not dataset_id:
        return []
    body = json.dumps(
        {
            "query": query,
            "retrieval_model": {
                "search_method": "semantic_search",
                "reranking_enable": False,
                "top_k": top_k,
                "score_threshold_enabled": True,
                "score_threshold": 0.3,
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{settings.dify_api_base_url}/datasets/{dataset_id}/retrieve",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.dify_dataset_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        return [r["segment"]["content"] for r in data.get("records", []) if r.get("segment")]
    except Exception:
        return []  # 检索失败不影响主流程
