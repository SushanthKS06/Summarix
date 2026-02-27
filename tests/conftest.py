import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Sample Test Data ───────────────────────────────────────────────────────

SAMPLE_TRANSCRIPT = [
    {"text": "Hello and welcome to this video about machine learning.", "start": 0.0, "duration": 3.0},
    {"text": "Today we will cover three main topics.", "start": 3.0, "duration": 2.5},
    {"text": "First, let's talk about neural networks.", "start": 5.5, "duration": 2.0},
    {"text": "Neural networks are composed of layers of neurons.", "start": 7.5, "duration": 3.0},
    {"text": "Each neuron applies an activation function.", "start": 10.5, "duration": 2.5},
    {"text": "Second, we will discuss training algorithms.", "start": 13.0, "duration": 2.0},
    {"text": "Gradient descent is the most common optimization method.", "start": 15.0, "duration": 3.0},
    {"text": "Third, we will look at practical applications.", "start": 18.0, "duration": 2.5},
    {"text": "Machine learning is used in healthcare, finance, and more.", "start": 20.5, "duration": 3.0},
    {"text": "Thank you for watching. Don't forget to subscribe!", "start": 23.5, "duration": 2.5},
]

SAMPLE_FULL_TEXT = " ".join(entry["text"] for entry in SAMPLE_TRANSCRIPT)

SAMPLE_SUMMARY = """🎥 Title: Introduction to Machine Learning

📌 Key Points:
- Neural networks are composed of layers of neurons
- Gradient descent is the main optimization method
- ML is used in healthcare, finance, and more

⏱ Important Timestamps:
- [0:00] Introduction
- [0:05] Neural Networks
- [0:13] Training Algorithms
- [0:18] Practical Applications

🧠 Core Takeaway: Machine learning fundamentals cover neural networks, training, and real-world applications.

✅ Actionable Insights:
- Start learning neural network architectures
- Practice gradient descent implementations"""


# ── Mock Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing session and cache operations."""
    redis_mock = AsyncMock()
    redis_mock.hget = AsyncMock(return_value=None)
    redis_mock.hset = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock()
    redis_mock.rpush = AsyncMock()
    redis_mock.ltrim = AsyncMock()
    redis_mock.lrange = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()
    
    pipe_mock = AsyncMock()
    pipe_mock.incr = MagicMock()
    pipe_mock.expire = MagicMock()
    pipe_mock.execute = AsyncMock(return_value=[1, True])
    redis_mock.pipeline = MagicMock(return_value=pipe_mock)
    
    return redis_mock


@pytest.fixture
def mock_llm():
    """Mock LLM for testing without API calls."""
    mock = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = SAMPLE_SUMMARY
    mock.ainvoke = AsyncMock(return_value=mock_response)
    return mock
