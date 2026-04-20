import fitz  # PyMuPDF
import re

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Parses text directly from an uploaded PDF file bytes structure using PyMuPDF,
    without saving it to disk, cleans up excessive whitespace, and handles structural errors.
    """
    text = ""
    try:
        # Open the PDF directly from the byte stream
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
                
        # Ensure proper memory cleanup
        pdf_document.close()
    except Exception as e:
        raise ValueError(f"Failed to read or parse PDF file: {str(e)}")

    if not text.strip():
        raise ValueError("The uploaded PDF appears to be empty or contains unreadable image-based text.")
        
    # Clean up excessive whitespace padding / newlines
    clean_text = re.sub(r'\s+', ' ', text).strip()
    return clean_text
