from embeddings import model
from vector_store import chroma_client
from rank_bm25 import BM25Okapi
from reranker import rerank


def vector_search(
    collection,
    query,
    user_id,
    document_id,
    n_results
):
    query_embedding = model.encode(query)

    # document_id is unique for every uploaded document.
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
    query_tokens = query.lower().split()

    tokenized_documents = [
        document.lower().split()
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


def retrieve(
    query,
    user_id,
    document_id
):
    collection = chroma_client.get_collection(
        name="documents"
    )

    # Retrieve all chunks belonging to this document.
    # document_id is unique, so this is sufficient here.
    data = collection.get(
        where={
            "document_id": str(document_id)
        }
    )

    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])

    if not documents:
        return []

    # BM25 exact / keyword retrieval
    bm25_results = bm25_search(
        query,
        documents,
        metadatas,
        5
    )

    # Vector semantic retrieval
    vector_results = vector_search(
        collection,
        query,
        user_id,
        document_id,
        5
    )

    # Hybrid RRF fusion
    hybrid_results = hybrid_search(
        vector_results,
        bm25_results,
        5
    )

    if not hybrid_results:
        return []

    # Cross-encoder reranking
    reranked_results = rerank(
        query,
        hybrid_results
    )

    return reranked_results