import fitz
from extraction import extract_text


def create_test_pdf():
    pdf = fitz.open()

    page1 = pdf.new_page()
    page1.insert_text((50, 50), "This is page one.")

    page2 = pdf.new_page()
    page2.insert_text((50, 50), "This is page two.")

    pdf_bytes = pdf.tobytes()
    pdf.close()

    return pdf_bytes


def test_extract_text_returns_page_text():

    pdf_bytes = create_test_pdf()

    extracted_text = extract_text(pdf_bytes)

    assert len(extracted_text) == 2
    assert 1 in extracted_text
    assert 2 in extracted_text


def test_extract_text_preserves_page_content():

    pdf_bytes = create_test_pdf()

    extracted_text = extract_text(pdf_bytes)

    assert "This is page one." in extracted_text[1]
    assert "This is page two." in extracted_text[2]