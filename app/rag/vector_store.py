import json
import faiss
import numpy as np
import redis
from app.core.config import settings
from app.rag.embeddings import get_embeddings, get_embedding
import logging

logger = logging.getLogger(__name__)

# Synchronous Redis client for blocking Celery & FAISS ops
_sync_redis = redis.from_url(settings.REDIS_URL, decode_responses=False)

FAISS_TTL = 86400  # 24 hours expiry for embeddings to save RAM/Redis memory

class VectorStore:
    def __init__(self, video_id: str, dimension: int = 768):
        self.video_id = video_id
        # Use a dimension of 384 since we switched to paraphrase-albert-small-v2
        self.dimension = 768
        self.index_key = f"faiss_index:{video_id}"
        self.meta_key = f"faiss_meta:{video_id}"
        
        self._load()
    
    def _load(self):
        """Load FAISS index and metadata from Redis."""
        index_data = _sync_redis.get(self.index_key)
        meta_data = _sync_redis.get(self.meta_key)
        
        if index_data and meta_data:
            try:
                # Deserialize from bytes to numpy array, then to FAISS index
                index_np = np.frombuffer(index_data, dtype=np.uint8)
                self.index = faiss.deserialize_index(index_np)
                self.metadata = json.loads(meta_data.decode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to deserialize FAISS index from Redis: {e}")
                self.index = faiss.IndexFlatIP(self.dimension)
                self.metadata = []
        else:
            # Cosine similarity: use Inner Product on L2-normalized vectors
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []

    def add_chunks(self, chunks: list[dict]):
        """Add chunks, update the FAISS index, and persist to Redis."""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = np.array(get_embeddings(texts)).astype("float32")
        
        # Override dimension if starting fresh to match actual embedding shape
        if self.index.ntotal == 0 and embeddings.shape[1] > 0:
            if embeddings.shape[1] != self.dimension:
                self.dimension = embeddings.shape[1]
                self.index = faiss.IndexFlatIP(self.dimension)
        
        # L2 normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)
        
        self.index.add(embeddings)
        self.metadata.extend(chunks)
        
        try:
            # Serialize the updated index to a numpy array, then to bytes
            index_np = faiss.serialize_index(self.index)
            index_bytes = index_np.tobytes()
            meta_bytes = json.dumps(self.metadata).encode('utf-8')
            
            # Save into Redis with TTL using pipeline for atomicity
            pipe = _sync_redis.pipeline()
            pipe.setex(self.index_key, FAISS_TTL, index_bytes)
            pipe.setex(self.meta_key, FAISS_TTL, meta_bytes)
            pipe.execute()
        except Exception as e:
            logger.error(f"Failed to serialize/save FAISS index to Redis: {e}")

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
