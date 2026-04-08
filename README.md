# LLM Stock Market Training Dataset Pipeline

An automated data pipeline that collects financial and technical content from free public APIs,
uses Claude (or GPT) to extract company/ticker information and generate high-quality
instruction/response pairs focused on stock prediction, then exports the dataset in formats
ready for fine-tuning small language models (1B-7B parameters).

---

## How the Pipeline Works

The pipeline runs five stages in sequence:

```text
scrape -> clean -> generate (entity extraction + pair generation) -> filter -> export
```

### Stage 1: Scrape

Sources are defined in `config/sources.yaml`. Each source has a type:

- `api` — calls a structured JSON API directly (no HTML parsing). Currently supported:
  - **HackerNews** via the Algolia search API. Searches for stories matching a query, fetches
    comment bodies for stories with little text.
  - **Semantic Scholar** via the Graph API. Returns paper titles, authors, abstracts, venue,
    and year for academic papers matching a query.
  - **arXiv** via the Atom XML API (available but disabled by default due to aggressive rate
    limiting on shared IPs).
- `static` — fetches a URL with httpx and extracts text using a CSS selector.
- `dynamic` — renders the page with a headless Chromium browser via Playwright, for
  JavaScript-heavy sites.

All fetching is async with a configurable concurrency limit and per-domain rate limiting.
Transient network errors are retried with exponential backoff via tenacity. HTTP 4xx errors
(paywalls, missing pages) are caught and logged without retrying.

### Stage 2: Clean

Each scraped document passes through three cleaning steps:

1. **HTML extraction** (`cleaners/html_cleaner.py`) — strips noise tags (nav, footer, script,
   ads), then extracts plain text from the configured CSS selector. Skipped for API sources
   that return pre-cleaned text.
2. **Text normalisation** (`cleaners/text_normalizer.py`) — decodes HTML entities, applies
   Unicode NFKC normalisation, removes control characters, strips bare URLs and Wikipedia
   citation markers, collapses repeated punctuation and blank lines.
3. **Deduplication** (`cleaners/deduplicator.py`) — computes a SHA-256 hash of the cleaned
   text and discards any document whose hash has already been seen in this run. Prevents the
   same article appearing twice if multiple sources link to it.

Documents shorter than `MIN_INPUT_TEXT_LENGTH / 5` words are dropped before reaching the LLM.

### Stage 3: Generate

This is a two-pass LLM call per document.

#### Pass 1: Entity extraction

The cleaned text is sent to the LLM with a prompt that asks it to identify every company,
organisation, or financial instrument mentioned and return structured JSON:

```json
{
  "entities": [
    {
      "name": "Nvidia Corporation",
      "ticker": "NVDA",
      "exchange": "NASDAQ",
      "relevance": "Dominant GPU manufacturer central to AI training infrastructure."
    }
  ]
}
```

If the text contains no publicly traded companies, `entities` is an empty array and the
second pass continues without ticker context.

#### Pass 2: Instruction pair generation

The identified tickers are injected into the prompt as a labelled list before the passage.
The LLM is then instructed to generate `PAIRS_PER_DOCUMENT` instruction/response pairs
that are:

- Grounded strictly in the passage
- Relevant to stock price prediction and investment decision-making
- Varied in type: price impact analysis, sentiment assessment, sector comparison, risk
  factors, earnings implications, macroeconomic effects
- Explicit about company names and ticker symbols in every response

Each pair has the shape:

```json
{
  "instruction": "What does this passage imply for Nvidia (NVDA) stock in the near term?",
  "input": "...relevant excerpt...",
  "output": "...detailed analytical response referencing NVDA and related tickers..."
}
```

Both passes share the same async concurrency semaphore (`GENERATION_CONCURRENCY`).

### Stage 4: Filter

Every generated pair is checked against four filters in order. The first failure discards
the pair:

| Filter | Check |
| --- | --- |
| Length | Instruction >= 5 words; output between `MIN_OUTPUT_LENGTH` and `MAX_OUTPUT_LENGTH` chars |
| Language | Output language detected as English (requires `langdetect`) |
| Toxicity | Regex screen against a list of slurs and explicit terms |
| Duplicate | SHA-256 of `instruction + output[:200]` not seen in this run |

All pairs (passed and failed) are written to the database with their filter outcome recorded.
Only passed pairs enter the export.

### Stage 5: Export

Three output formats are written simultaneously:

- **JSONL** — one JSON object per line, the standard Alpaca instruction-tuning format
- **Parquet** — columnar format for efficient loading with pandas or Polars
- **HuggingFace Dataset** — saved with `datasets.Dataset.save_to_disk()` for direct use
  with `Trainer` / `SFTTrainer`

A separate export script converts the JSONL to the full Alpaca prompt template for LoRA
fine-tuning frameworks.

---

## Data Sources

All sources are free and require no API key.

| Source | API | Content | Tags |
| --- | --- | --- | --- |
| HackerNews (ML) | Algolia HN Search | Stories and comments on machine learning | `ml`, `technology` |
| HackerNews (Finance) | Algolia HN Search | Stories and comments on investing | `finance`, `investing` |
| HackerNews (Engineering) | Algolia HN Search | Software engineering discussion | `programming`, `engineering` |
| Semantic Scholar (ML) | S2 Graph API | Academic abstracts on neural networks | `ml`, `research` |
| Semantic Scholar (Finance) | S2 Graph API | Academic abstracts on quant finance | `finance`, `research` |
| Semantic Scholar (LLMs) | S2 Graph API | Academic abstracts on LLM fine-tuning | `llm`, `research` |

Add or remove sources by editing `config/sources.yaml`. See the Configuration section below.

---

## Project Structure

```text
run_pipeline.py              Entry point. Orchestrates all five stages.

config/
  settings.py                Pydantic settings model. Reads from .env.
  sources.yaml               List of data sources with their fetcher config.

api_fetcher/
  hackernews.py              Algolia HN search API. Fetches stories and comment bodies.
  semantic_scholar.py        Semantic Scholar Graph API. Fetches paper abstracts.
  arxiv.py                   arXiv Atom API. Serialised requests to respect rate limits.

scraper/
  base.py                    Shared httpx client factory, RateLimiter, tenacity retry decorator.
  sources.py                 SourceConfig dataclass and YAML loader.
  scraper.py                 Routes each source to the correct fetcher (static/dynamic/api).

cleaners/
  html_cleaner.py            BeautifulSoup-based noise removal and text extraction.
  text_normalizer.py         HTML entity decoding, Unicode normalisation, URL stripping.
  deduplicator.py            SHA-256 document-level deduplication.
  pipeline.py                Applies all cleaning steps to a ScrapeResult.

llm_generation/
  client.py                  Async LLM client wrappers for Anthropic, OpenAI, and Mock.
  prompt_builder.py          System prompt, entity extraction prompt, pair generation prompt.
  generator.py               Two-pass generation: entity extraction then pair generation.

filters/
  length_filter.py           Instruction and output length bounds.
  language_filter.py         English-only gate via langdetect.
  toxicity_filter.py         Regex screen for slurs and explicit content.
  duplicate_filter.py        Pair-level SHA-256 deduplication.
  pipeline.py                Runs all filters in sequence, logs pass/fail counts.

dataset_builder/
  builder.py                 Converts passed FilterResults to plain dicts (with tickers field).
  exporter.py                Writes JSONL, Parquet, and HuggingFace dataset formats.

database/
  models.py                  SQLAlchemy ORM models: RawDocument, ProcessedDocument, InstructionPair.
  db.py                      Engine, SessionLocal, init_db, get_session context manager.
  persistence.py             save_raw(), save_processed(), save_pairs() called by the pipeline.

scripts/
  export_lora.py             Converts JSONL to full Alpaca prompt template for LoRA training.
  export_hf_hub.py           Pushes the local HuggingFace dataset to the Hub.
```

---

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium     # only needed if using dynamic sources
```

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```text
ANTHROPIC_API_KEY=sk-ant-...
```

Or to use OpenAI instead:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

---

## Running the Pipeline

```bash
# Full pipeline with real LLM calls
python run_pipeline.py

# Test the full pipeline without spending API credits (mock LLM)
python run_pipeline.py --mock

# Custom source file and output directory
python run_pipeline.py --sources config/sources.yaml --output output/
```

The pipeline logs its progress at each stage:

```text
INFO: Scraping 6 sources
INFO: Scraped 44/44 sources successfully
INFO: Cleaned 44 documents
INFO: Generating instruction pairs via anthropic
INFO: Extracted 3 entities from HackerNews - Finance: NVDA, MSFT, AMD
INFO: Generated 132 raw pairs
INFO: Filtering: 128/132 pairs passed
INFO: Exporting 128 final records to output
INFO: Pipeline complete.
```

---

## Configuration

### Environment variables (`.env`)

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `LLM_MODEL` | `claude-sonnet-4-6` | Model ID passed to the provider |
| `LLM_MAX_TOKENS` | `2048` | Maximum tokens per LLM response |
| `PAIRS_PER_DOCUMENT` | `3` | Instruction pairs generated per document |
| `GENERATION_CONCURRENCY` | `3` | Parallel LLM calls (watch API rate limits) |
| `SCRAPE_CONCURRENCY` | `5` | Parallel HTTP requests |
| `SCRAPE_DELAY_SECONDS` | `1.0` | Minimum delay between requests to the same host |
| `SCRAPE_MAX_RETRIES` | `3` | Retry attempts on transient network errors |
| `MIN_INPUT_TEXT_LENGTH` | `200` | Minimum character length to pass a document to the LLM |
| `MIN_OUTPUT_LENGTH` | `50` | Minimum character length for a generated response |
| `MAX_OUTPUT_LENGTH` | `4000` | Maximum character length for a generated response |
| `OUTPUT_DIR` | `output` | Directory for JSONL, Parquet, and HuggingFace exports |
| `DATABASE_URL` | `sqlite:///pipeline.db` | SQLAlchemy database URL |

### Adding sources (`config/sources.yaml`)

API source (recommended, no parsing required):

```yaml
- name: "HackerNews - AI Safety"
  url: "https://hn.algolia.com/api/v1/search"
  type: "api"
  fetcher: "hackernews"         # hackernews | semantic_scholar | arxiv
  query: "AI safety risk"
  max_results: 10
  tags: ["ai", "risk"]
```

Static HTML source (CSS selector extracts main content):

```yaml
- name: "My Financial Blog"
  url: "https://example.com/blog"
  type: "static"
  content_selector: "article.post-content"
  tags: ["finance"]
```

Dynamic (JavaScript-rendered) source:

```yaml
- name: "JS-Heavy Dashboard"
  url: "https://example.com/dashboard"
  type: "dynamic"
  content_selector: "#main-content"
  tags: ["data"]
```

---

## Output

```text
output/
  dataset.jsonl          One record per line. Use for SFTTrainer, LitGPT, or any framework
                         that accepts Alpaca-format JSONL.
  dataset.parquet        Same data in Parquet. Load with pandas.read_parquet() or
                         datasets.load_dataset("parquet", ...).
  hf_dataset/            HuggingFace Dataset saved to disk. Load with
                         datasets.load_from_disk("output/hf_dataset").

pipeline.db              SQLite database tracking every stage of the pipeline.
```

Each JSONL record contains:

```json
{
  "instruction": "What does this passage imply for Nvidia (NVDA) stock in the near term?",
  "input": "Nvidia reported record data centre revenue driven by demand for H100 GPUs...",
  "output": "The record data centre revenue is a strong bullish signal for Nvidia (NVDA)...",
  "tickers": [
    {"name": "Nvidia Corporation", "ticker": "NVDA", "exchange": "NASDAQ"},
    {"name": "Advanced Micro Devices", "ticker": "AMD", "exchange": "NASDAQ"}
  ]
}
```

The `tickers` field lists every publicly traded company the LLM identified in the source
document. This makes it possible to filter or group the dataset by ticker after export.

---

## Fine-Tuning Compatibility

### HuggingFace SFTTrainer

```python
from datasets import load_from_disk
from trl import SFTTrainer

dataset = load_from_disk("output/hf_dataset")
trainer = SFTTrainer(model=model, train_dataset=dataset, ...)
```

### LoRA / Alpaca template format (llama-factory, axolotl, unsloth)

Convert the JSONL to the full Alpaca prompt template:

```bash
python -m scripts.export_lora \
  --input output/dataset.jsonl \
  --output output/lora_dataset.jsonl
```

Each record in the output has a single `text` field with the formatted prompt:

```text
Below is an instruction that describes a task, paired with an input that provides further
context. Write a response that appropriately completes the request.

### Instruction:
What does this passage imply for Nvidia (NVDA) stock?

### Input:
Nvidia reported record data centre revenue...

### Response:
The record revenue is a strong bullish signal for NVDA...
```

### Push to HuggingFace Hub

```bash
python -m scripts.export_hf_hub \
  --dataset output/hf_dataset \
  --name your-org/stock-prediction-dataset \
  --token hf_...
```

---

## Database Schema

The SQLite database (`pipeline.db`) tracks every document and pair through the pipeline.
Query it with any SQLite client or via SQLAlchemy.

### `raw_documents`

| Column | Type | Description |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `url` | TEXT | Unique URL or API identifier for the document |
| `source_name` | TEXT | Name from `sources.yaml` |
| `raw_html` | TEXT | Raw content as fetched (HTML or plain text for API sources) |
| `scraped_at` | DATETIME | Timestamp of the fetch |
| `http_status` | INTEGER | HTTP response code |
| `tags` | JSON | Tags array from `sources.yaml` |

### `processed_documents`

| Column | Type | Description |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `raw_id` | INTEGER | Foreign key to `raw_documents` |
| `clean_text` | TEXT | Cleaned, normalised plain text |
| `word_count` | INTEGER | Word count of the clean text |
| `language` | TEXT | Detected language code |
| `content_hash` | TEXT | SHA-256 of clean text, used for deduplication |
| `processed_at` | DATETIME | Timestamp of processing |

### `instruction_pairs`

| Column | Type | Description |
| --- | --- | --- |
| `id` | INTEGER | Primary key |
| `document_id` | INTEGER | Foreign key to `processed_documents` |
| `instruction` | TEXT | The question or task |
| `input` | TEXT | Optional context excerpt from the passage |
| `output` | TEXT | The analytical response |
| `model_used` | TEXT | LLM model ID that generated the pair |
| `generation_prompt_tokens` | INTEGER | Input tokens used in the generation call |
| `generation_output_tokens` | INTEGER | Output tokens used in the generation call |
| `passed_filters` | BOOLEAN | Whether the pair passed all quality filters |
| `filter_reason` | TEXT | Reason code if the pair was rejected |
| `tickers` | JSON | Array of `{name, ticker, exchange}` objects extracted from the document |
| `created_at` | DATETIME | Timestamp of generation |

---

## Next Steps

### Immediate

- **Top up Anthropic credits** and run `python run_pipeline.py` without `--mock` to generate
  real financial instruction pairs grounded in actual content.
- **Add more sources** in `config/sources.yaml`. Good candidates: SEC EDGAR full-text search
  API (`efts.sec.gov`), Financial Modeling Prep news endpoint (free tier), Alpha Vantage news
  sentiment API, Reddit finance subreddits via the Pushshift API.
- **Increase `PAIRS_PER_DOCUMENT`** in `.env` to 5-10 to get more training pairs per document.
  Each document already costs two LLM calls (entity extraction + pair generation), so the
  marginal cost of more pairs per call is low.

### Dataset Quality

- **Filter by ticker** — post-export, split `dataset.jsonl` into per-ticker files for
  focused fine-tuning on specific stocks or sectors.
- **Add a quality scoring pass** — send each generated pair back to the LLM and ask it to
  score the response 1-5 for analytical depth, accuracy, and relevance. Store the score in
  the database and filter to only use pairs scoring 4+.
- **Expand entity extraction** — prompt the LLM to also extract macroeconomic indicators,
  commodities (oil, gold), indices (S&P 500, NASDAQ), and currency pairs, not just equities.
- **Human review** — export `passed_filters=True` pairs to a CSV and spot-check a random
  sample to catch systematic prompt failures before using the dataset for training.

### Training

- **Fine-tune a base model** using the exported dataset. Recommended starting points:
  Mistral-7B-Instruct, Llama-3-8B, or Phi-3-Mini for the best performance at small scale.
- **Use QLoRA** (4-bit quantised LoRA) to fine-tune on a single consumer GPU. Frameworks:
  unsloth (`pip install unsloth`), axolotl, or llama-factory. Point them at
  `output/lora_dataset.jsonl`.
- **Evaluate** the fine-tuned model against a held-out set of financial QA pairs before
  deploying it in any real trading or analysis context.

### Infrastructure

- **Switch to PostgreSQL** for production runs by setting `DATABASE_URL` in `.env`. The
  SQLAlchemy models are compatible with any supported backend.
- **Add a scheduler** to run the pipeline on a cron and continuously grow the dataset as new
  content is published.
- **Dedup across runs** — the document-level deduplicator currently only deduplicates within
  a single run. The database `content_hash` unique constraint catches cross-run duplicates at
  the persistence layer, but the pipeline should be extended to skip LLM generation for
  documents already in the database.
