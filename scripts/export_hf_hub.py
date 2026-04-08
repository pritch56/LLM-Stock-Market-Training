"""
Push the local HuggingFace dataset to the Hub.

Usage: python -m scripts.export_hf_hub --dataset output/hf_dataset --name your-org/dataset-name
"""
import argparse
from pathlib import Path


def main() -> None:
    from datasets import load_from_disk
    from config.settings import settings

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("output/hf_dataset"))
    parser.add_argument("--name", type=str, default=settings.hf_dataset_name)
    parser.add_argument("--token", type=str, default=settings.hf_token)
    args = parser.parse_args()

    if not args.name:
        raise SystemExit("Provide --name or set HF_DATASET_NAME in .env")

    ds = load_from_disk(str(args.dataset))
    ds.push_to_hub(args.name, token=args.token)
    print(f"Pushed {len(ds)} records to https://huggingface.co/datasets/{args.name}")


if __name__ == "__main__":
    main()
