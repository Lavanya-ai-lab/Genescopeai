
"""
Test the Nebius embedding connection for GeneScope AI.
"""

import os

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


def main():
    load_dotenv()

    api_key = os.getenv("NEBIUS_API_KEY")
    base_url = os.getenv("NEBIUS_BASE_URL")
    model = os.getenv("NEBIUS_EMBEDDING_MODEL")

    if not all([api_key, base_url, model]):
        raise ValueError(
            "Missing Nebius configuration in .env"
        )

    embeddings = OpenAIEmbeddings(
        model=model,
        api_key=api_key,
        base_url=base_url,
        check_embedding_ctx_length=False,
    )

    test_text = (
        "APOE is a gene associated with "
        "Alzheimer's disease risk."
    )

    print("Connecting to Nebius...")
    print(f"Embedding model: {model}")

    vector = embeddings.embed_query(test_text)

    print("\nEmbedding created successfully!")
    print(f"Vector dimensions: {len(vector)}")
    print(f"First 5 values: {vector[:5]}")


if __name__ == "__main__":
    main()
