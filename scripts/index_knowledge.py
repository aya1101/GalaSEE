import argparse
import hashlib
import json
from pathlib import Path


def build_index(root: Path) -> dict:
    sources = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    claims = json.loads((root / "claims.json").read_text(encoding="utf-8"))
    approved = {source["documentId"] for source in sources if source.get("status") == "approved"}
    chunks = [claim for claim in claims if claim.get("reviewStatus") == "approved" and claim.get("sourceDocumentId") in approved]
    digest = hashlib.sha256(json.dumps(chunks, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"version": f"knowledge-{digest[:16]}", "chunks": chunks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent / "knowledge"
    index = build_index(root)
    target = root / "index.json"
    if args.check:
        if target.exists() and json.loads(target.read_text(encoding="utf-8")) == index:
            return 0
        print("knowledge index is missing or stale")
        return 1
    if args.rebuild or not target.exists():
        target.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
