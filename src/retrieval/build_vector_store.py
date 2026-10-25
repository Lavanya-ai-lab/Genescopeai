
"""
Build GeneScope AI's local scientific vector database.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CHUNKS_FILE = (
    PROJECT_ROOT / "data/processed/research_chunks.json"
)

CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "genescope_research"


def clean_metadata(metadata):
    """
    Chroma metadata must contain simple values.
    Convert lists and dictionaries to JSON strings.
    """

    cleaned = {}

    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        elif value is not None:
            cleaned[key] = json.dumps(
                value,
                ensure_ascii=False,
            )

    return cleaned


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("NEBIUS_API_KEY")
    base_url = os.getenv("NEBIUS_BASE_URL")
    model = os.getenv("NEBIUS_EMBEDDING_MODEL")

    if not all([api_key, base_url, model]):
        raise ValueError("Missing Nebius configuration.")

    with CHUNKS_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not records:
        raise ValueError("No research chunks found.")

    documents = []
    ids = []

    for record in records:
        document = Document(
            page_content=record["content"],
            metadata=clean_metadata(record["metadata"]),
        )

        documents.append(document)
        ids.append(record["chunk_id"])

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs detected.")

    embeddings = OpenAIEmbeddings(
        model=model,
        api_key=api_key,
        base_url=base_url,
        check_embedding_ctx_length=False,
    )


    # Remove the previous research collection so obsolete
    # chunks do not remain after changing chunking rules.
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(name=COLLECTION_NAME)
        print("Previous research collection removed.")
    except chromadb.errors.NotFoundError:
        print("No previous research collection found.")


    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    print(f"Documents to store: {len(documents)}")
    print(f"Embedding model: {model}")
    print("Generating embeddings and storing documents...")

    # Stable IDs let Chroma update existing records
    # instead of creating duplicates on later runs.
    vector_store.add_documents(
        documents=documents,
        ids=ids,
    )

    count = vector_store._collection.count()

    print("\nVector store built successfully!")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Stored records: {count}")
    print(f"Database directory: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
