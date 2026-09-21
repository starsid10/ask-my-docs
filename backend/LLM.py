from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def generate_answer(query, context):

    prompt = f"""
You are "Ask My Docs", an AI document assistant.

Your job is to answer the user's question using ONLY the information
contained in the provided document context.

IMPORTANT RULES:

1. Never use outside knowledge.
2. Never invent or assume information.
3. If the answer is not available in the context, say exactly:
   "I don't have enough information in the provided documents."
4. Keep the answer directly related to the user's question.
5. Do not mention the retrieval process.
6. Do not mention embeddings, vector search, BM25, RAG, or internal systems.
7. Do not repeat the question unnecessarily.
8. Use clean Markdown formatting.

ANSWER FORMAT:

- Start with a short direct answer.
- If there are multiple points, use bullet points.
- If the question asks for steps, use numbered points.
- If useful, use a short heading.
- Keep paragraphs short.
- Highlight important names, dates, numbers, or terms using **bold**.
- Do not create information that is not present in the context.

Example:

### Answer

The document is about **[topic]**.

Key details:

- **Person:** ...
- **Purpose:** ...
- **Amount:** ...
- **Date:** ...

User question:
{query}

Document context:
{context}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )

    return response.choices[0].message.content


def build_context(retrieved_chunks):

    sources = []

    for chunk in retrieved_chunks:

        metadata = chunk["metadata"]

        filename = metadata.get("filename", "Unknown document")
        document_id = metadata.get("document_id")
        page_number = metadata.get("page", "Unknown")
        chunk_text = chunk.get("text", "")

        source_block = f"""
SOURCE

Filename: {filename}

Document ID: {document_id}

Page: {page_number}

Content:
{chunk_text}
"""

        sources.append(source_block)

    return "\n\n".join(sources)