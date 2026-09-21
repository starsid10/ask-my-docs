import json
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

from retrieval import retrieve


DOCUMENT_ID = os.getenv("EVAL_DOCUMENT_ID")
USER_ID = os.getenv("EVAL_USER_ID")


def load_dataset():
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "eval_dataset.json"
        ),
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def normalize_text(text):
    return str(text).lower().strip()


def evaluate_retrieval():

    dataset = load_dataset()

    if not DOCUMENT_ID:
        raise ValueError(
            "EVAL_DOCUMENT_ID environment variable is missing."
        )

    if not USER_ID:
        raise ValueError(
            "EVAL_USER_ID environment variable is missing."
        )

    total_questions = 0
    successful_retrievals = 0

    print("\n==============================")
    print("RETRIEVAL EVALUATION")
    print("==============================")

    for item in dataset:

        # Skip unanswerable questions
        if item["expected_page"] is None:
            continue

        total_questions += 1

        retrieved_chunks = retrieve(
            item["question"],
            USER_ID,
            DOCUMENT_ID
        )

        retrieved_pages = []
        retrieved_texts = []

        for chunk in retrieved_chunks:

            metadata = chunk.get("metadata", {})

            page = metadata.get("page")

            if page is not None:
                retrieved_pages.append(page)

            text = chunk.get("text", "")

            if not text:
                text = metadata.get("text", "")

            retrieved_texts.append(
                normalize_text(text)
            )

        # Combine retrieved text
        combined_text = " ".join(
            retrieved_texts
        )

        expected_keywords = [
            normalize_text(keyword)
            for keyword in item.get(
                "expected_keywords",
                []
            )
        ]

        # Keyword relevance
        matched_keywords = [
            keyword
            for keyword in expected_keywords
            if keyword in combined_text
        ]

        keyword_hit = (
            len(matched_keywords) > 0
            if expected_keywords
            else False
        )

        # Page relevance
        page_hit = (
            item["expected_page"]
            in retrieved_pages
        )

        # Retrieval succeeds only when
        # both page and relevant content match.
        hit = page_hit and keyword_hit

        if hit:
            successful_retrievals += 1

        print("\nQuestion:", item["question"])

        print(
            "Expected page:",
            item["expected_page"]
        )

        print(
            "Retrieved pages:",
            retrieved_pages
        )

        print(
            "Expected keywords:",
            expected_keywords
        )

        print(
            "Matched keywords:",
            matched_keywords
        )

        print(
            "Page hit:",
            page_hit
        )

        print(
            "Content relevance:",
            keyword_hit
        )

        print(
            "Retrieval Hit@5:",
            hit
        )

    if total_questions == 0:

        print(
            "\nNo retrieval questions available."
        )

        return

    retrieval_accuracy = (
        successful_retrievals
        / total_questions
        * 100
    )

    print("\n==============================")
    print("RETRIEVAL RESULTS")
    print("==============================")

    print(
        f"Total answerable questions: "
        f"{total_questions}"
    )

    print(
        f"Successful retrievals: "
        f"{successful_retrievals}"
    )

    print(
        f"Retrieval Hit@5: "
        f"{retrieval_accuracy:.2f}%"
    )

    print("==============================")


if __name__ == "__main__":
    evaluate_retrieval()