from dataclasses import dataclass, field


@dataclass
class KnowledgePassage:
    text: str
    source_id: str
    citation: str
    relevance_score: float
    source_url: str = ""    # article link from citation_metadata
    title: str = ""         # article title from citation_metadata
    video_url: str = ""     # canonical (provider-agnostic) video URL, "" when none

    def to_dict(self) -> dict:
        return {
            "text": self.text, "source_id": self.source_id, "citation": self.citation,
            "relevance_score": self.relevance_score,
            "source_url": self.source_url, "title": self.title, "video_url": self.video_url,
        }


@dataclass
class KnowledgeResult:
    passages: list[KnowledgePassage] = field(default_factory=list)
    abstain: bool = False
    query_raw: str = ""       # query as submitted by the caller (pre-normalization)
    query_searched: str = ""  # query actually sent to the backend (post-normalization)
    top_similarity: float | None = None  # best cosine sim in the returned pack; drives abstain
