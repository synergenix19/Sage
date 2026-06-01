from __future__ import annotations
import json
import logging
from sage_poc.knowledge.models import KnowledgePassage, KnowledgeResult
from sage_poc.knowledge.repository import KnowledgeRepository

_log = logging.getLogger(__name__)

# POC default: abstain only on zero-score (no subsystem returned any match at all).
# Calibrate with scripts/calibrate_retrieval_threshold.py once seed corpus >= 10 articles.
# Pre-production: add BGE-reranker-v2-m3 reranking pass after RRF (insert here).
KNOWLEDGE_ABSTAIN_THRESHOLD: float = 0.0

# Reciprocal Rank Fusion constant (k=60 is standard literature default).
_RRF_K = 60

_HYBRID_SQL = """
WITH vector_ranked AS (
    SELECT
        id,
        article_id,
        chunk_text,
        citation_metadata,
        ROW_NUMBER() OVER (ORDER BY chunk_embedding <=> $1::vector) AS vec_rank
    FROM public.knowledge_articles
    WHERE language = $2
    ORDER BY chunk_embedding <=> $1::vector
    LIMIT $3
),
text_ranked AS (
    SELECT
        id,
        article_id,
        chunk_text,
        citation_metadata,
        ROW_NUMBER() OVER (ORDER BY ts_rank_cd(chunk_tsv, query) DESC) AS txt_rank
    FROM public.knowledge_articles,
         plainto_tsquery($7::regconfig, $4) AS query
    WHERE language = $2
      AND chunk_tsv @@ query
    ORDER BY ts_rank_cd(chunk_tsv, query) DESC
    LIMIT $3
),
combined AS (
    SELECT
        COALESCE(v.id, t.id) AS id,
        COALESCE(v.article_id, t.article_id) AS article_id,
        COALESCE(v.chunk_text, t.chunk_text) AS chunk_text,
        COALESCE(v.citation_metadata, t.citation_metadata) AS citation_metadata,
        COALESCE(1.0 / ($5 + v.vec_rank), 0) +
        COALESCE(1.0 / ($5 + t.txt_rank), 0) AS rrf_score
    FROM vector_ranked v
    FULL OUTER JOIN text_ranked t ON v.id = t.id
)
SELECT article_id, chunk_text, citation_metadata, rrf_score
FROM combined
ORDER BY rrf_score DESC
LIMIT $6
"""


def _get_embedding(text: str) -> list[float]:
    from sage_poc.memory.embedding import get_embedding
    return get_embedding(text)


class PostgresKnowledgeRepository(KnowledgeRepository):
    def __init__(self, pool):
        self._pool = pool

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        top_k: int = 5,
    ) -> KnowledgeResult:
        # 'simple' tokenises on whitespace (language-agnostic); 'english' adds stemming+stopwords.
        tsconfig = "simple" if language == "ar" else "english"
        try:
            embedding = _get_embedding(query)
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    _HYBRID_SQL,
                    embedding_str,   # $1 vector
                    language,        # $2 language filter
                    top_k * 4,       # $3 per-subsystem limit (retrieve more, RRF selects top_k)
                    query,           # $4 full-text query
                    _RRF_K,          # $5 RRF k constant
                    top_k,           # $6 final limit
                    tsconfig,        # $7 FTS config ('simple' for ar, 'english' for en)
                )
        except Exception as exc:
            _log.warning("[knowledge] retrieval failed: %s", exc)
            return KnowledgeResult(passages=[], abstain=True)

        if not rows:
            return KnowledgeResult(passages=[], abstain=True)

        passages = []
        for row in rows:
            if row["rrf_score"] <= KNOWLEDGE_ABSTAIN_THRESHOLD:
                continue
            raw_meta = row["citation_metadata"] or {}
            meta = json.loads(raw_meta) if isinstance(raw_meta, str) else raw_meta
            passages.append(KnowledgePassage(
                text=row["chunk_text"],
                source_id=row["article_id"],
                citation=meta.get("citation", row["article_id"]),
                relevance_score=round(float(row["rrf_score"]), 4),
            ))

        # POC substitute: Postgres hybrid RRF stands in for v7-mandated Azure AI Search (BM25+vector) + BGE-reranker-v2-m3 (UAE North). Migrate pre-prod. See §20.1 CKPT-REGION.
        # TODO: add BGE-reranker-v2-m3 reranking pass here (pre-production, corpus > 100 articles)
        return KnowledgeResult(passages=passages, abstain=len(passages) == 0)
