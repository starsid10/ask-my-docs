import json
import os
import re
import sys

import requests


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

EVAL_TOKEN = os.getenv("EVAL_TOKEN")

DATASET_PATH = os.path.join(
    os.path.dirname(__file__),
    "eval_dataset.json"
)


# ============================================================
# HELPERS
# ============================================================

def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def load_dataset():

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}"
        )

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ============================================================
# GET CURRENT USER'S DOCUMENT
# ============================================================

def get_current_document(token):

    response = requests.get(
        f"{API_URL}/documents",
        headers=get_headers(token),
        timeout=30
    )

    if response.status_code != 200:

        print(
            "\nFailed to retrieve documents."
        )

        print(
            "Status:",
            response.status_code
        )

        print(
            response.text
        )

        return None

    data = response.json()

    if isinstance(data, list):

        documents = data

    elif (
        isinstance(data, dict)
        and isinstance(
            data.get("documents"),
            list
        )
    ):

        documents = data["documents"]

    elif (
        isinstance(data, dict)
        and isinstance(
            data.get("data"),
            list
        )
    ):

        documents = data["data"]

    else:

        documents = []

    for document in documents:

        filename = (
            document.get("filename")
            or document.get("file_name")
            or document.get("name")
            or ""
        )

        if (
            filename.strip().lower()
            == "sm cv.pdf"
        ):

            document_id = (
                document.get("document_id")
                or document.get("id")
                or document.get("documentId")
            )

            if document_id:

                return {
                    "document_id": str(
                        document_id
                    ),
                    "filename": filename
                }

    print(
        "\nSM cv.pdf was not found "
        "for the current user."
    )

    return None


# ============================================================
# GET EXISTING CONVERSATION
# ============================================================

def get_existing_conversation(token):

    response = requests.get(
        f"{API_URL}/conversations",
        headers=get_headers(token),
        timeout=30
    )

    if response.status_code != 200:

        print(
            "\nFailed to retrieve conversations."
        )

        print(
            "Status:",
            response.status_code
        )

        print(
            response.text
        )

        return None

    data = response.json()

    if isinstance(data, list):

        conversations = data

    elif (
        isinstance(data, dict)
        and isinstance(
            data.get("conversations"),
            list
        )
    ):

        conversations = data[
            "conversations"
        ]

    elif (
        isinstance(data, dict)
        and isinstance(
            data.get("data"),
            list
        )
    ):

        conversations = data[
            "data"
        ]

    else:

        conversations = []

    if not conversations:

        print(
            "\nNo existing conversation was found."
        )

        print(
            "Open the application and ask "
            "one question first."
        )

        return None

    # Use the newest conversation.
    conversation = conversations[0]

    conversation_id = (
        conversation.get(
            "conversation_id"
        )
        or conversation.get("id")
    )

    if not conversation_id:

        print(
            "\nConversation exists but "
            "has no conversation_id."
        )

        return None

    return str(
        conversation_id
    )


# ============================================================
# ASK QUESTION
# ============================================================

def ask_question(
    token,
    question,
    document_id,
    conversation_id
):

    payload = {
        "query": question,
        "document_id": document_id,
        "conversation_id": conversation_id
    }

    response = requests.post(
        f"{API_URL}/ask",
        headers=get_headers(token),
        json=payload,
        timeout=120
    )

    return response


# ============================================================
# EXTRACT ANSWER
# ============================================================

def get_answer(response_data):

    if not isinstance(
        response_data,
        dict
    ):
        return ""

    return (
        response_data.get("answer")
        or response_data.get("response")
        or response_data.get("message")
        or ""
    )


# ============================================================
# EXTRACT CITATIONS
# ============================================================

def get_citations(response_data):

    if not isinstance(
        response_data,
        dict
    ):
        return []

    citations = response_data.get(
        "citations",
        []
    )

    if not isinstance(
        citations,
        list
    ):
        return []

    return citations


# ============================================================
# ABSTENTION
# ============================================================

def is_abstention(answer):

    normalized = normalize_text(
        answer
    )

    abstention_phrases = [

        "i don't have enough information",

        "i do not have enough information",

        "not enough information",

        "information is not available",

        "information is not present",

        "cannot find the answer",

        "can't find the answer",

        "cannot answer",

        "can't answer",

        "not provided in the document",

        "not mentioned in the document",

        "not available in the document"
    ]

    return any(
        phrase in normalized
        for phrase in abstention_phrases
    )


# ============================================================
# ANSWER EVALUATION
# ============================================================

def evaluate_answer(
    answer,
    expected_answer,
    expected_keywords
):

    normalized_answer = normalize_text(
        answer
    )

    normalized_expected = normalize_text(
        expected_answer
    )

    # --------------------------------------------------------
    # Unanswerable question
    # --------------------------------------------------------

    if is_abstention(
        expected_answer
    ):

        passed = is_abstention(
            answer
        )

        return {
            "passed": passed,
            "answer_correct": passed,
            "hallucination": not passed
        }

    # --------------------------------------------------------
    # Expected answer
    # --------------------------------------------------------

    expected_text_match = (
        normalized_expected
        in normalized_answer
        if normalized_expected
        else False
    )

    keyword_matches = []

    for keyword in expected_keywords:

        normalized_keyword = normalize_text(
            keyword
        )

        if (
            normalized_keyword
            and normalized_keyword
            in normalized_answer
        ):

            keyword_matches.append(
                keyword
            )

    answer_correct = (
        expected_text_match
        or len(keyword_matches) > 0
    )

    return {
        "passed": answer_correct,
        "answer_correct": answer_correct,
        "hallucination": False,
        "keyword_matches": keyword_matches
    }


# ============================================================
# CITATION EVALUATION
# ============================================================

def citation_matches(
    citation,
    expected_document,
    expected_page
):

    if not isinstance(
        citation,
        dict
    ):
        return False

    filename = (
        citation.get("filename")
        or citation.get("file_name")
        or citation.get("document")
        or citation.get("source")
        or ""
    )

    page = (
        citation.get("page")
        or citation.get("page_number")
        or citation.get("pageNumber")
    )

    filename_match = True

    if expected_document:

        filename_match = (
            expected_document.lower()
            in str(filename).lower()
            or
            str(filename).lower()
            in expected_document.lower()
        )

    page_match = True

    if expected_page is not None:

        try:

            page_match = (
                int(page)
                == int(expected_page)
            )

        except (
            TypeError,
            ValueError
        ):

            page_match = False

    return (
        filename_match
        and page_match
    )


# ============================================================
# MAIN
# ============================================================

def evaluate():

    print(
        "\n=========================================="
    )

    print(
        "ASK MY DOCS - RAG EVALUATION"
    )

    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # Token
    # --------------------------------------------------------

    if not EVAL_TOKEN:

        print(
            "\nEVAL_TOKEN is missing."
        )

        print(
            'Set it with:'
        )

        print(
            '$env:EVAL_TOKEN="YOUR_TOKEN"'
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Dataset
    # --------------------------------------------------------

    try:

        dataset = load_dataset()

    except Exception as error:

        print(
            "\nFailed to load dataset:"
        )

        print(
            error
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Document
    # --------------------------------------------------------

    document = get_current_document(
        EVAL_TOKEN
    )

    if not document:

        sys.exit(1)

    document_id = document[
        "document_id"
    ]

    print(
        "\nEvaluation document:",
        document["filename"]
    )

    print(
        "Document ID:",
        document_id
    )

    # --------------------------------------------------------
    # Existing conversation
    # --------------------------------------------------------

    conversation_id = (
        get_existing_conversation(
            EVAL_TOKEN
        )
    )

    if not conversation_id:

        sys.exit(1)

    print(
        "Conversation ID:",
        conversation_id
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    total_questions = 0

    successful_requests = 0

    answer_correct_count = 0

    citation_correct_count = 0

    hallucination_count = 0

    answerable_questions = 0

    unanswerable_questions = 0

    citation_questions = 0

    # ========================================================
    # QUESTIONS
    # ========================================================

    for index, item in enumerate(
        dataset,
        start=1
    ):

        question = item[
            "question"
        ]

        expected_answer = item.get(
            "expected_answer",
            ""
        )

        expected_page = item.get(
            "expected_page"
        )

        expected_document = item.get(
            "document",
            "SM cv.pdf"
        )

        expected_keywords = item.get(
            "expected_keywords",
            []
        )

        total_questions += 1

        print(
            "\n------------------------------------------"
        )

        print(
            f"Question {index}: {question}"
        )

        # ----------------------------------------------------
        # API
        # ----------------------------------------------------

        try:

            response = ask_question(
                EVAL_TOKEN,
                question,
                document_id,
                conversation_id
            )

        except Exception as error:

            print(
                "\nRequest failed:"
            )

            print(
                error
            )

            continue

        # ----------------------------------------------------
        # HTTP status
        # ----------------------------------------------------

        if response.status_code != 200:

            print(
                "\nRequest failed:",
                response.status_code
            )

            print(
                response.text
            )

            continue

        successful_requests += 1

        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        try:

            response_data = response.json()

        except Exception:

            print(
                "\nInvalid JSON response."
            )

            print(
                response.text
            )

            continue

        # ----------------------------------------------------
        # Answer
        # ----------------------------------------------------

        answer = get_answer(
            response_data
        )

        citations = get_citations(
            response_data
        )

        print(
            "\nAnswer:"
        )

        print(
            answer
        )

        # ----------------------------------------------------
        # Answer evaluation
        # ----------------------------------------------------

        answer_result = evaluate_answer(
            answer,
            expected_answer,
            expected_keywords
        )

        answer_correct = answer_result[
            "answer_correct"
        ]

        hallucination = answer_result[
            "hallucination"
        ]

        if expected_page is None:

            unanswerable_questions += 1

        else:

            answerable_questions += 1

            if answer_correct:
                answer_correct_count += 1

        if hallucination:

            hallucination_count += 1

        # ----------------------------------------------------
        # Citation evaluation
        # ----------------------------------------------------

        citation_correct = False

        if expected_page is not None:

            citation_questions += 1

            for citation in citations:

                if citation_matches(
                    citation,
                    expected_document,
                    expected_page
                ):

                    citation_correct = True

                    break

            if citation_correct:

                citation_correct_count += 1

        else:

            # Unanswerable questions should not
            # receive a source citation.

            citation_correct = (
                len(citations) == 0
            )

        print(
            "\nCitations:"
        )

        print(
            citations
        )

        print(
            "\nAnswer correct:",
            answer_correct
        )

        print(
            "Citation correct:",
            citation_correct
        )

        print(
            "Hallucination:",
            hallucination
        )

    # ========================================================
    # RESULTS
    # ========================================================

    print(
        "\n=========================================="
    )

    print(
        "EVALUATION RESULTS"
    )

    print(
        "=========================================="
    )

    print(
        "Total questions:",
        total_questions
    )

    print(
        "Successful API requests:",
        successful_requests
    )

    if answerable_questions > 0:

        answer_accuracy = (
            answer_correct_count
            / answerable_questions
            * 100
        )

        print(
            f"Answer correctness: "
            f"{answer_accuracy:.2f}%"
        )

    else:

        answer_accuracy = 0

        print(
            "Answer correctness: N/A"
        )

    if citation_questions > 0:

        citation_accuracy = (
            citation_correct_count
            / citation_questions
            * 100
        )

        print(
            f"Citation accuracy: "
            f"{citation_accuracy:.2f}%"
        )

    else:

        citation_accuracy = 0

        print(
            "Citation accuracy: N/A"
        )

    print(
        "Hallucinations:",
        hallucination_count
    )

    if total_questions > 0:

        api_success_rate = (
            successful_requests
            / total_questions
            * 100
        )

    else:

        api_success_rate = 0

    print(
        f"API success rate: "
        f"{api_success_rate:.2f}%"
    )

    print(
        "\n=========================================="
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    results_path = os.path.join(
        os.path.dirname(__file__),
        "evaluation_results.json"
    )

    results = {
        "total_questions": total_questions,
        "successful_api_requests": successful_requests,
        "answerable_questions": answerable_questions,
        "unanswerable_questions": unanswerable_questions,
        "answer_correct": answer_correct_count,
        "citation_correct": citation_correct_count,
        "hallucinations": hallucination_count,
        "answer_accuracy": round(
            answer_accuracy,
            2
        ),
        "citation_accuracy": round(
            citation_accuracy,
            2
        ),
        "api_success_rate": round(
            api_success_rate,
            2
        )
    }

    with open(
        results_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )

    print(
        "Results saved to:"
    )

    print(
        results_path
    )

    print(
        "=========================================="
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    evaluate()