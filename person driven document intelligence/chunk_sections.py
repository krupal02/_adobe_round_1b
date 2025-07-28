# chunk_sections.py
import re

def split_into_sections(pages):
    """
    Splits pages into logical sections by identifying strong headings and grouping
    subsequent coherent paragraphs. Aggressively merges small fragments or
    sections without clear headings.
    """
    sections = []
    
    # Very strict regex for main section titles.
    # - Must be predominantly uppercase or Title Case, relatively short (5-40 chars).
    # - Must NOT end with typical sentence punctuation.
    # - Allows for numbering (e.g., "1. Introduction").
    # This regex is highly tuned to catch actual headings.
    STRICT_HEADING_REGEX = re.compile(
        r"^(?:[A-Z][A-Za-z0-9\s,&'\(\)\/_-]{4,40}|[A-Z][A-Z\s]{4,40}|" # Title Case or ALL CAPS
        r"\d+(?:\.\d+)*\s+[A-Z][A-Za-z0-9\s,&'\(\)\/_-]{4,40})$" # Numbered headings (e.g., "1.2 Section Name")
        r"(?<![\.\?\!])$" # Negative lookbehind: does NOT end with sentence punctuation
    )
    
    # Minimum length for a content block to be considered a valid *new* section.
    # This prevents fragmentation.
    MIN_NEW_SECTION_CONTENT_LENGTH = 200 # characters, for a new section to truly start

    # Minimum length for a section that's added to the final list.
    MIN_FINAL_SECTION_LENGTH = 80 # characters, allows smaller valid sections after merging

    for page in pages:
        # Split page content by double newlines to get potential paragraphs/blocks
        # Filter out empty blocks immediately.
        content_blocks = [block.strip() for block in page["content"].split('\n\n') if block.strip()]
        
        current_section = {
            "title": "",
            "content_blocks": [], # Store blocks, join later
            "page_number": page["page_number"],
            "document": page["document"]
        }
        
        for block_idx, block in enumerate(content_blocks):
            # Check if this block's first line could be a new title
            first_line_of_block = block.split('\n')[0].strip()
            is_potential_title = bool(STRICT_HEADING_REGEX.fullmatch(first_line_of_block))
            
            # Heuristic: if a "potential title" is actually just a very long sentence, it's not a title
            if is_potential_title and len(first_line_of_block.split()) > 10:
                is_potential_title = False

            if is_potential_title:
                # Before starting a new section, check if the current one has *substantial* content.
                combined_content_len = len(" ".join(current_section["content_blocks"]).strip())
                if combined_content_len >= MIN_NEW_SECTION_CONTENT_LENGTH:
                    # Finalize previous section if it's substantial
                    sections.append({
                        "title": current_section["title"],
                        "content": " ".join(current_section["content_blocks"]).strip(),
                        "page_number": current_section["page_number"],
                        "document": current_section["document"]
                    })
                    
                    # Start a new section with the detected title
                    current_section = {
                        "title": first_line_of_block,
                        "content_blocks": [block], # Include the rest of the block content as part of new section
                        "page_number": page["page_number"],
                        "document": page["document"]
                    }
                else:
                    # If existing content is not substantial enough for a new section,
                    # absorb this "title" into the current section's content.
                    # Or, if current section is truly empty (first section of page, first block), use it as title.
                    if not current_section["title"] and not current_section["content_blocks"]:
                        current_section["title"] = first_line_of_block
                        current_section["content_blocks"].append(block) # The rest of the block is content
                    else:
                        current_section["content_blocks"].append(block) # Treat as continuation of content
            else:
                # This block is not a strong title, so it's content.
                current_section["content_blocks"].append(block)

        # After processing all blocks on a page, handle the last current_section.
        final_section_content = " ".join(current_section["content_blocks"]).strip()
        
        if final_section_content:
            # If the last section is too short, try to merge it with the *last added* section
            # to prevent small fragmented sections at the end of a page/document.
            if len(final_section_content) < MIN_FINAL_SECTION_LENGTH and sections:
                # Only merge if the last section isn't already too large (e.g., >1000 chars)
                if len(sections[-1]["content"]) < 1000:
                    sections[-1]["content"] += "\n\n" + final_section_content
                else: # If previous is too large, add this short one as a separate entry
                    sections.append({
                        "title": current_section["title"], # Might be empty
                        "content": final_section_content,
                        "page_number": current_section["page_number"],
                        "document": current_section["document"]
                    })
            else:
                # Add if it meets minimum length, or if it's the very first section found.
                if final_section_content and (len(final_section_content) >= MIN_FINAL_SECTION_LENGTH or not sections):
                    sections.append({
                        "title": current_section["title"],
                        "content": final_section_content,
                        "page_number": current_section["page_number"],
                        "document": current_section["document"]
                    })
    return sections