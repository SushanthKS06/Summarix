from langchain_text_splitters import TokenTextSplitter

def chunk_transcript(transcript_dicts: list[dict], chunk_size: int = 400, chunk_overlap: int = 50) -> list[dict]:
    """
    Chunks transcript while preserving accurate timestamp metadata.
    Uses TokenTextSplitter to ensure chunks are contextually meaningful.
    Each chunk gets the correct start timestamp based on character offset mapping.
    """
    text_splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Build a unified text with a char-offset -> timestamp map
    full_text = ""
    char_to_timestamp: list[tuple[int, float]] = []  # (char_offset, start_time)

    for item in transcript_dicts:
        offset = len(full_text)
        char_to_timestamp.append((offset, item.get('start', 0.0)))
        full_text += item['text'] + " "

    if not full_text.strip():
        return []

    splits = text_splitter.split_text(full_text)

    chunks = []
    search_start = 0
    for split in splits:
        # Find where this split starts in the full text
        pos = full_text.find(split, search_start)
        if pos == -1:
            pos = full_text.find(split)
        if pos == -1:
            pos = search_start

        # Find the closest timestamp at or before this position
        start_time = 0.0
        for char_offset, ts in char_to_timestamp:
            if char_offset <= pos:
                start_time = ts
            else:
                break

        chunks.append({
            "text": split,
            "start": start_time
        })
        search_start = pos + 1

    return chunks
