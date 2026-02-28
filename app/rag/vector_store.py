import os
import json
import fcntl
import faiss
import numpy as np
from app.rag.embeddings import get_embeddings, get_embedding

# Use a mounted volume for cross-process shared FAISS data
FAISS_DIR = "/app/data/faiss"
os.makedirs(FAISS_DIR, exist_ok=True)


class VectorStore:
    def __init__(self, video_id: str, dimension: int = 768):
        self.video_id = video_id
        self.dimension = dimension
        self.index_path = os.path.join(FAISS_DIR, f"{video_id}.index")
        self.meta_path = os.path.join(FAISS_DIR, f"{video_id}.meta.json")
        self.lock_path = os.path.join(FAISS_DIR, f"{video_id}.lock")
        
        self._load()
    
    def _load(self):
        """Load FAISS index and metadata from disk with file locking."""
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            with open(self.lock_path, 'w') as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_SH)  # Shared read lock
                try:
                    self.index = faiss.read_index(self.index_path)
                    with open(self.meta_path, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        else:
            # Cosine similarity: use Inner Product on L2-normalized vectors
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []

    def add_chunks(self, chunks: list[dict]):
        """Add chunks with embeddings to the index (with exclusive file lock)."""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = np.array(get_embeddings(texts)).astype("float32")
        
        # L2 normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)
        
        self.index.add(embeddings)
        self.metadata.extend(chunks)
        
        # Write with exclusive lock to prevent concurrent corruption
        with open(self.lock_path, 'w') as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)  # Exclusive write lock
            try:
                faiss.write_index(self.index, self.index_path)
                with open(self.meta_path, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f)
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Search for the top-k most similar chunks using cosine similarity."""
        if self.index.ntotal == 0:
            return []
            
        query_embedding = np.array([get_embedding(query)]).astype("float32")
        # L2 normalize the query vector too
        faiss.normalize_L2(query_embedding)
        
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for i in indices[0]:
            if i != -1 and i < len(self.metadata):
                results.append(self.metadata[i])
        return results
