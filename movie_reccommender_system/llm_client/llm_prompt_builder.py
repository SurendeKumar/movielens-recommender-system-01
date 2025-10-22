# llm_prompt_builder.py
# ----------------------------------------
# Template prompt builder for Part 3 (LLM integration)
# Uses the compact context (Point 2) + cleaned results (Point 1)
# Produces a single prompt string for a text-generation model (e.g., Llama3)
# ----------------------------------------

def make_facts_lines(results, max_items=10):
    """
    Build deterministic, compact fact lines from cleaned results.

    Args:
        results (list[dict]): List of movie rows from canonicalize_query_output().
        max_items (int): Maximum number of lines to include.

    Returns:
        list[str]: Bullet-point lines, each with title, year, rating, ratings count, and genres.
    """
    # Create a list to collect formatted lines
    lines = []
    # Keep a simple counter to enforce the limit
    count = 0
    # Loop through result rows in order (already sorted upstream)
    for row in results:
        # Stop if we already reached the limit
        if count >= max_items:
            break
        # Read title safely
        title = row.get("title") or ""
        # Read year safely
        year = row.get("year")
        # Read average rating safely
        avg_rating = row.get("avg_rating")
        # Read ratings count safely
        num_ratings = row.get("num_ratings")
        # Read genres safely and join them into a short string
        genres_list = row.get("genres") or []
        # Join genres with comma for readability
        genres_text = ", ".join(genres_list) if genres_list else ""
        # Format rating text with one decimal when available
        rating_text = f"{avg_rating:.1f}/5" if isinstance(avg_rating, (int, float)) else "rating n/a"
        # Format ratings count text when available
        count_text = f"{num_ratings} ratings" if isinstance(num_ratings, int) else "count n/a"
        # Build the year text part safely
        year_text = f" ({year})" if isinstance(year, int) else ""
        # Build the genres text part safely
        genres_bracket = f" — [{genres_text}]" if genres_text else ""
        # Compose one bullet line deterministically
        line = f"• {title}{year_text} — {rating_text} — {count_text}{genres_bracket}"
        # Append the line to the list
        lines.append(line)
        # Increase the counter
        count += 1
    # Return all collected lines
    return lines


def build_llm_prompt(context, results, tone="concise", max_items=10):
    """
    Construct a single prompt string for a text-generation LLM.

    Args:
        context (dict): Output of extract_compact_context(), contains:
                        {result_count, seed_title, filters_text, time_window, rating_bounds, (optional) titles}
        results (list[dict]): Cleaned and sorted movie rows from canonicalize_query_output().
        tone (str): Desired response style hint (e.g., "concise", "friendly", "neutral").
        max_items (int): Maximum number of facts included in the facts block.

    Returns:
        str: Prompt text ready to pass to a HF text-generation pipeline.
    """
    # Read the number of results from the context
    result_count = context.get("result_count", 0)
    # Read the compact filters text for quick query summary
    filters_text = context.get("filters_text")
    # Read the human-readable time window text
    time_window_text = context.get("time_window")
    # Read the human-readable rating bounds text
    rating_bounds_text = context.get("rating_bounds")
    # Read the optional titles list for quick mention
    titles_list = context.get("titles", [])

    # Start building a list of prompt sections
    sections = []

    # Add a short system-style instruction to keep the model grounded
    sections.append(
        "You are a helpful movie assistant. "
        "Answer using only the facts provided. Do not invent movies or data."
    )

    # Add a context header line that tells the model what the user asked for
    if filters_text:
        sections.append(f"Context: {filters_text}")
    else:
        # Fallback to explicit pieces if filters_text is missing
        hint_parts = []
        if time_window_text:
            hint_parts.append(time_window_text)
        if rating_bounds_text:
            hint_parts.append(rating_bounds_text)
        hint_text = "; ".join(hint_parts) if hint_parts else "no explicit filters"
        sections.append(f"Context: {hint_text}")

    # Add a brief summary of how many results were found
    sections.append(f"Found: {result_count} result(s).")

    # If we have a titles list, show a quick one-line summary of titles
    if titles_list:
        sections.append("Titles: " + ", ".join(titles_list))

    # Build a facts block from the results so the LLM has structured data to rely on
    fact_lines = make_facts_lines(results, max_items=max_items)
    # Add a header for the facts block
    sections.append("Facts:")
    # Add each fact line as-is to keep formatting deterministic
    sections.extend(fact_lines if fact_lines else ["• No matching items."])

    # Add a direct task instruction that guides tone and length
    sections.append(
        f"Task: Write a short, {tone} response that summarizes these results for the user. "
        "If there are no results, say that politely and suggest broadening the filters."
    )

    # Join all sections with newlines to form one prompt string
    prompt_text = "\n".join(sections)

    # Return the final prompt text
    return prompt_text



if __name__ == "__main__": 

    # test_llm_prompt.py

    from llm_preprocessing import canonicalize_query_output
    from llm_context_builder import extract_compact_context
    from llm_prompt_builder import build_llm_prompt
    import json

    # Step 1: Sample canonical_data input (raw query executor output)
    raw_data = {
        "intent": "TOP_N",
        "slots": {
            "min_rating": "4.0",
            "start_year": "2000",
            "end_year": "2010"
        },
        "results": [
            {
                "movieId": 1,
                "title": "The Dark Knight",
                "year": "2008",
                "avg_rating": "4.7",
                "num_ratings": "5000",
                "genres": "Action|Crime|Drama"
            },
            {
                "movieId": 2,
                "title": "Inception",
                "year": "2010",
                "avg_rating": "4.6",
                "num_ratings": "4500",
                "genres": ["Action", "Sci-Fi", "Thriller"]
            }
        ]
    }

    # Step 2: Canonicalize the raw data (Point 1)
    canonical_data = canonicalize_query_output(raw_data)

    # Step 3: Extract compact context (Point 2)
    context = extract_compact_context(canonical_data)

    # Step 4: Build the LLM prompt (Point 3)
    prompt = build_llm_prompt(context, canonical_data["results"], tone="concise", max_items=5)

    # Print the pieces
    print("=== Canonical Data ===")
    print(json.dumps(canonical_data, indent=4))

    print("\n=== Context ===")
    print(json.dumps(context, indent=4))

    print("\n=== LLM Prompt ===")
    print(prompt)
