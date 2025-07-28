# extract_text.py
import fitz # PyMuPDF
import os
import re

def clean_text_content(text):
    """
    Cleans and standardizes text extracted from PDF pages.
    Removes common page artifacts, headers/footers, and excessive whitespace.
    This version focuses on essential cleaning without advanced layout analysis.
    """
    # 1. Remove common page number patterns (isolated numbers, or at line end)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE) # e.g., "   5   " on its own line
    text = re.sub(r'\s+\d+\s*\n', '\n', text) # e.g., "text on line 5\n"
    text = re.sub(r'\n\s*\d+\s*$', '', text) # Page number at very end of page content

    # 2. Replace multiple newlines with at most two (to distinguish paragraph breaks from simple line breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 3. Replace multiple spaces/tabs with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 4. Strip leading/trailing whitespace from each line
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines]
    
    # 5. Join lines back, preserving original line breaks for paragraph distinction by \n\n later
    text = '\n'.join(cleaned_lines)
    
    # 6. Remove non-ASCII characters that often appear as garbage from PDF extraction (e.g., ligatures not converted well)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    
    return text.strip()

def extract_text_from_pdf(folder_path):
    """
    Extracts and preprocesses text from PDF files in a given folder.
    """
    documents = []
    if not os.path.exists(folder_path):
        print(f"Error: Input folder '{folder_path}' does not exist.")
        return documents

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(folder_path, filename)
        pdf = fitz.open(pdf_path)
        print(f"Extracting from: {filename}")
        for i, page in enumerate(pdf):
            text = page.get_text("text")
            if text.strip():
                cleaned_text = clean_text_content(text) # Apply cleaning
                if cleaned_text: # Only add if cleaned text is not empty
                    documents.append({
                        "document": filename,
                        "page_number": i + 1,
                        "content": cleaned_text
                    })
        pdf.close()
    return documents