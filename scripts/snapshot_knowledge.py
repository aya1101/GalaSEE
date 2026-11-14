import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the allowlisted knowledge snapshot registry.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--fetch-approved", action="store_true", help="Reserved for a reviewed ingestion job; never called by the chatbot.")
    parser.parse_args()
    root = Path(__file__).resolve().parent.parent / "knowledge"
    sources = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    invalid = [source["documentId"] for source in sources if source.get("status") != "approved" or not source.get("canonicalUrl", "").startswith("https://")]
    if invalid:
        print(f"invalid sources: {', '.join(invalid)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
