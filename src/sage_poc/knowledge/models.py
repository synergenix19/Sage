from dataclasses import dataclass, field


@dataclass
class KnowledgePassage:
    text: str
    source_id: str
    citation: str
    relevance_score: float

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "source_id": self.source_id,
            "citation": self.citation,
            "relevance_score": self.relevance_score,
        }


@dataclass
class KnowledgeResult:
    passages: list[KnowledgePassage] = field(default_factory=list)
    abstain: bool = False
    query_raw: str = ""       # query as submitted by the caller (pre-normalization)
    query_searched: str = ""  # query actually sent to the backend (post-normalization)
    top_similarity: float | None = None  # best cosine sim in the returned pack; drives abstain
