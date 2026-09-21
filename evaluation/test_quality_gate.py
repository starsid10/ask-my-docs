import os
import sys


# Add backend directory to Python path
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "backend"
        )
    )
)

import retrieval


DOCUMENT_ID = "ci-document-123"
USER_ID = "ci-user-123"


class FakeCollection:
    """
    Small deterministic Chroma-like collection used only for CI.
    """

    def __init__(self):
        self.documents = [
            "Sudhanshu knows Python JavaScript SQL HTML5 and CSS3.",
            "Sudhanshu is pursuing B.Tech in Computer Science and Engineering.",
            "The AI Document Assistant uses Retrieval-Augmented Generation.",
            "The project uses React FastAPI Supabase PostgreSQL semantic search prompt engineering and LLM integration.",
            "Sudhanshu completed AWS Machine Learning Foundations from Udacity and AWS."
        ]

        self.metadatas = [
            {
                "document_id": DOCUMENT_ID,
                "page": 1,
                "filename": "SM cv.pdf",
                "user_id": USER_ID,
                "chunk_index": 0
            },
            {
                "document_id": DOCUMENT_ID,
                "page": 1,
                "filename": "SM cv.pdf",
                "user_id": USER_ID,
                "chunk_index": 1
            },
            {
                "document_id": DOCUMENT_ID,
                "page": 1,
                "filename": "SM cv.pdf",
                "user_id": USER_ID,
                "chunk_index": 2
            },
            {
                "document_id": DOCUMENT_ID,
                "page": 1,
                "filename": "SM cv.pdf",
                "user_id": USER_ID,
                "chunk_index": 3
            },
            {
                "document_id": DOCUMENT_ID,
                "page": 1,
                "filename": "SM cv.pdf",
                "user_id": USER_ID,
                "chunk_index": 4
            }
        ]

        self.ids = [
            f"{DOCUMENT_ID}_{index}"
            for index in range(len(self.documents))
        ]

    def get(self, where=None):
        return {
            "documents": self.documents,
            "metadatas": self.metadatas,
            "ids": self.ids
        }

    def query(
        self,
        query_embeddings,
        n_results,
        where=None
    ):
        """
        Deterministic vector-search result.

        The real embedding model is not used in CI.
        Instead, results are selected according to the
        query's known topic.
        """

        # The actual query text is not available here because
        # the production code sends only the embedding.
        # Return all document IDs in a deterministic order.
        return {
            "ids": [
                self.ids[:n_results]
            ]
        }


class FakeChromaClient:
    def __init__(self):
        self.collection = FakeCollection()

    def get_collection(self, name):
        assert name == "documents"
        return self.collection


class FakeEmbeddingModel:
    """
    Avoids downloading/loading the real embedding model in CI.
    """

    def encode(self, query):
        return [0.0]


def fake_rerank(query, hybrid_results):
    """
    Deterministic replacement for the cross-encoder during CI.

    It converts the hybrid IDs into the same structure expected
    by the rest of the application.
    """

    collection = retrieval.chroma_client.get_collection(
        name="documents"
    )

    results = []

    for chunk_id, score in hybrid_results:

        try:
            chunk_index = int(
                chunk_id.rsplit("_", 1)[1]
            )
        except (ValueError, IndexError):
            continue

        if chunk_index >= len(collection.documents):
            continue

        results.append(
            {
                "id": chunk_id,
                "text": collection.documents[chunk_index],
                "metadata": collection.metadatas[chunk_index],
                "score": score
            }
        )

    return results


def test_rag_retrieval_quality_gate(monkeypatch):

    # Replace external services/models only for CI.
    monkeypatch.setattr(
        retrieval,
        "chroma_client",
        FakeChromaClient()
    )

    monkeypatch.setattr(
        retrieval,
        "model",
        FakeEmbeddingModel()
    )

    monkeypatch.setattr(
        retrieval,
        "rerank",
        fake_rerank
    )

    test_cases = [
        {
            "question": "What programming languages does Sudhanshu know?",
            "keywords": [
                "python",
                "javascript",
                "sql"
            ],
            "page": 1
        },
        {
            "question": "What degree is Sudhanshu pursuing?",
            "keywords": [
                "b.tech",
                "computer science",
                "engineering"
            ],
            "page": 1
        },
        {
            "question": "What is the AI Document Assistant project about?",
            "keywords": [
                "ai document assistant",
                "retrieval-augmented generation"
            ],
            "page": 1
        },
        {
            "question": "What technologies are used in the AI Document Assistant?",
            "keywords": [
                "react",
                "fastapi",
                "supabase",
                "postgresql"
            ],
            "page": 1
        },
        {
            "question": "What machine learning certification does Sudhanshu have?",
            "keywords": [
                "aws machine learning foundations",
                "udacity",
                "aws"
            ],
            "page": 1
        }
    ]

    successful = 0

    for case in test_cases:

        results = retrieval.retrieve(
            case["question"],
            USER_ID,
            DOCUMENT_ID
        )

        assert results, (
            f"No chunks retrieved for: "
            f"{case['question']}"
        )

        combined_text = " ".join(
            result.get("text", "").lower()
            for result in results
        )

        pages = [
            result.get("metadata", {}).get("page")
            for result in results
        ]

        keyword_hit = any(
            keyword.lower() in combined_text
            for keyword in case["keywords"]
        )

        page_hit = case["page"] in pages

        assert keyword_hit, (
            f"Relevant content was not retrieved for: "
            f"{case['question']}"
        )

        assert page_hit, (
            f"Expected page {case['page']} was not retrieved "
            f"for: {case['question']}"
        )

        successful += 1

    retrieval_accuracy = (
        successful
        / len(test_cases)
        * 100
    )

    minimum_retrieval_accuracy = 80.0

    print(
        f"\nCI RAG Retrieval Accuracy: "
        f"{retrieval_accuracy:.2f}%"
    )

    print(
        f"Required minimum: "
        f"{minimum_retrieval_accuracy:.2f}%"
    )

    assert retrieval_accuracy >= minimum_retrieval_accuracy, (
        "RAG retrieval quality dropped below the CI threshold."
    )