def store_chunks(supabase_client, chunks):
    rows = []

    for chunk_index, chunk in enumerate(chunks):
        row = {
            "chunk_index": chunk_index,
            "document_id": str(chunk["document_id"]),
            "page": chunk["page"],
            "text": chunk["text"]
        }

        rows.append(row)

    response = (
        supabase_client
        .table("document_chunks")
        .insert(rows)
        .execute()
    )

    return response