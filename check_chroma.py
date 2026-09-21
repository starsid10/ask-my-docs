import sys
import os

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "backend"
        )
    )
)

from vector_store import chroma_client


collection = chroma_client.get_collection(
    name="documents"
)

document_id = "2782d4e5-0a51-4ec1-b8a6-ea2b82cc8a5c"
user_id = "c83b00dc-4917-4cad-a1eb-db40615ded93"


print("=== TOTAL CHROMA RECORDS ===")

print(
    "COUNT:",
    collection.count()
)


print("\n=== DOCUMENT ID FILTER ===")

document_result = collection.get(
    where={
        "document_id": document_id
    }
)

print(
    "COUNT:",
    len(document_result["ids"])
)

print(
    "IDS:",
    document_result["ids"]
)


print("\n=== USER ID FILTER ===")

user_result = collection.get(
    where={
        "user_id": user_id
    }
)

print(
    "COUNT:",
    len(user_result["ids"])
)

print(
    "IDS:",
    user_result["ids"]
)

if user_result["metadatas"]:
    print(
        "FIRST USER ID:",
        repr(user_result["metadatas"][0]["user_id"])
    )
else:
    print(
        "FIRST USER ID: NONE"
    )


print("\n=== BOTH FILTERS ===")

both_result = collection.get(
    where={
        "$and": [
            {
                "document_id": document_id
            },
            {
                "user_id": user_id
            }
        ]
    }
)

print(
    "COUNT:",
    len(both_result["ids"])
)

print(
    "IDS:",
    both_result["ids"]
)


print("\n=== ACTUAL DOCUMENT METADATA ===")

if document_result["metadatas"]:

    print(
        "FIRST CHUNK METADATA:"
    )

    print(
        document_result["metadatas"][0]
    )

else:

    print(
        "No metadata found."
    )