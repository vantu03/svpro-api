import numpy as np
from numpy.linalg import norm

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (norm(vec1) * norm(vec2))

class PDFRetriever:
    def __init__(self, embedder, doc_chunks_with_vecs):
        self.embedder = embedder
        self.doc_chunks = doc_chunks_with_vecs

    async def embed_query(self, query: str):
        if not query.strip():
            return None  

        # embed query giống như embed text của PDF
        q_emb = await self.embedder.embed_chunks(
            [{"text": query, "page": None, "images": [], "page_image": None}]
        )
        if not q_emb:
            return None  

        return np.array(q_emb[0][1])

    async def retrieve(self, query: str, top_k: int = 3):
        q_vec = await self.embed_query(query)
        if q_vec is None:
            return []  
    
        # cosine similarity với từng chunk vector
        sims = [cosine_similarity(q_vec, np.array(v)) for meta, v in self.doc_chunks]
        top_idx = np.argsort(sims)[::-1][:top_k]
    
        results = [(self.doc_chunks[i][0], sims[i]) for i in top_idx]
        return results
