# llm_context_builder.py
# ----------------------------------------
# Point 2: Extract compact context object for LLM
# Builds summary fields from canonicalized data
# ----------------------------------------

# Safely convert a value to string
def to_str_safe(value):
    """
    Convert a value to a stripped string, return None if empty.
    """
    # If input is None, return None
    if value is None:
        return None
    # Convert to string and strip whitespace
    s = str(value).strip()
    # Return None if result is empty
    return s if s else None


# Normalize 'genres' slot values
def normalize_slot_genres(slots):
    """
    Normalize 'genres' or 'genre' from slots into a list of clean strings.
    Supports comma or pipe separated strings, or a list.
    """
    # Read from either "genres" or "genre"
    raw_slot = slots.get("genres", slots.get("genre"))
    # If nothing present, return empty list
    if raw_slot is None:
        return []
    # If string, replace pipes with commas and split
    if isinstance(raw_slot, str):
        parts = raw_slot.replace("|", ",").split(",")
        # Strip whitespace and drop empties
        return [p.strip() for p in parts if p.strip()]
    # If list, convert each to string and strip
    if isinstance(raw_slot, list):
        return [str(p).strip() for p in raw_slot if str(p).strip()]
    # Otherwise return empty list
    return []


# Build time window phrase
def build_time_window(slots):
    """
    Construct a human-readable time window phrase.
    Examples:
      start_year + end_year -> "between 2000 and 2010"
      start_year only -> "since 2000"
      end_year only -> "until 2010"
      year only -> "in 2005"
    """
    # Read slot values
    year = slots.get("year")
    start_year = slots.get("start_year")
    end_year = slots.get("end_year")

    # If both start and end provided
    if start_year is not None and end_year is not None:
        return f"between {start_year} and {end_year}"
    # If only start year provided
    if start_year is not None:
        return f"since {start_year}"
    # If only end year provided
    if end_year is not None:
        return f"until {end_year}"
    # If only year provided
    if year is not None:
        return f"in {year}"
    # If nothing provided
    return None


# Build rating bounds phrase
def build_rating_bounds(slots):
    """
    Construct a human-readable rating constraint phrase.
    Examples:
      min + max -> "between 3.5 and 4.5"
      min only -> "≥ 4.0"
      max only -> "≤ 3.0"
      exact rating -> "= 5.0"
    """
    # Read slot values
    min_rating = slots.get("min_rating")
    max_rating = slots.get("max_rating")
    exact_rating = slots.get("rating")

    # If exact rating provided
    if exact_rating is not None:
        return f"= {round(float(exact_rating), 1)}"
    # If both min and max provided
    if min_rating is not None and max_rating is not None:
        return f"between {round(float(min_rating), 1)} and {round(float(max_rating), 1)}"
    # If only min rating provided
    if min_rating is not None:
        return f"≥ {round(float(min_rating), 1)}"
    # If only max rating provided
    if max_rating is not None:
        return f"≤ {round(float(max_rating), 1)}"
    # Nothing provided
    return None


# Build a combined filters text line
def build_filters_text(intent, slots, time_window_text, rating_text, max_length=140):
    """
    Combine filters into one short text string.
    Order:
      - intent hint
      - genres
      - time window
      - rating bounds
      - seed title
    """
    # Container for text pieces
    parts = []

    # Add intent hint based on type
    if to_str_safe(intent) in {"RECOMMEND_BY_FILTER", "RECOMMEND"}:
        parts.append("recommendations by filters")
    elif to_str_safe(intent) == "TOP_N":
        parts.append("top titles")
    elif to_str_safe(intent) == "SIMILAR_MOVIES":
        parts.append("similar titles")
    elif to_str_safe(intent) == "GET_DETAILS":
        parts.append("title details")

    # Add genres from slots
    genres_list = normalize_slot_genres(slots)
    if genres_list:
        parts.append("genres=" + ", ".join(genres_list))

    # Add time window if present
    if to_str_safe(time_window_text):
        parts.append(time_window_text)

    # Add rating bounds if present
    if to_str_safe(rating_text):
        parts.append(rating_text)

    # Add seed title if present
    seed_title = to_str_safe(slots.get("title"))
    if seed_title:
        parts.append(f'title="{seed_title}"')

    # Join all parts with semicolons
    text = "; ".join(parts)

    # If too long, trim and add ellipsis
    if len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "…"

    # Return final text or None
    return text if text else None


# Extract compact context object
def extract_compact_context(canonical_data, max_filters_length=140):
    """
    Build a compact context object from canonicalized query data.

    Input:
      canonical_data: dict returned by canonicalize_query_output()

    Output:
      dict with keys:
        result_count: int
        seed_title: str|None
        filters_text: str|None
        time_window: str|None
        rating_bounds: str|None
    """
    # Extract intent
    intent = canonical_data.get("intent")
    # Extract slots dictionary
    slots = canonical_data.get("slots", {})
    # Extract results list
    results = canonical_data.get("results", [])

    # Count number of results
    result_count = len(results)

    # Build human time window phrase
    time_window_text = build_time_window(slots)

    # Build human rating bounds phrase
    rating_text = build_rating_bounds(slots)

    # Extract seed title from slots if present
    seed_title = to_str_safe(slots.get("title"))

    # Build combined filters string
    filters_text = build_filters_text(intent, slots, time_window_text, rating_text, max_length=max_filters_length)

    # Collect all movie titles from results
    titles = [r.get("title") for r in results if r.get("title")]

    # Return compact context object
    return {
        "result_count": result_count,
        "seed_title": seed_title,
        "filters_text": filters_text,
        "time_window": time_window_text,
        "rating_bounds": rating_text,
        "titles": titles,
    }


if __name__ == "__main__":
    canonical_data={
            "intent": "TOP_N",
            "slots": {
                "min_rating": 4.0,
                "start_year": 2000,
                "end_year": 2010
            },
            "results": [
                {
                    "movieId": "1",
                    "title": "The Dark Knight",
                    "year": 2008,
                    "avg_rating": 4.7,
                    "num_ratings": 5000,
                    "genres": [
                        "Action",
                        "Crime",
                        "Drama"
                    ]
                },
                {
                    "movieId": "2",
                    "title": "Inception",
                    "year": 2010,
                    "avg_rating": 4.6,
                    "num_ratings": 4500,
                    "genres": [
                        "Action",
                        "Sci-Fi",
                        "Thriller"
                    ]
                }
            ]
        }
    
    import json
    response= extract_compact_context(canonical_data, max_filters_length=140)
    print("response: \n", response)
    # print("response: \n", json.dumps(response, indent=4))
