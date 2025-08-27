import time
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering

from storage import (
    fetch_items_for_analysis,
    record_link,
    set_status,
    replace_clusters,
)


def _build_corpus(rows) -> Tuple[List[int], List[str]]:
    item_ids: List[int] = []
    corpus: List[str] = []
    for r in rows:
        item_ids.append(int(r[0]))
        title = (r[3] or "").strip()
        body = (r[4] or "").strip()
        text = (title + "\n\n" + body).strip()
        corpus.append(text)
    return item_ids, corpus


def run_similarity_and_clusters(
    duplicate_threshold: float = 0.78,
    related_threshold: float = 0.52,
    min_token_len: int = 2,
) -> None:
    rows = fetch_items_for_analysis(limit=5000)
    if not rows:
        return

    item_ids, corpus = _build_corpus(rows)
    preprocessed = [" ".join([w for w in text.split() if len(w) >= min_token_len]) for text in corpus]

    vectorizer = TfidfVectorizer(max_features=50000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(preprocessed)

    # Pairwise similarity
    sim = cosine_similarity(X)

    n = len(item_ids)
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sim[i, j])
            if s >= duplicate_threshold:
                record_link(item_ids[i], item_ids[j], link_type="duplicate", score=s, note=None)
            elif s >= related_threshold:
                record_link(item_ids[i], item_ids[j], link_type="related", score=s, note=None)

    # Clustering to group related/duplicate items into problem clusters
    if n >= 3:
        # Convert similarity to distance (bounded [0,1])
        dist = 1.0 - sim
        np.fill_diagonal(dist, 0.0)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=(1.0 - related_threshold),
            affinity="precomputed",
            linkage="average",
        )
        clustering.fit(dist)
        labels = clustering.labels_
        label_by_item = {int(item_ids[i]): int(labels[i]) for i in range(n)}
        replace_clusters(label_by_item, score_by_item=None)

    # Update priorities based on rough heuristics
    now = int(time.time())
    for i in range(n):
        # Base priority heuristic: longer text and recent update get higher weight
        text_len = len(corpus[i])
        priority = 999 - min(998, int(text_len / 500))
        set_status(item_ids[i], priority=priority, status=None, last_seen=now, labels=None)

