
"""
Test the Nebius generative LLM connection.

This test does not use ChromaDB or scientific documents.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI


def main():
    load_dotenv()

    client = OpenAI(
        api_key=os.getenv("NEBIUS_API_KEY"),
        base_url=os.getenv("NEBIUS_BASE_URL"),
    )

    model = os.getenv("NEBIUS_LLM_MODEL")

    if not model:
        raise ValueError("NEBIUS_LLM_MODEL is not configured.")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a concise scientific assistant.",
            },
            {
                "role": "user",
                "content": (
                    "In one sentence, explain the difference "
                    "between a genetic risk factor and a "
                    "guaranteed disease outcome."
                ),
            },
        ],
        temperature=0,
        max_tokens=150,
    )

    print("Model:", model)
    print("Response:", response.choices[0].message.content)
    print("LLM connection test completed.")


if __name__ == "__main__":
    main()
