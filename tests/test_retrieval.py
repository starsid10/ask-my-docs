from retrieval import bm25_search
from retrieval import hybrid_search
from reranker import rerank


def test_bm25_returns_relevant_document():

    documents = [
        "Python is a programming language.",
        "SQL is used for database queries.",
        "Machine learning uses data to build models."
    ]

    metadatas = [
        {"document_id": "doc1", "chunk_index": 0},
        {"document_id": "doc2", "chunk_index": 0},
        {"document_id": "doc3", "chunk_index": 0}
    ]

    results = bm25_search(
        "Python programming",
        documents,
        metadatas,
        1
    )

    assert len(results) == 1
    assert results[0][0] == "Python is a programming language."


def test_hybrid_search_combines_results():

    vector_results = {
        "ids": [
            ["doc1_0", "doc2_0"]
        ]
    }

    bm25_results = [
        (
            "Python is a programming language.",
            8.5,
            {
                "document_id": "doc1",
                "chunk_index": 0
            }
        ),
        (
            "SQL is used for databases.",
            7.0,
            {
                "document_id": "doc3",
                "chunk_index": 0
            }
        )
    ]

    results = hybrid_search(
        vector_results,
        bm25_results,
        3
    )

    result_ids = [item[0] for item in results]

    assert "doc1_0" in result_ids
    assert "doc2_0" in result_ids
    assert "doc3_0" in result_ids


def test_rerank_orders_candidates_by_cross_encoder_score(monkeypatch):

    class FakeCollection:

        def get(self, ids):

            data = {
                "doc1_0": {
                    "text": "Python is a programming language.",
                    "metadata": {
                        "document_id": "doc1",
                        "page": 1
                    }
                },
                "doc2_0": {
                    "text": "SQL is used for database queries.",
                    "metadata": {
                        "document_id": "doc2",
                        "page": 2
                    }
                }
            }

            item = data[ids[0]]

            return {
                "documents": [item["text"]],
                "metadatas": [item["metadata"]]
            }


    class FakeChromaClient:

        def get_collection(self, name):
            return FakeCollection()


    class FakeReranker:

        def predict(self, pairs):
            return [0.2, 0.9]


    monkeypatch.setattr(
        "reranker.chroma_client",
        FakeChromaClient()
    )

    monkeypatch.setattr(
        "reranker.reranker",
        FakeReranker()
    )


    candidates = [
        ("doc1_0", 0.02),
        ("doc2_0", 0.01)
    ]

    results = rerank(
        "database query",
        candidates
    )

    assert len(results) == 2
    assert results[0]["chunk_id"] == "doc2_0"
    assert results[1]["chunk_id"] == "doc1_0"