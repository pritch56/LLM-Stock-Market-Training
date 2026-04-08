SYSTEM_PROMPT = """\
You are an expert financial analyst and dataset curator creating high-quality instruction-following \
training data for a stock market prediction model.

Your responses must:
- Be grounded strictly in the provided passage
- Always reference specific companies by name and include their stock ticker symbols where identifiable
- Focus on signals, indicators, and reasoning relevant to stock price prediction and investment decisions
- Vary question types: price impact analysis, sentiment assessment, sector comparisons, risk factors, \
earnings implications, macroeconomic effects
- Produce detailed responses of at least 3 sentences

Respond ONLY with valid JSON. No markdown fences, no preamble.
"""

_ENTITY_EXTRACTION_TEMPLATE = """\
Analyse the following passage and extract all companies, organisations, and financial instruments mentioned.

Passage:
\"\"\"
{text}
\"\"\"

Return a JSON object with a single key "entities" containing an array of objects with:
- "name": full company/organisation name
- "ticker": stock ticker symbol (e.g. "AAPL", "MSFT") — use null if not publicly traded or unknown
- "exchange": exchange the ticker trades on (e.g. "NASDAQ", "NYSE", "LSE") — use null if unknown
- "relevance": one-sentence explanation of why this entity is relevant to stock prediction

Only include entities that are meaningfully relevant to financial markets or stock prediction. \
If no relevant entities exist, return {{"entities": []}}.
"""

_PAIR_TEMPLATE = """\
Generate {n} diverse instruction/response pairs for training a stock market prediction model, \
based on the following passage.

{entity_context}\
Passage:
\"\"\"
{text}
\"\"\"

Requirements:
- Each pair must be relevant to stock price prediction, investment decisions, or market analysis
- Reference specific companies and their tickers (e.g. Apple Inc. (AAPL)) wherever applicable
- Cover a mix of: price impact, sentiment signals, sector analysis, risk assessment, \
earnings implications, comparative analysis
- Responses must be analytical and specific, not generic

Return a JSON array of objects with keys: "instruction", "input", "output".
- "instruction": a specific analytical question or task relevant to stock prediction
- "input": the most relevant excerpt from the passage (can be empty string "")
- "output": a thorough analytical response that names companies and tickers where applicable

Example format:
[
  {{
    "instruction": "What are the potential impacts on Tesla (TSLA) stock based on this passage?",
    "input": "...",
    "output": "..."
  }}
]
"""


def build_entity_prompt(text: str) -> str:
    truncated = text[:4000] if len(text) > 4000 else text
    return _ENTITY_EXTRACTION_TEMPLATE.format(text=truncated)


def build_generation_prompt(text: str, n: int, entities: list[dict] | None = None) -> str:
    truncated = text[:5000] if len(text) > 5000 else text

    entity_context = ""
    if entities:
        lines = ["Identified companies and tickers in this passage:"]
        for e in entities:
            ticker_str = f" ({e['ticker']})" if e.get("ticker") else " (private/unlisted)"
            exchange_str = f" on {e['exchange']}" if e.get("exchange") else ""
            lines.append(f"  - {e['name']}{ticker_str}{exchange_str}: {e.get('relevance', '')}")
        entity_context = "\n".join(lines) + "\n\n"

    return _PAIR_TEMPLATE.format(text=truncated, n=n, entity_context=entity_context)
