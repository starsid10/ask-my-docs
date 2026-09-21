from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(extracted_text, document_id):
    all_chunks = []
    
   
    text_splitter = RecursiveCharacterTextSplitter( 
        chunk_size=400,
        chunk_overlap=80
    )

    
    for page_number, page_text in extracted_text.items():
       
        page_chunks = text_splitter.split_text(page_text)
        
        
        for chunk in page_chunks:
            all_chunks.append({
                "document_id": document_id,
                "page": page_number,
                "text": chunk
            })

    return all_chunks
