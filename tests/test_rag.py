import pytest
from app.rag.chunking import chunk_transcript
from tests.conftest import SAMPLE_TRANSCRIPT


class TestChunkTranscript:
    """Test transcript chunking with timestamp preservation."""
    
    def test_basic_chunking(self):
        chunks = chunk_transcript(SAMPLE_TRANSCRIPT, chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 0
        assert all("text" in c and "start" in c for c in chunks)
    
    def test_first_chunk_starts_at_zero(self):
        chunks = chunk_transcript(SAMPLE_TRANSCRIPT, chunk_size=50, chunk_overlap=10)
        assert chunks[0]["start"] == 0.0
    
    def test_timestamps_are_non_decreasing(self):
        """Timestamps should generally increase (or stay same) across chunks."""
        chunks = chunk_transcript(SAMPLE_TRANSCRIPT, chunk_size=20, chunk_overlap=5)
        for i in range(1, len(chunks)):
            assert chunks[i]["start"] >= chunks[i-1]["start"], (
                f"Chunk {i} has start {chunks[i]['start']} < chunk {i-1} start {chunks[i-1]['start']}"
            )
    
    def test_later_chunks_have_later_timestamps(self):
        """Last chunk should have a timestamp > first chunk."""
        chunks = chunk_transcript(SAMPLE_TRANSCRIPT, chunk_size=20, chunk_overlap=5)
        if len(chunks) > 1:
            assert chunks[-1]["start"] > chunks[0]["start"]
    
    def test_empty_transcript(self):
        chunks = chunk_transcript([])
        assert chunks == []
    
    def test_single_entry_transcript(self):
        single = [{"text": "Hello world.", "start": 5.0, "duration": 1.0}]
        chunks = chunk_transcript(single, chunk_size=50, chunk_overlap=5)
        assert len(chunks) > 0
        assert chunks[0]["start"] == 5.0
    
    def test_no_text_entries(self):
        empty_text = [{"text": "", "start": 0.0}, {"text": "", "start": 1.0}]
        chunks = chunk_transcript(empty_text)
        assert chunks == []
    
    def test_all_chunks_have_text(self):
        chunks = chunk_transcript(SAMPLE_TRANSCRIPT, chunk_size=30, chunk_overlap=5)
        for chunk in chunks:
            assert len(chunk["text"].strip()) > 0
    
    def test_small_chunk_size_creates_more_chunks(self):
        small_chunks = chunk_transcript(SAMPLE_TRANSCRIPT, chunk_size=10, chunk_overlap=2)
        large_chunks = chunk_transcript(SAMPLE_TRANSCRIPT, chunk_size=100, chunk_overlap=20)
        assert len(small_chunks) >= len(large_chunks)
