import fitz

def extract_text(contents):
    
    pdf = fitz.open(stream=contents, filetype="pdf")

   
    text = {}

    for page in pdf:
        
        page_num = page.number + 1
        
        
        text[page_num] = page.get_text()

    
    pdf.close()

    return text
