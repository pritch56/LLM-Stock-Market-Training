# LLM Dataset Generation Pipeline

Automated pipeline that scrapes web content, cleans it, and uses an LLM to generate high-quality instruction/response pairs for fine-tuning small language models (1B-7B parameters).

## Pipeline Overview

```text
scrape -> clean -> generate -> filter -> export
```

1. **Scrape**: Fetches pages from a configurable source list (static via httpx, dynamic via Playwright)
2. **Clean**: Strips HTML noise, normalises text, deduplicates by content hash
3. **Generate**: Sends cleaned text to Claude or GPT to produce instruction/input/output triples
4. **Filter**: Removes pairs that fail length, language, toxicity, or duplicate checks
5. **Export**: Writes JSONL, Parquet, and HuggingFace dataset formats; tracks everything in SQLite

## Project Structure

```text
config/
  settings.py        - Pydantic settings (loads from .env)
  sources.yaml       - Configurable list of scrape targets
scraper/
  base.py            - Rate limiter, retry-wrapped fetch
  sources.py         - SourceConfig dataclass and YAML loader
  scraper.py         - Async static + Playwright dynamic scraping
cleaners/
  html_cleaner.py    - BeautifulSoup noise removal and text extraction
  text_normalizer.py - Unicode normalisation, URL/reference stripping
  deduplicator.py    - SHA-256 content deduplication
  pipeline.py        - Orchestrates cleaning for a single ScrapeResult
llm_generation/
  client.py          - Anthropic and OpenAI async client wrappers
  prompt_builder.py  - Prompt templates for pair generation
  generator.py       - Async batch generation with concurrency control
filters/
  length_filter.py   - Min/max length checks
  language_filter.py - langdetect-based language gating
  toxicity_filter.py - Regex-based toxicity screen
  duplicate_filter.py - Pair-level deduplication
  pipeline.py        - Runs all filters, logs pass/fail stats
dataset_builder/
  builder.py         - Converts FilterResults to plain dicts
  exporter.py        - JSONL, Parquet, and HuggingFace export
database/
  models.py          - SQLAlchemy ORM: RawDocument, ProcessedDocument, InstructionPair
  db.py              - Engine, session factory, init_db
  persistence.py     - Save helpers called by the pipeline
scripts/
  export_lora.py     - Converts dataset to Alpaca/LoRA text format
  export_hf_hub.py   - Pushes local HF dataset to the Hub
run_pipeline.py      - Entry point
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium  # only needed for dynamic sources

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY (or OPENAI_API_KEY + LLM_PROVIDER=openai)
```

## Configuration

Edit `config/sources.yaml` to add scrape targets:

```yaml
sources:
  - name: "My Source"
    url: "https://example.com/article"
    type: "static"           # or "dynamic" for JS-rendered pages
    content_selector: "article"  # CSS selector for main content
    follow_links: false
    tags: ["my-tag"]
```

All settings can be overridden via environment variables or `.env`. Key settings:

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `LLM_MODEL` | `claude-sonnet-4-6` | Model ID |
| `PAIRS_PER_DOCUMENT` | `3` | Instruction pairs to generate per page |
| `SCRAPE_CONCURRENCY` | `5` | Parallel scrape requests |
| `GENERATION_CONCURRENCY` | `3` | Parallel LLM calls |
| `OUTPUT_DIR` | `output` | Where exports are written |

## Running

```bash
# Full pipeline
python run_pipeline.py

# Custom sources and output
python run_pipeline.py --sources config/sources.yaml --output output/

# Export to LoRA/Alpaca format
python -m scripts.export_lora --input output/dataset.jsonl --output output/lora_dataset.jsonl

# Push to HuggingFace Hub
python -m scripts.export_hf_hub --name your-org/dataset-name
```

## Output

```text
output/
  dataset.jsonl       - Alpaca-format instruction pairs (one JSON object per line)
  dataset.parquet     - Same data in Parquet for efficient loading
  hf_dataset/         - HuggingFace datasets-compatible directory
pipeline.db           - SQLite tracking raw, processed, and generated data
```

Each JSONL record:

```json
{
  "instruction": "Explain the difference between supervised and unsupervised learning.",
  "input": "",
  "output": "Supervised learning uses labelled training data..."
}
```

## Fine-Tuning Compatibility

- **HuggingFace Transformers / SFTTrainer**: load `output/dataset.jsonl` directly or `load_from_disk("output/hf_dataset")`
- **LoRA (llama-factory, axolotl, unsloth)**: use `output/lora_dataset.jsonl` which contains formatted `text` fields in Alpaca template format
- **LitGPT / TinyLlama**: the JSONL format is directly compatible

## Database Schema

| Table | Tracks |
| --- | --- |
| `raw_documents` | Scraped HTML, URL, HTTP status, source tags |
| `processed_documents` | Clean text, word count, language, content hash |
| `instruction_pairs` | Generated pairs, token usage, filter outcome |
