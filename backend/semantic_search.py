
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the model once and reuse it."""
    return SentenceTransformer(MODEL_NAME)


def create_embedding(text: str) -> list[float]:
    """Convert text into a normalized vector."""
    model = get_embedding_model()

    vector = model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return vector.astype(float).tolist()


def article_to_text(article: dict) -> str:
    """Create consistent searchable text from a knowledge article."""
    keywords = article.get("keywords", [])

    if not isinstance(keywords, list):
        keywords = []

    return (
        f"Title: {article.get('title', '')}\n"
        f"Category: {article.get('category', '')}\n"
        f"Keywords: {' '.join(str(word) for word in keywords)}\n"
        f"Content: {article.get('content', '')}"
    ).strip()


def find_relevant_articles(
    question: str,
    articles: list[dict],
    top_k: int = 3,
    minimum_score: float = 0.35,
) -> list[dict]:
    """Rank articles by cosine similarity."""
    if not question.strip() or not articles:
        return []

    question_vector = np.asarray(
        create_embedding(question),
        dtype=np.float32,
    )

    scored_articles = []

    for article in articles:
        stored_vector = article.get("embedding")

        try:
            article_vector = np.asarray(
                stored_vector,
                dtype=np.float32,
            )

            if article_vector.shape != question_vector.shape:
                raise ValueError("Invalid embedding dimensions.")

            if not np.all(np.isfinite(article_vector)):
                raise ValueError("Invalid embedding values.")

        except (TypeError, ValueError):
            article_vector = np.asarray(
                create_embedding(article_to_text(article)),
                dtype=np.float32,
            )

        score = float(np.dot(question_vector, article_vector))

        if score >= minimum_score:
            scored_articles.append({
                "article": article,
                "score": score,
            })

    scored_articles.sort(
        key=lambda result: result["score"],
        reverse=True,
    )

    return scored_articles[:top_k]
