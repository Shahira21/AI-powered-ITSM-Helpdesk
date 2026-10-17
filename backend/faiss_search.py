
import faiss
import numpy as np

from semantic_search import create_embedding, article_to_text


def search_articles(
    question: str,
    articles: list[dict],
    top_k: int = 3,
    minimum_score: float = 0.40,
) -> list[dict]:
    """Search knowledge articles using FAISS cosine similarity."""

    if not question.strip() or not articles:
        return []

    # Create normalized vectors for the question and each article.
    question_vector = np.asarray(
        create_embedding(question),
        dtype=np.float32,
    ).reshape(1, -1)

    article_vectors = np.asarray(
        [
            article.get("embedding")
            if isinstance(article.get("embedding"), list)
            and len(article["embedding"]) == question_vector.shape[1]
            else create_embedding(article_to_text(article))
            for article in articles
        ],
        dtype=np.float32,
    )

    # The embeddings are normalized, so inner product equals cosine similarity.
    index = faiss.IndexFlatIP(question_vector.shape[1])
    index.add(article_vectors)

    scores, indices = index.search(
        question_vector,
        min(top_k, len(articles)),
    )

    results = []

    for score, article_index in zip(scores[0], indices[0]):
        if article_index < 0:
            continue

        similarity = float(score)

        if similarity >= minimum_score:
            results.append(
                {
                    "article": articles[int(article_index)],
                    "score": similarity,
                }
            )

    return results
