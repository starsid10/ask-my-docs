from sentence_transformers import CrossEncoder
from vector_store import chroma_client
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query, candidates):
    pairs=[]
    candidate_data = []
    collection = chroma_client.get_collection(name="documents")
    

    for candidate in candidates:
        chunk_id, rrf_score = candidate
        result=collection.get(ids=[chunk_id])
        chunk_text = result["documents"][0]
        metadata = result["metadatas"][0]
        pairs.append([query, chunk_text])

        candidate_data.append({
            "chunk_id": chunk_id,
            "text": chunk_text,
            "metadata": metadata,
            "rrf_score": rrf_score})

    scores = reranker.predict(pairs)

   
    for candidate, score in zip(candidate_data, scores):
        candidate["cross_encoder_score"] = score
    
    
    ranked_candidates = sorted(
        candidate_data,
        key=lambda item: item["cross_encoder_score"],
        reverse=True 
        )

    return ranked_candidates    