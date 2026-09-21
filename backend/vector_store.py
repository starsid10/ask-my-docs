import os
import chromadb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

def store_embeddings(chroma_client, collection_name, chunks):
    
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    
    documents_list = [chunk['text'] for chunk in chunks]
    
   
    metadatas_list = [
        {
            "document_id": str(chunk.get('document_id')),
            "page": chunk.get('page'),
            "filename": chunk.get("filename"),
            "user_id": str(chunk.get("user_id")),
            "chunk_index": i
        } 
        for i, chunk in enumerate(chunks)
    ]
    
   
    ids_list = [f"{chunk.get('document_id')}_{i}" for i, chunk in enumerate(chunks)]
    
   
    embeddings_list = [chunk.get('embedding').tolist()for chunk in chunks]

    print("METADATA:", metadatas_list)
    
   
    collection.add(
        ids=ids_list,
        documents=documents_list,
        embeddings=embeddings_list,
        metadatas=metadatas_list
    )


    

    return len(chunks)