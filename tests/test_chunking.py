from chunking import chunk_text
import uuid


def test_chunk_text_creates_chunks():

    document_id = uuid.uuid4()

    extracted_text = {
        1: """
        This is a sample document.
        It contains information about Python,
        SQL, machine learning and data analysis.
        We are testing whether the document
        is correctly divided into chunks.
        """
    }

    chunks = chunk_text(extracted_text, document_id)

    assert len(chunks) > 0

def test_chunk_metadata():

    document_id = uuid.uuid4()

    extracted_text = {
        1: "This is page one of the document."
    }

    chunks = chunk_text(extracted_text, document_id)

    assert chunks[0]["document_id"] == document_id
    assert chunks[0]["page"] == 1
    assert "text" in chunks[0]