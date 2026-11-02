"""Frozen inputs and corpus integrity checks. No network or inference."""

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"
DATASET = EVALS / "apoe_v1.jsonl"
CORPUS = EVALS / "corpus.json"
MANIFEST = EVALS / "manifest.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def load_cases(path=DATASET):
    cases = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if len(cases) != 40 or len({c["id"] for c in cases}) != 40:
        raise ValueError("Expected exactly 40 uniquely identified cases.")
    corpus = {c["chunk_id"]: c for c in json.loads(CORPUS.read_text())}
    for case in cases:
        if case["expected_route"] not in {"research", "clarification", "out_of_scope"}:
            raise ValueError(f"Invalid expected route: {case['id']}")
        review = case["human_review"]
        if review["status"] not in {"draft", "reviewed"}:
            raise ValueError("Review status must be draft or reviewed.")
        if review["status"] == "reviewed" and not all(
            review.get(k) for k in ("reviewer", "reviewed_at", "notes")
        ):
            raise ValueError("Reviewed cases require a named reviewer, date, and notes.")
        for reference in case["references"]:
            record = corpus.get(reference["chunk_id"])
            if not record or reference["quote"] not in record["content"]:
                raise ValueError(f"Reference does not match frozen evidence: {case['id']}")
        if not case["expected_behavior"] or not case["forbidden_claims"]:
            raise ValueError("Each case needs an explicit rubric.")
    return cases


def index_contents(db=ROOT / "chroma_db/chroma.sqlite3"):
    """Inspect only the target collection in SQLite read-only mode."""
    with sqlite3.connect(f"file:{Path(db).resolve()}?mode=ro", uri=True) as connection:
        rows = connection.execute(
            "SELECT e.embedding_id, m.string_value FROM embeddings e "
            "JOIN embedding_metadata m ON m.id=e.id "
            "JOIN segments s ON s.id=e.segment_id "
            "JOIN collections c ON c.id=s.collection "
            "WHERE c.name=? AND m.key='chroma:document'",
            ("genescope_research",),
        ).fetchall()
    if len(rows) != len(dict(rows)):
        raise ValueError("Duplicate collection chunk IDs.")
    return dict(rows)


def verify_frozen(cases=None, check_index=True):
    cases = load_cases() if cases is None else cases
    manifest = json.loads(MANIFEST.read_text())
    corpus = json.loads(CORPUS.read_text())
    if digest(corpus) != manifest["corpus_sha256"]:
        raise ValueError("Frozen corpus changed.")
    # Review annotations can be completed without changing the case inputs.
    inputs = [{k: v for k, v in c.items() if k != "human_review"} for c in cases]
    if digest(inputs) != manifest["cases_sha256"]:
        raise ValueError("Frozen evaluation inputs changed; create a new dataset version.")
    if check_index and index_contents() != {c["chunk_id"]: c["content"] for c in corpus}:
        raise ValueError("Active Chroma collection differs from the frozen corpus.")
    return manifest
