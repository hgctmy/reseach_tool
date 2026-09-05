"""「いいね」履歴とのTF-IDF類似度で候補論文をランキングする簡易レコメンダー。"""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .arxiv_client import Paper
from .profile import Profile


def rank_papers(candidates: list[Paper], profile: Profile, top_n: int = 10) -> list[Paper]:
    """未読の候補論文を、いいね済み論文との類似度が高い順に並べ替える。

    いいね履歴がまだ無い場合は、arXiv取得時の並び順（新着順）をそのまま使う。
    """
    unseen = [p for p in candidates if p.arxiv_id not in profile.seen]

    if not profile.liked:
        return unseen[:top_n]

    liked_abstracts = list(profile.liked.values())
    corpus = liked_abstracts + [p.abstract for p in unseen]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    matrix = vectorizer.fit_transform(corpus)

    liked_matrix = matrix[: len(liked_abstracts)]
    candidate_matrix = matrix[len(liked_abstracts) :]

    # 各候補について、いいね済み論文群との最大類似度をスコアとする
    similarity = cosine_similarity(candidate_matrix, liked_matrix)
    scores = similarity.max(axis=1)

    scored = list(zip(scores, unseen))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [paper for _, paper in scored[:top_n]]
