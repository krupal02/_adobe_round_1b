# main.py
import os
import json
from datetime import datetime
from extract_text import extract_text_from_pdf
from chunk_sections import split_into_sections
from rank_sections import rank_sections

# Define input and output paths
INPUT_FOLDER = "input_pdfs"
OUTPUT_FILE = "output/output.json"

# Define persona and job-to-be-done based on the challenge brief
persona = "Travel Planner"
job = "Plan a trip of 4 days for a group of 10 college friends."

def run_pipeline():
    """
    Orchestrates the document processing pipeline:
    1. Extracts text from PDFs.
    2. Chunks the text into meaningful sections.
    3. Ranks sections based on persona and job-to-be-done.
    4. Saves the results to a JSON file.
    """
    print(f"Starting document processing pipeline for persona: '{persona}', job: '{job}'")

    # Step 1: Extract text from PDF documents
    print(f"Extracting text from PDFs in '{INPUT_FOLDER}'...")
    pages = extract_text_from_pdf(INPUT_FOLDER)
    if not pages:
        print(f"No PDF documents found or text extracted from '{INPUT_FOLDER}'. Exiting.")
        return
    # Get unique document names for metadata
    input_docs_set = {p["document"] for p in pages}
    print(f"Extracted text from {len(pages)} pages across {len(input_docs_set)} documents.")

    # Step 2: Split extracted pages into logical sections
    print("Splitting extracted text into sections...")
    sections = split_into_sections(pages)
    print(f"Identified {len(sections)} sections.")

    # Step 3: Rank sections based on the persona and job-to-be-done
    # Pass the desired number of sections to extract (e.g., 10 or more)
    desired_output_sections = 10 # You can change this number
    print(f"Ranking sections based on persona and job-to-be-done, aiming for {desired_output_sections} sections...")
    extracted_sections, subsection_analysis = rank_sections(sections, persona, job, max_sections_to_extract=desired_output_sections)
    print(f"Selected {len(extracted_sections)} top relevant sections.")

    # Prepare the final output structure
    result = {
        "metadata": {
            "input_documents": sorted(list(input_docs_set)), # Sorted list of unique document names
            "persona": persona,
            "job_to_be_done": job,
            "processing_timestamp": datetime.utcnow().isoformat()
        },
        "extracted_sections": extracted_sections,
        "subsection_analysis": subsection_analysis
    }

    # Step 4: Write the results to a JSON file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=4)
    print(f"✅ Output written to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_pipeline()