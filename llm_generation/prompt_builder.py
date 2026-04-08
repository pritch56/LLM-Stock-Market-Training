SYSTEM_PROMPT = """\
You are an expert dataset curator creating high-quality instruction-following training data.
Given a passage of text, generate instruction/response pairs that:
- Test comprehension, reasoning, or application of the content
- Are specific and answerable from the passage
- Vary in difficulty and style (factual, analytical, explanatory, comparative)
- Have detailed, accurate responses of at least 2-3 sentences

Respond ONLY with valid JSON. No markdown fences, no preamble.
"""

_PAIR_TEMPLATE = """\
Generate {n} diverse instruction/response pairs from the following passage.

Passage:
\"\"\"
{text}
\"\"\"

Return a JSON array of objects with keys: "instruction", "input", "output".
- "instruction": the task or question
- "input": relevant excerpt from the passage (can be empty string "")
- "output": a thorough, accurate answer

Example format:
[
  {{
    "instruction": "Explain the concept of...",
    "input": "",
    "output": "..."
  }}
]
"""


def build_generation_prompt(text: str, n: int) -> str:
    truncated = text[:6000] if len(text) > 6000 else text
    return _PAIR_TEMPLATE.format(text=truncated, n=n)
