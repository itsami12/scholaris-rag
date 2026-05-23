"""
Groq LLM integration for context-aware academic paper Q&A.
"""
from __future__ import annotations

from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are Scholaris, an expert AI research assistant specializing in academic papers.

Your role:
- Answer questions accurately based ONLY on the provided paper excerpts
- Cite specific pages or sections when possible (e.g. "According to page 3...")
- Acknowledge when information is not found in the provided context
- Provide nuanced, scholarly analysis — not just summaries
- Use clear, precise academic language
- If asked about methodology, results, conclusions, or limitations, ground every claim in the excerpts

Format guidelines:
- Use markdown for structured answers (headers, bullet points, bold for key terms)
- Keep answers concise unless depth is explicitly requested
- Always mention which paper(s) the answer comes from when multiple papers are in context
"""


def build_context(retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks into a readable context block."""
    if not retrieved_chunks:
        return "No relevant excerpts found."

    parts: list[str] = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        authors = ", ".join(chunk.get("authors", [])) or "Unknown authors"
        parts.append(
            f"[Excerpt {i}] — {chunk.get('title', 'Unknown')} "
            f"({authors}, {chunk.get('year', 'n.d.')}) | Page {chunk.get('page_hint', '?')}\n"
            f"{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def chat_with_paper(
    query: str,
    retrieved_chunks: list[dict],
    history: list[dict] | None = None,
) -> str:
    """
    Generate a context-aware response using Groq.

    Parameters
    ----------
    query           : user question
    retrieved_chunks: output from VectorStore.search()
    history         : prior turns [{"role": "user"|"assistant", "content": str}]
    """
    context = build_context(retrieved_chunks)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Here are the relevant excerpts from the research paper(s):\n\n"
                f"{context}\n\n"
                f"---\n\nBased on these excerpts, please answer the following question:\n{query}"
            ),
        },
    ]

    # Inject prior turns (only the last 6 to stay within context)
    if history:
        tail = history[-6:]
        # Insert before the current user message
        messages = (
            messages[:1]      # system
            + tail            # prior turns
            + messages[1:]    # current user message with context
        )

    completion = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
    )

    return completion.choices[0].message.content


def summarize_paper(abstract: str, title: str) -> str:
    """Generate a concise summary of a paper from its abstract."""
    prompt = (
        f"Title: {title}\n\nAbstract:\n{abstract}\n\n"
        "Provide a clear 3-bullet summary of this paper covering: "
        "(1) Problem addressed, (2) Approach/Method, (3) Key findings/contributions."
    )
    completion = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return completion.choices[0].message.content
