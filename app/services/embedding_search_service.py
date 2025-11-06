import json
import numpy as np


class EmbeddingSearch:
    def __init__(self):

        # Nạp dữ liệu embedding
        with open("text-embedding-3-small.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        self.vectors = np.array([item["vector"] for item in data], dtype=np.float32)
        self.texts = [item["data"] for item in data]

        # Chuẩn hóa vector để tính cosine nhanh
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        self.vectors = self.vectors / norms


    # ---------------------------------------
    def search(self, query_vec, top_k: int = 3):
        query_vec = np.array(query_vec, dtype=np.float32)
        query_vec /= np.linalg.norm(query_vec)

        sims = np.dot(self.vectors, query_vec)
        top_indices = np.argsort(sims)[::-1][:top_k]

        results = []
        for i in top_indices:
            results.append({
                "similarity": float(sims[i]),
                "text": self.texts[i]
            })
        return results


embedding_search =  None#EmbeddingSearch()