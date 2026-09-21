from sentence_transformers import SentenceTransformer


model = SentenceTransformer("all-MiniLM-L6-v2")





def create_embeddings(chunks):
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts)

    all_chunks=[]

    for chunk, embedding in zip(chunks, embeddings):
        combined_record = {
        "document_id": chunk["document_id"],
        "page": chunk["page"],
        "filename": chunk["filename"],
        "user_id": chunk["user_id"],
        "text": chunk["text"],
        "embedding": embedding  
    }

        all_chunks.append(combined_record)
    return all_chunks