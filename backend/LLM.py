from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()


ABSTENTION_MESSAGE = (
    "I don't have enough information in the provided documents."
)


def is_summary_query(query):
    q = query.lower().strip()

    summary_phrases = [
        "summarize the document",
        "summarise the document",
        "summarize this document",
        "summarise this document",
        "summarize document",
        "summarise document",
        "give me a summary",
        "give me the summary",
        "provide a summary",
        "document summary",
        "summarize the cv",
        "summarise the cv",
        "summarize the resume",
        "summarise the resume",
        "what does the document contain",
        "what does this document contain",
        "what is this document about",
        "give me an overview",
        "give an overview",
    ]

    return any(
        phrase in q
        for phrase in summary_phrases
    )


def generate_answer(query, context):

    client = Groq(
        api_key=os.getenv("GROQ_API_KEY")
    )

    summary_request = is_summary_query(query)

    if summary_request:

        task_instruction = """
The user is asking for a summary or overview of the document.

Summarize the information contained in the supplied document context.

Cover the major useful information available, such as:
- document purpose or subject
- people or organizations
- education
- work experience
- skills
- projects
- dates
- contact information when relevant
- other important facts

Use only information actually present in the supplied context.

Do not invent missing information.

If the supplied context represents only part of the document,
summarize the available information rather than claiming information
that is not present.
"""

    else:

        task_instruction = """
Answer the user's specific question directly.

Use the supplied document context as the source of truth.

If the context contains the answer, provide it clearly.

If the context genuinely does not contain enough information,
say exactly:

"I don't have enough information in the provided documents."

Do not refuse simply because the question uses different wording.

Match normal equivalent terminology.

Examples:

- "contact number" can match phone, mobile, or telephone.
- "languages" can match a languages or programming-languages section.
- "education" can match degree, university, college, or academic details.
- "experience" can match employment or work experience.
"""

    prompt = f"""
You are "Ask My Docs", an AI document assistant.

Answer using ONLY the supplied document context.

RULES:

1. Never use outside knowledge.
2. Never invent, guess, or assume facts.
3. Do not contradict the document context.
4. Preserve exact names, numbers, dates and factual details.
5. Match equivalent wording between the question and the document.
6. Do not mention retrieval, embeddings, vector search, BM25,
   RAG, reranking, or internal systems.
7. Do not repeat the question unnecessarily.
8. Use clean Markdown.
9. Keep answers concise but complete.
10. Bold important names, dates, numbers and terms.

TASK:

{task_instruction}

USER QUESTION:

{query}

DOCUMENT CONTEXT:

{context}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise document-grounded "
                    "question-answering assistant."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0
    )

    answer = response.choices[0].message.content

    if not answer:
        return ABSTENTION_MESSAGE

    return answer.strip()


def build_context(retrieved_chunks):

    sources = []

    for chunk in retrieved_chunks:

        metadata = chunk.get("metadata", {})

        filename = metadata.get(
            "filename",
            "Unknown document"
        )

        document_id = metadata.get(
            "document_id"
        )

        page_number = metadata.get(
            "page",
            "Unknown"
        )

        chunk_text = chunk.get(
            "text",
            ""
        ).strip()

        if not chunk_text:
            continue

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
