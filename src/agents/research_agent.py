
"""
Research Agent for GeneScope AI.

Retrieves scientific evidence from ChromaDB and
returns updates to the shared LangGraph state.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from src.graph.state import ResearchState


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "genescope_research"
TOP_K = 3


def research_agent(state: ResearchState) -> dict:
    """Retrieve scientific evidence for a research question."""

    question = state["question"]

    if state.get("needs_clarification", False):
        return {
            "agent_log": state.get("agent_log", []) + [
                "Research Agent paused: clarification required."
            ]
        }

    if state.get("out_of_scope", False):
        return {
            "agent_log": state.get("agent_log", []) + [
                "Research Agent paused: topic outside the indexed collection."
            ]
        }

    try:
        load_dotenv(PROJECT_ROOT / ".env")

        api_key = os.getenv("NEBIUS_API_KEY")
        base_url = os.getenv("NEBIUS_BASE_URL")
        model = os.getenv("NEBIUS_EMBEDDING_MODEL")

        if not all([api_key, base_url, model]):
            raise ValueError("Missing Nebius configuration.")

        if not CHROMA_DIR.exists():
            raise FileNotFoundError(
                "ChromaDB directory not found."
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

        results = vector_store.similarity_search_with_score(
            question,
            k=TOP_K,
        )

        evidence = []

        for document, distance in results:
            evidence.append(
                {
                    "document_id": document.metadata.get(
                        "document_id", ""
                    ),
                    "title": document.metadata.get(
                        "title", ""
                    ),
                    "chunk_id": document.metadata.get(
                        "chunk_id", ""
                    ),
                    "content": document.page_content,
                    "distance": float(distance),
                    "metadata": document.metadata,
                }
            )

        return {
            "retrieved_evidence": evidence,
            "agent_log": state.get("agent_log", []) + [
                f"Research Agent retrieved {len(evidence)} passages."
            ],
        }

    except Exception as exc:
        return {
            "retrieved_evidence": [],
            "errors": state.get("errors", []) + [
                f"Research Agent error: {exc}"
            ],
            "agent_log": state.get("agent_log", []) + [
                "Research Agent failed."
            ],
        }
