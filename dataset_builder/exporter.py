import json
import logging
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


def export_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info("Wrote %d records to %s", len(records), path)


def export_parquet(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(records)
    pq.write_table(table, path)
    logger.info("Wrote %d records to %s", len(records), path)


def export_hf_dataset(records: list[dict[str, Any]], path: Path) -> None:
    try:
        from datasets import Dataset
    except ImportError:
        logger.warning("datasets library not installed; skipping HuggingFace export")
        return

    path.mkdir(parents=True, exist_ok=True)
    ds = Dataset.from_list(records)
    ds.save_to_disk(str(path))
    logger.info("Saved HuggingFace dataset (%d rows) to %s", len(ds), path)


def export_all(records: list[dict[str, Any]], output_dir: Path) -> None:
    export_jsonl(records, output_dir / "dataset.jsonl")
    export_parquet(records, output_dir / "dataset.parquet")
    export_hf_dataset(records, output_dir / "hf_dataset")
