
"""
Load GeneScope AI's normalized scientific documents
into LangChain Document objects.
"""

import json
from pathlib import Path

from langchain_core.documents import Document


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data/processed"


def load_research_documents():
    """Load and validate normalized scientific records."""

    documents = []

    files = sorted(PROCESSED_DIR.glob("*_normalized.json"))

    for file_path in files:
        with file_path.open("r", encoding="utf-8") as file:
            record = json.load(file)

        # Validate the required fields.
        required_fields = [
            "document_id",
            "document_type",
            "title",
            "content",
            "metadata",
        ]

        missing = [
            field for field in required_fields
            if field not in record
        ]

        if missing:
            raise ValueError(
                f"{file_path.name} is missing: {missing}"
            )

        if not isinstance(record["content"], str):
            raise ValueError(
                f"{file_path.name} has invalid content."
            )

        if not isinstance(record["metadata"], dict):
            raise ValueError(
                f"{file_path.name} has invalid metadata."
            )

        # LangChain Document stores text and metadata.
        metadata = {
            **record["metadata"],
            "document_id": record["document_id"],
            "document_type": record["document_type"],
            "title": record["title"],
        }

        document = Document(
            page_content=record["content"],
            metadata=metadata,
        )

        documents.append(document)

    return documents


def main():
    documents = load_research_documents()

    print(f"Documents loaded: {len(documents)}")

    for document in documents:
        print(
            f"- {document.metadata['document_id']}: "
            f"{len(document.page_content)} characters"
        )


if __name__ == "__main__":
    main()
