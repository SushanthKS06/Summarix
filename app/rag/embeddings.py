from sentence_transformers import SentenceTransformer

# Load model globally to avoid reloading inside workers
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    model = None # Fallback for test initialization if needed

def get_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    if not model:
        raise RuntimeError("SentenceTransformer model not loaded")
    return model.encode(text).tolist()

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    if not model:
        raise RuntimeError("SentenceTransformer model not loaded")
    return model.encode(texts).tolist()
