
"""
Normalize an NCBI Gene record into a research document.

Input:
    data/raw/apoe_gene.json

Output:
    data/processed/apoe_gene_normalized.json
"""

import json
from pathlib import Path

from src.ingestion.config import TARGET_GENE_ID


# Locate the project root from this script's location.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = PROJECT_ROOT / "data/raw/apoe_gene.json"

OUTPUT_FILE = (
    PROJECT_ROOT / "data/processed/apoe_gene_normalized.json"
)


def normalize_gene_record(raw_data: dict) -> dict:
    """
    Convert an NCBI Gene summary into our standard format.
    """

    # NCBI stores gene records under result -> gene ID.
    result = raw_data["result"]
    gene = result[TARGET_GENE_ID]

    # Extract fields needed for our initial research document.
    gene_name = gene["name"]
    description = gene["description"]
    summary = gene.get("summary", "")

    # Keep source text separate from structured metadata.
    content = (
        f"Gene: {gene_name}\n"
        f"Description: {description}\n"
        f"Summary: {summary}"
    )

    normalized_document = {
        "document_id": f"ncbi_gene_{TARGET_GENE_ID}",
        "document_type": "gene",
        "title": f"{gene_name} - {description}",
        "content": content,
        "metadata": {
            "source": "NCBI Gene",
            "gene_id": TARGET_GENE_ID,
            "gene_symbol": gene_name,
            "source_url": (
                f"https://www.ncbi.nlm.nih.gov/gene/"
                f"{TARGET_GENE_ID}"
            ),
        },
    }

    return normalized_document


def main():
    """Read, normalize, and save the gene record."""

    with RAW_FILE.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    document = normalize_gene_record(raw_data)

    # Create the destination directory if needed.
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            document,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Normalization successful!")
    print(f"Document ID: {document['document_id']}")
    print(f"Gene: {document['metadata']['gene_symbol']}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
