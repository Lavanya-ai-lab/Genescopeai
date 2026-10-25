
"""
Split GeneScope AI research documents into searchable chunks.
"""

import json
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.retrieval.load_documents import load_research_documents


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_FILE = PROJECT_ROOT / "data/processed/research_chunks.json"

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


def create_chunks():
    """Load research documents and split their text."""

    documents = load_research_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    
    # Remove article title headers before chunking.
    # Titles remain available in document metadata for citations.
    for document in documents:
        title = document.metadata.get("title", "")
        text = document.page_content

        title_header = f"Title: {title}"

        if title and text.startswith(title_header):
            document.page_content = text[len(title_header):].strip()

    chunks = splitter.split_documents(documents)


    # Preserve source identity and give every chunk a unique ID.
    counters = {}

    for chunk in chunks:
        document_id = chunk.metadata["document_id"]

        index = counters.get(document_id, 0)
        counters[document_id] = index + 1

        chunk.metadata["chunk_id"] = (
            f"{document_id}_chunk_{index:03d}"
        )

    return chunks


def main():
    chunks = create_chunks()

    records = []

    for chunk in chunks:
        records.append(
            {
                "chunk_id": chunk.metadata["chunk_id"],
                "content": chunk.page_content,
                "metadata": chunk.metadata,
            }
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Chunking successful!")
    print(f"Total chunks: {len(chunks)}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Chunk overlap: {CHUNK_OVERLAP}")

    print("\nChunks per document:")

    counts = {}

    for chunk in chunks:
        document_id = chunk.metadata["document_id"]
        counts[document_id] = counts.get(document_id, 0) + 1

    for document_id, count in sorted(counts.items()):
        print(f"- {document_id}: {count}")

    if chunks:
        print("\nFirst chunk preview:")
        print(chunks[0].page_content[:300])


if __name__ == "__main__":
    main()
