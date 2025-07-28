# rank_sections.py
from vector_database import VectorDatabase
import re

def meaningful_title(section):
    """
    Generates a meaningful, concise (5-25 words) title for a section.
    Prioritizes the section's 'title' field if it strongly resembles a clean heading.
    Falls back to the first few coherent sentences from content if a good title isn't found.
    Ensures no fragmented or irrelevant titles.
    """
    extracted_title = section.get("title", "").strip()
    content_text = section["content"].strip()

    # Criteria for a good title from the 'title' field
    if (5 < len(extracted_title.split()) < 25 and # Reasonable word count for a title
        re.match(r"^(?:[A-Z][a-z0-9\s,&'\(\)\/_-]*|[A-Z][A-Z\s]*)$", extracted_title) and # Capitalization pattern (Title Case or ALL CAPS)
        not extracted_title.endswith(('.', '!', '?')) # Not ending with sentence punctuation
        ):
        return extracted_title
    
    # Fallback 1: Try to form a title from the first 1-3 sentences of the content
    sentences = re.findall(r'[^.!?]*[.!?]', content_text)
    
    candidate_from_content = ""
    for s in sentences:
        # Build a title up to ~25 words or max 100 characters, prioritize ending a sentence
        if len((candidate_from_content + s).split()) < 25 and len(candidate_from_content + s) < 100:
            candidate_from_content += s.strip() + " "
        else:
            break
    
    candidate_from_content = candidate_from_content.strip()
    # Check if the generated content-based title is substantial and clean
    if (5 < len(candidate_from_content.split()) < 25 and # Word count check
        re.search(r"[a-zA-Z]{3,}", candidate_from_content) and # Contains meaningful words
        candidate_from_content[0].isupper() and # Starts with capital
        candidate_from_content.endswith(('.', '!', '?')) # Ends like a complete sentence
        ):
        return candidate_from_content

    # Final fallback: Clean, truncated snippet of the first significant paragraph or a generic title.
    fallback_snippet = content_text.split('\n\n')[0].strip() # Take the first full paragraph as snippet
    if len(fallback_snippet) > 100:
        fallback_snippet = fallback_snippet[:100].rsplit(' ', 1)[0] + "..." # Truncate gracefully to last full word
    
    # If fallback snippet is still bad (too short, or looks like a fragment), use a truly generic title.
    if not re.search(r"[a-zA-Z]{3,}", fallback_snippet) or len(fallback_snippet.split()) < 5 or fallback_snippet.endswith(('.', '!', '?')):
        return f"Information from Page {section['page_number']} of {section['document'].replace('.pdf','')}"

    return fallback_snippet


def rank_sections(sections, persona, job, max_sections_to_extract=10): # Added max_sections_to_extract parameter
    # Compose a query that *aggressively focuses* on actionable planning for the given job.
    # This query must be general enough to work across diverse PDF types,
    # and emphasize "actionable information" directly from the persona's need.
    query = (
        f"As a {persona.strip()}, I need to {job.strip()}. "
        "Provide concrete, actionable information and key recommendations. "
        "Focus on essential details, steps, or insights relevant to completing this task."
    )

    db = VectorDatabase()
    # Filter sections before adding to DB: only substantial content to avoid embedding noise
    filtered_sections = [s for s in sections if len(s["content"].strip()) > 150]
    if not filtered_sections:
        return [], [] # Return empty if no meaningful sections found

    db.add_chunks(filtered_sections)

    # Get a very large pool of top candidates (e.g., top 100-150) to ensure the strict thematic selection has ample options.
    results = db.search(query, top_k=100) # Increased top_k for more options

    # Helper: classify sections by theme. Make categories distinct and broadly applicable.
    # Added more keywords to capture various facets across different documents.
    def classify(section):
        title_and_content = (section.get("title", "") + " " + section["content"]).lower()
        
        # Match against general categories
        for category, keywords in GENERAL_CATEGORIES_KEYWORDS.items():
            if any(keyword in title_and_content for keyword in keywords):
                return category
        
        # Fallback for themes specific to 'Travel Planner' (if persona is explicitly 'Travel Planner')
        # This makes it adaptable: if the persona is travel planner, these keywords apply.
        # Otherwise, the general categories above will be used.
        if "travel planner" in persona.lower():
            if "city" in title_and_content or "destination" in title_and_content or "town" in title_and_content or "regions" in title_and_content:
                return "travel_cities"
            if "activity" in title_and_content or "entertainment" in title_and_content or "nightlife" in title_and_content or "attraction" in title_and_content or "excursion" in title_and_content:
                return "travel_activities"
            if "cuisine" in title_and_content or "food" in title_and_content or "restaurant" in title_and_content or "dining" in title_and_content:
                return "travel_food"
            if "hotel" in title_and_content or "accommodation" in title_and_content or "stay" in title_and_content:
                return "travel_accommodation"
            if "tip" in title_and_content or "packing" in title_and_content or "safety" in title_and_content or "transport" in title_and_content:
                return "travel_tips_practical"
        
        return "other_general" # Default if no specific category match

    chosen = []
    # Use a set of (document, page_number, content_hash) for robust uniqueness checks
    chosen_section_identifiers = set() 

    # Define a set of broad, general categories that can apply to many domains.
    # The 'classify' function will try to match sections to these.
    GENERAL_CATEGORIES_KEYWORDS = {
        "introduction_overview": ["introduction", "overview", "abstract", "summary", "purpose", "scope", "background", "context"],
        "key_concepts_definitions": ["define", "concept", "definition", "key terms", "principles", "fundamentals"],
        "methods_procedures_steps": ["how to", "method", "steps", "procedure", "process", "approach", "guidelines", "instructions", "guide", "implementation"],
        "results_findings_data": ["results", "findings", "data", "analysis", "outcome", "statistics", "performance"],
        "recommendations_solutions": ["recommendation", "solution", "advice", "suggestion", "best practices", "tips", "strategy", "plan", "roadmap"],
        "examples_applications": ["example", "case study", "application", "use case", "scenario", "demonstration"],
        "conclusion_summary": ["conclusion", "summary", "final thoughts", "in brief", "key takeaways", "outlook"],
        "contact_information": ["contact", "address", "phone", "email", "website", "support"],
        "appendix_references": ["appendix", "references", "bibliography", "glossary", "index"]
    }

    # Define a default strict priority order for general actionable information.
    # This ensures that key actionable items are always prioritized.
    # For a *specific persona*, this can be overridden or dynamically weighted.
    DEFAULT_STRICT_PRIORITY_THEMES = [
        "methods_procedures_steps",
        "recommendations_solutions",
        "results_findings_data",
        "key_concepts_definitions",
        "examples_applications",
        "introduction_overview",
        "conclusion_summary",
        "travel_cities",           # Specific to Travel Planner, used if matched by classify
        "travel_activities",       # Specific to Travel Planner
        "travel_food",             # Specific to Travel Planner
        "travel_accommodation",    # Specific to Travel Planner
        "travel_tips_practical",   # Specific to Travel Planner
        "supplemental_info",
        "other_general"
    ]

    # Adjust priority for 'Travel Planner' specifically, placing core travel elements higher.
    # This section makes the prioritization dynamic based on the persona.
    current_priority_themes = list(DEFAULT_STRICT_PRIORITY_THEMES)
    if "travel planner" in persona.lower():
        # Move travel-specific categories to the top if the persona is a travel planner
        travel_priorities = ["travel_cities", "travel_activities", "travel_food", "travel_accommodation"]
        for theme in reversed(travel_priorities): # Insert at beginning
            if theme in current_priority_themes:
                current_priority_themes.remove(theme)
                current_priority_themes.insert(0, theme)
        # Ensure practical tips are after core planning, but before general info
        if "travel_tips_practical" in current_priority_themes:
            current_priority_themes.remove("travel_tips_practical")
            # Find insertion point after accommodation or food if they exist
            idx_after_core = -1
            for core_theme in ["travel_accommodation", "travel_food", "travel_activities", "travel_cities"]:
                if core_theme in current_priority_themes:
                    idx_after_core = max(idx_after_core, current_priority_themes.index(core_theme))
            current_priority_themes.insert(idx_after_core + 1, "travel_tips_practical")
    
    # Pass 1: Select the highest-scoring UNIQUE section for EACH critical theme, in order.
    # This loop enforces the desired diversity and relevance.
    for theme_priority in current_priority_themes:
        if len(chosen) >= max_sections_to_extract: # Use max_sections_to_extract here
            break
        
        best_sec_for_theme = None
        best_score_for_theme = -1
        
        for sec_data, score in results:
            sec_identifier = (sec_data["document"], sec_data["page_number"], hash(sec_data["content"]))
            
            if sec_identifier not in chosen_section_identifiers: # Must be unique and not yet chosen
                if classify(sec_data) == theme_priority:
                    # Prefer higher score, if scores are equal, prefer different document (if applicable)
                    if best_sec_for_theme is None or \
                       score > best_score_for_theme or \
                       (score == best_score_for_theme and best_sec_for_theme[0]["document"] != sec_data["document"]):
                        best_score_for_theme = score
                        best_sec_for_theme = (sec_data, score)
        
        if best_sec_for_theme:
            chosen.append(best_sec_for_theme)
            chosen_section_identifiers.add(sec_identifier) # Add identifier after selection


    # Pass 2: If less than max_sections_to_extract are chosen after strict thematic prioritization,
    # fill remaining slots with the next best unique sections from the overall results,
    # prioritizing high scores, regardless of theme, but avoiding exact duplicates.
    if len(chosen) < max_sections_to_extract: # Use max_sections_to_extract here
        results_sorted_by_score = sorted(results, key=lambda x: -x[1])
        for sec_data, score in results_sorted_by_score:
            if len(chosen) >= max_sections_to_extract: # Use max_sections_to_extract here
                break
            
            sec_identifier = (sec_data["document"], sec_data["page_number"], hash(sec_data["content"]))
            if sec_identifier not in chosen_section_identifiers: # Ensure it's not already picked
                chosen.append((sec_data, score))
                chosen_section_identifiers.add(sec_identifier)

    # Final sort by importance (score) for the output ranking
    chosen = sorted(chosen, key=lambda x: -x[1])

    extracted = []
    detailed = []
    for rank, (sec, score) in enumerate(chosen, start=1):
        refined_text_content = sec["content"].strip()
        
        # Make refined_text highly concise (target 150-250 characters), prioritizing key sentences/paragraphs.
        # This is a heuristic summary, not an extractive or abstractive summary.
        paragraphs = refined_text_content.split('\n\n')
        concise_text_parts = []
        current_len = 0
        target_len = 220 # Aim for around 220 characters

        for para in paragraphs:
            para = para.strip()
            if para:
                # If adding full paragraph fits or is the first part, add it
                if current_len + len(para) <= target_len or not concise_text_parts:
                    concise_text_parts.append(para)
                    current_len += len(para) + 2 # +2 for newline
                else:
                    # If full paragraph is too long, try adding first sentence(s)
                    sentences = re.findall(r'[^.!?]*[.!?]', para)
                    temp_sentence_summary = ""
                    for s in sentences:
                        if current_len + len(temp_sentence_summary) + len(s) <= target_len:
                            temp_sentence_summary += s.strip() + " "
                        else:
                            break
                    if temp_sentence_summary:
                        concise_text_parts.append(temp_sentence_summary.strip())
                    elif current_len < target_len: # If still space, just take a clean snippet
                        remaining_space = target_len - current_len
                        snippet = para[:remaining_space].strip()
                        if len(snippet.split()) > 3: # Ensure snippet is not too small
                           concise_text_parts.append(snippet + "...")
                    break # Stop adding if limit reached or appropriate snippet taken
        
        final_refined_text = "\n\n".join(concise_text_parts).strip()
        # Remove all remaining newlines before final output, replacing with space for JSON formatting
        final_refined_text = final_refined_text.replace('\n', ' ')

        # Fallback if no content or too fragmented to meet criteria for a clean summary
        if not final_refined_text and refined_text_content:
             final_refined_text = refined_text_content[:target_len].strip() # Take raw snippet
             if len(refined_text_content) > target_len and not final_refined_text.endswith(('.', '!', '?')):
                 final_refined_text += "..."
             final_refined_text = final_refined_text.replace('\n', ' ') # Ensure no newlines
        elif not final_refined_text: # If still empty, indicate N/A
            final_refined_text = "N/A"

        extracted.append({
            "document": sec["document"],
            "section_title": meaningful_title(sec),
            "importance_rank": rank,
            "page_number": sec["page_number"]
        })
        detailed.append({
            "document": sec["document"],
            "refined_text": final_refined_text,
            "page_number": sec["page_number"]
        })
    return extracted, detailed