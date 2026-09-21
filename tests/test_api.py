from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_home_endpoint():

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["server"] == "ON"


def test_upload_requires_authentication():

    response = client.post(
        "/upload",
        files={
            "file": (
                "test.pdf",
                b"fake pdf content",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 401


def test_ask_requires_authentication():

    response = client.post(
        "/ask",
        json={
            "query": "What is the email address?",
            "document_id": "00000000-0000-0000-0000-000000000000",
            "conversation_id": "00000000-0000-0000-0000-000000000000"
        }
    )

    assert response.status_code == 401


def test_ask_rejects_document_not_owned_by_user(monkeypatch):

    class FakeUser:
        id = "user-123"


    class FakeAuth:

        def get_user(self, token):

            return type(
                "Result",
                (),
                {
                    "user": FakeUser()
                }
            )()


    class FakeQuery:

        def select(self, *args):
            return self

        def eq(self, *args):
            return self

        def execute(self):

            return type(
                "Result",
                (),
                {
                    "data": []
                }
            )()


    class FakeSupabase:

        auth = FakeAuth()

        def table(self, name):

            return FakeQuery()


    monkeypatch.setattr(
        "main.supabase",
        FakeSupabase()
    )

    monkeypatch.setattr(
        "main.create_client",
        lambda *args, **kwargs:
            FakeSupabase()
    )


    def fail_if_retrieval_runs(*args, **kwargs):

        raise AssertionError(
            "Retrieval should not run for an unauthorized document."
        )


    monkeypatch.setattr(
        "main.retrieve",
        fail_if_retrieval_runs
    )


    response = client.post(
        "/ask",
        headers={
            "Authorization": "Bearer fake-token"
        },
        json={
            "query": "What is the email address?",
            "document_id": "document-123",
            "conversation_id": "conversation-123"
        }
    )


    assert response.status_code == 404

    assert response.json()["detail"] == (
        "Document not found."
    )


def test_ask_success_returns_answer_and_citation(monkeypatch):

    saved_messages = []

    saved_citations = []


    class FakeUser:

        id = "user-123"


    class FakeAuth:

        def get_user(self, token):

            return type(
                "Result",
                (),
                {
                    "user": FakeUser()
                }
            )()


    class FakeQuery:

        def __init__(self, table_name):

            self.table_name = table_name
            self.inserted_data = None


        def select(self, *args):

            return self


        def eq(self, *args):

            return self


        def insert(self, data):

            self.inserted_data = data

            return self


        def execute(self):

            # -----------------------------------------
            # DOCUMENTS
            # -----------------------------------------

            if self.table_name == "documents":

                return type(
                    "Result",
                    (),
                    {
                        "data": [
                            {
                                "document_id": "document-123"
                            }
                        ]
                    }
                )()


            # -----------------------------------------
            # DOCUMENT CHUNKS
            # -----------------------------------------

            if self.table_name == "document_chunks":

                return type(
                    "Result",
                    (),
                    {
                        "data": [
                            {
                                "page": 1
                            }
                        ]
                    }
                )()


            # -----------------------------------------
            # CONVERSATIONS
            # -----------------------------------------

            if self.table_name == "conversations":

                return type(
                    "Result",
                    (),
                    {
                        "data": [
                            {
                                "conversation_id":
                                    "conversation-123",

                                "user_id":
                                    "user-123"
                            }
                        ]
                    }
                )()


            # -----------------------------------------
            # MESSAGES
            # -----------------------------------------

            if self.table_name == "messages":

                saved_messages.append(
                    self.inserted_data
                )

                if (
                    self.inserted_data["role"]
                    == "assistant"
                ):

                    return type(
                        "Result",
                        (),
                        {
                            "data": [
                                {
                                    "message_id":
                                        "assistant-message-123"
                                }
                            ]
                        }
                    )()

                return type(
                    "Result",
                    (),
                    {
                        "data": [
                            {
                                "message_id":
                                    "user-message-123"
                            }
                        ]
                    }
                )()


            # -----------------------------------------
            # CITATIONS
            # -----------------------------------------

            if self.table_name == "citations":

                saved_citations.append(
                    self.inserted_data
                )

                return type(
                    "Result",
                    (),
                    {
                        "data": [
                            self.inserted_data
                        ]
                    }
                )()


            # -----------------------------------------
            # DEFAULT RESPONSE
            # -----------------------------------------

            return type(
                "Result",
                (),
                {
                    "data": []
                }
            )()


    class FakeSupabase:

        auth = FakeAuth()

        def table(self, name):

            return FakeQuery(name)


    # ---------------------------------------------
    # MOCK SUPABASE
    # ---------------------------------------------

    monkeypatch.setattr(
        "main.supabase",
        FakeSupabase()
    )

    monkeypatch.setattr(
        "main.create_client",
        lambda *args, **kwargs:
            FakeSupabase()
    )


    # ---------------------------------------------
    # MOCK RETRIEVAL
    # ---------------------------------------------

    fake_chunks = [

        {
            "text":
                "Palak knows Python and SQL.",

            "metadata": {

                "document_id":
                    "document-123",

                "page":
                    1,

                "filename":
                    "Palak_Resume.pdf"
            }
        }
    ]


    monkeypatch.setattr(
        "main.retrieve",
        lambda query, user_id, document_id:
            fake_chunks
    )


    # ---------------------------------------------
    # MOCK CONTEXT
    # ---------------------------------------------

    monkeypatch.setattr(
        "main.build_context",
        lambda chunks:
            "Palak knows Python and SQL."
    )


    # ---------------------------------------------
    # MOCK LLM ANSWER
    # ---------------------------------------------

    monkeypatch.setattr(
        "main.generate_answer",
        lambda query, context:
            "Palak knows Python and SQL."
    )


    # ---------------------------------------------
    # CALL API
    # ---------------------------------------------

    response = client.post(

        "/ask",

        headers={
            "Authorization":
                "Bearer fake-token"
        },

        json={

            "query":
                "What programming languages does Palak know?",

            "document_id":
                "document-123",

            "conversation_id":
                "conversation-123"
        }
    )


    # ---------------------------------------------
    # RESPONSE
    # ---------------------------------------------

    assert response.status_code == 200

    response_data = response.json()


    assert response_data["answer"] == (
        "Palak knows Python and SQL."
    )


    assert response_data["citations"] == [

        {
            "filename":
                "Palak_Resume.pdf",

            "page":
                1
        }
    ]


    # ---------------------------------------------
    # MESSAGES
    # ---------------------------------------------

    assert len(saved_messages) == 2


    assert saved_messages[0]["role"] == "user"

    assert saved_messages[0]["content"] == (
        "What programming languages does Palak know?"
    )


    assert saved_messages[1]["role"] == "assistant"

    assert saved_messages[1]["content"] == (
        "Palak knows Python and SQL."
    )


    # ---------------------------------------------
    # CITATIONS
    # ---------------------------------------------

    assert len(saved_citations) == 1


    assert saved_citations[0]["message_id"] == (
        "assistant-message-123"
    )


    assert saved_citations[0]["document_id"] == (
        "document-123"
    )


    assert saved_citations[0]["filename"] == (
        "Palak_Resume.pdf"
    )


    assert saved_citations[0]["page"] == 1