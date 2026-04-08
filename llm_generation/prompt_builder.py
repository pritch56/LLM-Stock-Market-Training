SYSTEM_PROMPT = """\
You are an expert financial analyst. You analyse news articles to identify publicly traded companies \
mentioned and assess how the news is likely to affect their stock prices.

You must respond ONLY with valid JSON. No markdown fences, no preamble.\
"""

_ANALYSIS_TEMPLATE = """\
Analyse the following news article. Identify all publicly traded companies mentioned, \
their stock ticker symbols, and rate the likely impact of this news on each company's stock price.

Rating scale (1-10):
1 = extremely negative impact
5 = neutral
10 = extremely positive impact

Consider factors such as: earnings, mergers/acquisitions, regulation, lawsuits, product launches, \
leadership changes, supply chain disruptions, macroeconomic effects.

Article:
\"\"\"
{text}
\"\"\"

Return a JSON object in this exact structure:
{{
  "companies": [
    {{
      "company_name": "string",
      "ticker": "string or null",
      "impact_rating": number,
      "reasoning": "short explanation"
    }}
  ]
}}

If no publicly traded companies are mentioned, return {{"companies": []}}.
"""


def build_analysis_prompt(article_text: str) -> str:
    truncated = article_text[:6000] if len(article_text) > 6000 else article_text
    return _ANALYSIS_TEMPLATE.format(text=truncated)
