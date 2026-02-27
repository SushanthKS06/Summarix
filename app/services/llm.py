import tiktoken
from langchain_core.prompts import PromptTemplate
from app.core.llm_client import invoke_with_retry

# Tokenizer for accurate token counting
_encoding = tiktoken.get_encoding("cl100k_base")

# Groq free tier: 12,000 TPM. Reserve ~2,000 tokens for prompt + response overhead.
MAX_TRANSCRIPT_TOKENS = 8000

def _truncate_to_tokens(text: str, max_tokens: int = MAX_TRANSCRIPT_TOKENS) -> str:
    """Truncate text to a maximum number of tokens, preserving sentence boundaries."""
    tokens = _encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated = _encoding.decode(tokens[:max_tokens])
    # Try to end at a sentence boundary
    last_period = truncated.rfind('.')
    if last_period > len(truncated) * 0.8:
        return truncated[:last_period + 1]
    return truncated

# ── Summary Prompt ─────────────────────────────────────────────────────────

SUMMARY_PROMPT = PromptTemplate(
    input_variables=["title", "transcript", "timestamp_sections"],
    template="""You are a highly capable AI assistant. Read the provided YouTube video transcript and generate a structured summary.

Video Title: {title}

Transcript:
{transcript}

Real Timestamp Sections (use these exact timestamps):
{timestamp_sections}

Generate the response strictly in the following structure:
🎥 Title: {title}

📌 Key Points:
- [Point 1]
- [Point 2]
- [Point 3]
- [Point 4]
- [Point 5]

⏱ Important Timestamps: (use the real timestamps provided above)
- [M:SS] [Section description]
- [M:SS] [Section description]
- [M:SS] [Section description]

🧠 Core Takeaway: [One sentence main takeaway]

✅ Actionable Insights:
- [Action 1]
- [Action 2]
"""
)

# ── Q&A Prompt (with conversation history support) ─────────────────────────

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question", "history"],
    template="""You are a helpful AI assistant. Use the following context from a YouTube video transcript to answer the user's question. 

Context:
{context}

Previous conversation:
{history}

Current Question:
{question}

Grounding Rule: If the answer is not present in the context, you MUST reply EXACTLY with "This topic is not covered in the video." Do NOT hallucinate or make up information.

Answer:"""
)

# ── Deep Dive Prompt ──────────────────────────────────────────────────────

DEEPDIVE_PROMPT = PromptTemplate(
    input_variables=["context", "topic"],
    template="""You are a research-grade AI analyst. The user wants a deep dive into a specific topic from a YouTube video. Analyze the following transcript context thoroughly.

Context from the video:
{context}

Topic to deep dive into:
{topic}

Provide your analysis in this structure:

🔬 Deep Dive: {topic}

📖 Detailed Analysis:
[Provide a thorough, multi-paragraph analysis of everything the video covers about this topic]

💡 Key Nuances:
- [Nuance 1]
- [Nuance 2]
- [Nuance 3]

🔗 Related Points Mentioned:
- [Related point 1]
- [Related point 2]

Grounding Rule: Only use information from the provided context. If the topic is not substantially covered, say "This topic is not covered in sufficient detail in the video."

Analysis:"""
)

# ── Action Points Prompt ───────────────────────────────────────────────────

ACTIONPOINTS_PROMPT = PromptTemplate(
    input_variables=["context"],
    template="""You are a productivity-focused AI assistant. Extract all actionable items, recommendations, and steps from the following YouTube video transcript context.

Transcript Context:
{context}

Generate the response in this structure:

📋 Action Points from this Video:

🎯 Immediate Actions (things you can do right now):
- [ ] [Action 1]
- [ ] [Action 2]
- [ ] [Action 3]

📅 Short-term Goals (things to plan for):
- [ ] [Goal 1]
- [ ] [Goal 2]

🧭 Long-term Strategies (bigger picture ideas):
- [ ] [Strategy 1]
- [ ] [Strategy 2]

💡 Key Recommendations:
- [Recommendation 1]
- [Recommendation 2]

If no actionable items can be extracted, respond with "No clear action points found in this video."

Action Points:"""
)

# ── Functions ──────────────────────────────────────────────────────────────

async def generate_summary(transcript_text: str, video_title: str = "Unknown Title", timestamp_sections: str = "") -> str:
    """Generate structured summary using token-aware truncation and real timestamps."""
    truncated = _truncate_to_tokens(transcript_text, max_tokens=MAX_TRANSCRIPT_TOKENS)
    if not timestamp_sections:
        timestamp_sections = "(No timestamp data available — infer from transcript flow)"
    prompt = SUMMARY_PROMPT.format(title=video_title, transcript=truncated, timestamp_sections=timestamp_sections)
    return await invoke_with_retry(prompt)

async def answer_question(context: str, question: str, history: list[dict] | None = None) -> str:
    """Answer a question with conversation history for context-aware follow-ups."""
    history_text = ""
    if history:
        for entry in history:
            history_text += f"Q: {entry['question']}\nA: {entry['answer']}\n\n"
    if not history_text:
        history_text = "(No previous conversation)"
    
    context = _truncate_to_tokens(context, max_tokens=6000)
    prompt = QA_PROMPT.format(context=context, question=question, history=history_text)
    return await invoke_with_retry(prompt)

async def generate_deepdive(context: str, topic: str) -> str:
    """Generate a deep-dive analysis on a specific topic from the video."""
    context = _truncate_to_tokens(context, max_tokens=7000)
    prompt = DEEPDIVE_PROMPT.format(context=context, topic=topic)
    return await invoke_with_retry(prompt)

async def generate_actionpoints(context: str) -> str:
    """Extract actionable items from the video transcript."""
    context = _truncate_to_tokens(context, max_tokens=7000)
    prompt = ACTIONPOINTS_PROMPT.format(context=context)
    return await invoke_with_retry(prompt)
