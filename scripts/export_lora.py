"""
Export the dataset in Alpaca/LoRA-compatible format.

Usage: python -m scripts.export_lora --input output/dataset.jsonl --output output/lora_dataset.jsonl
"""
import argparse
import json
from pathlib import Path


_ALPACA_TEMPLATE = (
    "Below is an instruction that describes a task"
    "{input_suffix}. Write a response that appropriately completes the request.\n\n"
    "### Instruction:\n{instruction}\n\n"
    "{input_block}"
    "### Response:\n{output}"
)


def format_alpaca(record: dict) -> dict:
    has_input = bool(record.get("input", "").strip())
    input_suffix = ", paired with an input that provides further context" if has_input else ""
    input_block = f"### Input:\n{record['input']}\n\n" if has_input else ""

    return {
        "text": _ALPACA_TEMPLATE.format(
            input_suffix=input_suffix,
            instruction=record["instruction"],
            input_block=input_block,
            output=record["output"],
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("output/dataset.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("output/lora_dataset.jsonl"))
    args = parser.parse_args()

    records = []
    with open(args.input) as f:
        for line in f:
            records.append(json.loads(line))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for r in records:
            f.write(json.dumps(format_alpaca(r), ensure_ascii=False) + "\n")

    print(f"Exported {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
