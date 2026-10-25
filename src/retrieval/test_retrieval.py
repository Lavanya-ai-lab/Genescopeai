
"""
Test scientific evidence retrieval from GeneScope AI.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

COLLECTION_NAME = "genescope_research"

QUESTION = (
    "What does the available research say about "
    "APOE epsilon 4 and Alzheimer's disease risk?"
)

TOP_K = 3


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("NEBIUS_API_KEY")
    base_url = os.getenv("NEBIUS_BASE_URL")
    model = os.getenv("NEBIUS_EMBEDDING_MODEL")

    if not all([api_key, base_url, model]):
        raise ValueError("Missing Nebius configuration.")

    if not CHROMA_DIR.exists():
        raise FileNotFoundError(
            "ChromaDB not found. Build the vector store first."
        )

    embeddings = OpenAIEmbeddings(
        model=model,
        api_key=api_key,
        base_url=base_url,
        check_embedding_ctx_length=False,
    )

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    print(f"Stored chunks: {vector_store._collection.count()}")
    print(f"\nResearch question:\n{QUESTION}")
    print(f"\nRetrieving top {TOP_K} passages...")

    results = vector_store.similarity_search_with_score(
        QUESTION,
        k=TOP_K,
    )

    for rank, (document, distance) in enumerate(
        results,
        start=1,
    ):
        metadata = document.metadata

        print("\n" + "=" * 65)
        print(f"RESULT {rank}")
        print("=" * 65)

        print(
            "Source:",
            metadata.get("document_id", "Unknown"),
        )
        print(
            "Title:",
            metadata.get("title", "Unknown"),
        )
        print(
            "Chunk:",
            metadata.get("chunk_id", "Unknown"),
        )
        print(f"Distance: {distance:.4f}")

        print("\nRetrieved passage:")
        print(document.page_content)


if __name__ == "__main__":
    main()
