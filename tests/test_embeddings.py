from embeddings import create_embeddings
import uuid


def test_create_embeddings_generates_embedding():

    document_id = uuid.uuid4()

    chunks = [
        {
            "document_id": document_id,
            "page": 1,
            "filename": "test.pdf",
            "user_id": uuid.uuid4(),
            "text": "Python is a programming language."
        }
    ]

    result = create_embeddings(chunks)

    assert len(result) == 1
    assert "embedding" in result[0]
    assert len(result[0]["embedding"]) == 384


def test_create_embeddings_preserves_metadata():

    document_id = uuid.uuid4()
    user_id = uuid.uuid4()

    chunks = [
        {
            "document_id": document_id,
            "page": 2,
            "filename": "resume.pdf",
            "user_id": user_id,
            "text": "Machine learning is a field of artificial intelligence."
        }
    ]

    result = create_embeddings(chunks)

    assert result[0]["document_id"] == document_id
    assert result[0]["page"] == 2
    assert result[0]["filename"] == "resume.pdf"
    assert result[0]["user_id"] == user_id
    assert result[0]["text"] == chunks[0]["text"]