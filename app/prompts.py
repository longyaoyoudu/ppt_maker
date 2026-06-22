"""Prompt templates for the two LLM stages.

Outline prompt instructs the model to return strict JSON matching the
OutlinePage schema. We keep the system prompt identical across providers;
only the user message varies.
"""

OUTLINE_SYSTEM = """You are a presentation outline designer. Produce a structured outline \
for the user's topic. Each page must be one of: title, title-content, two-column, quote, section. \
Return ONLY valid JSON, no prose, no markdown fences."""

OUTLINE_USER_TEMPLATE = """Topic: {topic}

{requirements_block}

{document_block}

Output schema:
{{
  "pages": [
    {{"title": "...", "key_points": ["...", "..."], "layout": "title-content"}},
    ...
  ]
}}

Constraints:
- 5 to 15 pages total.
- First page usually layout="title", last page layout="section".
- Use "title-content" for most middle pages.
- Each key_points entry is a short phrase (max 20 Chinese chars or 12 English words).
- Return only the JSON object."""


def build_outline_user(
    topic: str,
    requirements: str | None,
    style_hint: str | None,
    document_excerpt: str | None = None,
) -> str:
    extra_lines = []
    if requirements:
        extra_lines.append(f"Additional requirements: {requirements}")
    if style_hint:
        extra_lines.append(f"Style hint: {style_hint}")
    requirements_block = "\n".join(extra_lines) if extra_lines else "(no extra requirements)"
    document_block = (
        "Source documents:\n" + document_excerpt if document_excerpt else "(no source documents)"
    )
    return OUTLINE_USER_TEMPLATE.format(
        topic=topic, requirements_block=requirements_block, document_block=document_block
    )
