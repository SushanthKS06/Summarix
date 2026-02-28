from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

# Global variable to hold the lazily loaded model
_model = None

def _get_model():
    """Lazy load the SentenceTransformer model to avoid multiprocessing overhead."""
    global _model
    if _model is None:
        logger.info("Loading SentenceTransformer model ('all-MiniLM-L6-v2')...")
        try:
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            _model = None
    return _model

def get_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    model = _get_model()
    if not model:
        raise RuntimeError("SentenceTransformer model not loaded")
    return model.encode(text).tolist()

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    model = _get_model()
    if not model:
        raise RuntimeError("SentenceTransformer model not loaded")
    return model.encode(texts).tolist()
