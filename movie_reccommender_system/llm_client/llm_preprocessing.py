# llm_preprocessing.py
# ----------------------------
# Preprocessing helpers for LLM pipeline
# Point 1: Canonicalize JSON from query executor
# ----------------------------

# Safely convert values to integer
def to_int(value, default=None):
    """
    Convert a value to int safely.
    Returns `default` if conversion fails.
    """
    # Try to convert to integer
    try:
        return int(value)
    # If value is invalid or None, return default
    except (TypeError, ValueError):
        return default


# Safely convert values to float
def to_float(value, default=None):
    """
    Convert a value to float safely.
    Returns `default` if conversion fails.
    """
    # Try to convert to float
    try:
        return float(value)
    # If value is invalid or None, return default
    except (TypeError, ValueError):
        return default


# Validate input and extract core parts
def validate_input(data):
    """
    Validate that the input is a dictionary with expected keys:
    - intent: str
    - slots: dict
    - results: list
    Returns tuple (intent, slots, results).
    """
    # Raise error if input is not a dict
    if not isinstance(data, dict):
        raise ValueError("Input must be a dictionary with keys: intent, slots, results")

    # Extract intent and clean up whitespace
    intent = data.get("intent", "").strip() if isinstance(data.get("intent"), str) else ""
    # Extract slots dict, fallback to empty dict
    slots = data.get("slots", {}) if isinstance(data.get("slots"), dict) else {}
    # Extract results list, fallback to empty list
    results = data.get("results", []) if isinstance(data.get("results"), list) else []

    # Return validated values
    return intent, slots, results


# Normalize slot values (years, ratings)
def normalize_slots(slots):
    """
    Normalize slot values:
    - Convert year-related fields to int
    - Convert rating-related fields to float
    - Leave others unchanged
    Returns a new cleaned slots dictionary.
    """
    # Create container for cleaned slots
    clean_slots = {}
    # Iterate over all slot keys and values
    for key, value in slots.items():
        # If key is a year field, convert to int
        if key in {"year", "start_year", "end_year"}:
            clean_slots[key] = to_int(value)
        # If key is a rating field, convert to float
        elif key in {"min_rating", "max_rating", "rating"}:
            clean_slots[key] = to_float(value)
        # Otherwise leave the slot as-is
        else:
            clean_slots[key] = value
    # Return cleaned slots
    return clean_slots


# Normalize a single result row
def normalize_result_row(row):
    """
    Normalize one movie result row into a consistent schema:
    {movieId, title, year, avg_rating, num_ratings, genres, similarity?}
    Returns None if row is invalid.
    """
    # Skip invalid rows
    if not isinstance(row, dict):
        return None

    # Extract movie id (accept multiple possible keys)
    movie_id = row.get("movieId") or row.get("movie_id")
    # Extract title
    title = row.get("title")
    # Skip if id or title missing
    if movie_id is None or not isinstance(title, str):
        return None

    # Normalize numeric fields
    year = to_int(row.get("year"))
    avg_rating = to_float(row.get("avg_rating") or row.get("rating") or row.get("avgRating"))
    num_ratings = to_int(row.get("num_ratings") or row.get("ratings_count") or row.get("numRatings"))
    similarity = to_float(row.get("similarity"))

    # Normalize genres into a list
    genres = row.get("genres")
    if isinstance(genres, str):
        # Split by commas or pipes, clean whitespace
        genres_list = [g.strip() for g in genres.replace("|", ",").split(",") if g.strip()]
    elif isinstance(genres, list):
        # Ensure every genre is a clean string
        genres_list = [str(g).strip() for g in genres if str(g).strip()]
    else:
        # Default to empty list if missing
        genres_list = []

    # Build normalized row dictionary
    clean_row = {
        "movieId": str(movie_id),          # always string
        "title": title.strip(),            # remove whitespace
        "year": year,                      # integer or None
        "avg_rating": avg_rating,          # float or None
        "num_ratings": num_ratings,        # integer or None
        "genres": genres_list,             # list of strings
    }

    # Include similarity only if it exists
    if similarity is not None:
        clean_row["similarity"] = similarity

    # Return the cleaned row
    return clean_row


# Deduplicate results by movieId
def dedupe_and_collect(results):
    """
    Deduplicate and normalize all results.
    Removes duplicates by movieId.
    Returns a list of cleaned movie rows.
    """
    # Track seen movie ids
    seen = set()
    # Container for cleaned rows
    clean_rows = []
    # Iterate over raw results
    for row in results:
        clean_row = normalize_result_row(row)
        # Only keep valid and unique rows
        if clean_row and clean_row["movieId"] not in seen:
            seen.add(clean_row["movieId"])
            clean_rows.append(clean_row)
    return clean_rows


# Sort results according to intent and cap the size
def sort_and_cap(intent, results, max_results=10):
    """
    Sort results according to intent rules:
    - TOP_N → rating desc, num_ratings desc, title
    - SIMILAR_MOVIES → similarity desc, rating desc, title
    - RECOMMEND → rating desc, num_ratings desc, title
    - GET_DETAILS → title asc, year asc
    - Default → rating desc, title asc
    Then cap the list to max_results.
    """
    # Intent-specific sorting logic
    if intent == "TOP_N":
        results.sort(key=lambda r: (
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            -(r["num_ratings"] if r["num_ratings"] is not None else -1),
            r["title"]
        ))
    elif intent == "SIMILAR_MOVIES":
        results.sort(key=lambda r: (
            -(r.get("similarity") if r.get("similarity") is not None else float("-inf")),
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            r["title"]
        ))
    elif intent in {"RECOMMEND_BY_FILTER", "RECOMMEND"}:
        results.sort(key=lambda r: (
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            -(r["num_ratings"] if r["num_ratings"] is not None else -1),
            r["title"]
        ))
    elif intent == "GET_DETAILS":
        results.sort(key=lambda r: (r["title"], r["year"] if r["year"] is not None else 0))
    else:
        results.sort(key=lambda r: (
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            r["title"]
        ))

    # Return only up to max_results items
    return results[:max_results if isinstance(max_results, int) and max_results > 0 else 10]


# Canonicalize the query output for LLM
def canonicalize_query_output(data, max_results=10):
    """
    Main entry point for preprocessing step 1:
    - Validate schema {intent, slots, results}
    - Normalize slot values
    - Normalize and deduplicate results
    - Sort and cap results depending on intent
    Returns canonical dict with fixed keys.
    """
    # Validate and extract raw parts
    intent, slots, results = validate_input(data)
    # Normalize slot values
    clean_slots = normalize_slots(slots)
    # Clean and deduplicate results
    clean_results = dedupe_and_collect(results)
    # Sort and cap based on intent
    capped_results = sort_and_cap(intent, clean_results, max_results)

    # Return standardized output
    return {
        "intent": intent,
        "slots": clean_slots,
        "results": capped_results,
    }



if __name__ == "__main__": 
    query_executor = {
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
        },
        {
        "movieId": 1,
        "title": "The Dark Knight", 
        "year": "2008", 
        "avg_rating": "4.7", 
        "num_ratings": "5000", 
        "genres": "Action|Crime|Drama"
        }
    ]
    }

    import json
    response = canonicalize_query_output(data=query_executor, max_results=10)
    print("response: \n", json.dumps(response, indent=4))