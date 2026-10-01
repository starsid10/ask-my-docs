from embeddings import model
from vector_store import chroma_client
from rank_bm25 import BM25Okapi
from reranker import rerank
import re


def normalize_tokens(text):
    """
    Normalize text for keyword retrieval.

    Removes punctuation while preserving words and numbers.
    This improves matching for things such as:
    phone numbers, emails, names, skills and dates.
    """
    return re.findall(
        r"\b[\w@.+#/-]+\b",
        text.lower()
    )


def is_summary_query(query):
    """
    Detect document-level summary/overview requests.
    """
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


def vector_search(
    collection,
    query,
    user_id,
    document_id,
    n_results
):
    query_embedding = model.encode(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={
            "document_id": str(document_id)
        }
    )

    return results


def bm25_search(
    query,
    documents,
    metadatas,
    n_results
):
    query_tokens = normalize_tokens(query)

    tokenized_documents = [
        normalize_tokens(document)
        for document in documents
    ]

    bm25 = BM25Okapi(tokenized_documents)

    scores = bm25.get_scores(query_tokens)

    scored_documents = list(
        zip(
            documents,
            scores,
            metadatas
        )
    )

    ranked_documents = sorted(
        scored_documents,
        key=lambda x: x[1],
        reverse=True
    )

    return ranked_documents[:n_results]


def hybrid_search(
    vector_results,
    bm25_results,
    n_results
):
    rrf_scores = {}

    vector_ids = vector_results.get("ids", [[]])[0]

    for rank, chunk_id in enumerate(
        vector_ids,
        start=1
    ):
        rrf_score = 1 / (60 + rank)

        rrf_scores[chunk_id] = (
            rrf_scores.get(chunk_id, 0)
            + rrf_score
        )

    for rank, result in enumerate(
        bm25_results,
        start=1
    ):
        metadata = result[2]

        chunk_id = (
            f"{metadata['document_id']}_"
            f"{metadata['chunk_index']}"
        )

        rrf_score = 1 / (60 + rank)

        rrf_scores[chunk_id] = (
            rrf_scores.get(chunk_id, 0)
            + rrf_score
        )

    ranked_chunks = sorted(
        rrf_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return ranked_chunks[:n_results]


def representative_chunks(
    documents,
    metadatas,
    max_chunks=12
):
    """
    Select representative chunks from across the document.

    Used for document-level summaries so the LLM does not receive
    only the chunks that happen to match the word 'summary'.
    """

    if not documents:
        return []

    total = len(documents)

    if total <= max_chunks:
        selected_indices = list(range(total))
    else:
        # Always include beginning and ending content.
        selected_indices = {
            0,
            total - 1
        }

        # Evenly sample the rest of the document.
        for i in range(max_chunks - 2):
            position = round(
                i * (total - 1) / (max_chunks - 3)
            )
            selected_indices.add(position)

        selected_indices = sorted(selected_indices)

        # Hard limit.
        selected_indices = selected_indices[:max_chunks]

    results = []

    for index in selected_indices:
        results.append({
            "chunk_id": (
                f"{metadatas[index]['document_id']}_"
                f"{metadatas[index]['chunk_index']}"
            ),
            "text": documents[index],
            "metadata": metadatas[index],
            "rrf_score": 0.0,
            "cross_encoder_score": 0.0
        })

    return results


def retrieve(
    query,
    user_id,
    document_id
):
    collection = chroma_client.get_collection(
        name="documents"
    )

    data = collection.get(
        where={
            "document_id": str(document_id)
        }
    )

    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])

    if not documents:
        return []

    # ---------------------------------------------------------
    # Document-level summary mode
    # ---------------------------------------------------------
    if is_summary_query(query):
        return representative_chunks(
            documents,
            metadatas,
            max_chunks=12
        )

    # ---------------------------------------------------------
    # Normal question retrieval
    # ---------------------------------------------------------

    # BM25 keyword retrieval
    bm25_results = bm25_search(
        query,
        documents,
        metadatas,
        15
    )

    # Vector semantic retrieval
    vector_results = vector_search(
        collection,
        query,
        user_id,
        document_id,
        15
    )

    # Hybrid RRF fusion
    hybrid_results = hybrid_search(
        vector_results,
        bm25_results,
        12
    )

    if not hybrid_results:
        return []

    # Cross-encoder reranking
    reranked_results = rerank(
        query,
        hybrid_results
    )

    # Give the LLM only the strongest final candidates.
    return reranked_results[:6]
