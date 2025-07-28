# vector_database.py
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class VectorDatabase:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)
        self.chunks = []

    def add_chunks(self, chunks):
        texts = [f"{chunk['title']}. {chunk['content']}" if chunk['title'] else chunk['content'] for chunk in chunks]
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.index.add(embeddings.astype('float32'))
        self.chunks.extend(chunks)

    def search(self, query, top_k=5):
        emb = self.model.encode([query], convert_to_numpy=True)
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        scores, idxs = self.index.search(emb.astype('float32'), top_k)
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))
        return results