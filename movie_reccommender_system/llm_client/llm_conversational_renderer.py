# conversational_renderer.py
# -------------------------------------------------------
# Deterministic, rule-based conversational formatter
# Works for common intents: TOP_N, RECOMMEND, RECOMMEND_BY_FILTER,
# GET_DETAILS, SIMILAR_MOVIES, and a generic fallback.
# Comments above every line; simple English variable names.
# -------------------------------------------------------

# Import typing helpers for clarity
from typing import Dict, List, Any, Optional


# Create a helper to format integer counts into friendly short strings
def format_count(count: Optional[int]) -> str:
    """
    Turn an integer count into a short string like '5k', '12k', or '1.2M'.
    """
    # Return "unknown" when count is not an integer
    if not isinstance(count, int):
        return "unknown"
    # Format millions with one decimal when needed
    if count >= 1_000_000:
        # Compute millions with one decimal
        text = f"{count/1_000_000:.1f}M"
        # Strip any trailing .0 for clean output
        return text.rstrip("0").rstrip(".")
    # Format thousands as whole-k (e.g., 5k, 12k)
    if count >= 1000:
        # Divide by 1000 and use integer part
        return f"{count//1000}k"
    # For small numbers, return as-is
    return str(count)



# Create a helper to format a single movie row into a compact phrase
def format_movie_brief(row: Dict[str, Any]) -> str:
    """
    Turn one canonical movie row into a compact phrase:
    "Title (Year, Genres, 4.6★, 2,345 ratings)"
    """
    # Read the title safely
    title = row.get("title") or "Unknown Title"
    # Read the year safely
    year = row.get("year")
    # Read the genres list safely
    genres_list = row.get("genres") or []
    # Join genres with slash for brevity
    genres_text = "/".join(genres_list[:3]) if genres_list else "Genre N/A"
    # Read average rating safely
    avg = row.get("avg_rating")
    # Read ratings count safely
    count = row.get("num_ratings")

    # Build the rating part with a star if available
    rating_part = f"{avg:.1f}★" if isinstance(avg, (int, float)) else "rating N/A"
    # Build the count part with a simple thousands separator
    # count_part = f"{count:,} ratings" if isinstance(count, int) else "count N/A"
    count_part = f"{format_count(count)} ratings" if isinstance(count, int) else "unknown rating count"
    # Start with title
    base = title
    # Add year if present
    if isinstance(year, int):
        base += f" ({year}"
        # Add genres, rating, and count inside the same parentheses
        base += f", {genres_text}, {rating_part}, {count_part})"
    else:
        # If no year, add everything after a dash
        base += f" — {genres_text}, {rating_part}, {count_part}"
    # Return the final compact phrase
    return base




# Create a helper to format a single movie in an even simpler sentence
def format_movie_sentence(row: Dict[str, Any]) -> str:
    """
    Turn one canonical movie row into a short sentence:
    "Title is an Action/Drama movie from 2008 with a 4.7★ rating and 5,000 ratings."
    """
    # Read fields with safe defaults
    title = row.get("title") or "This title"
    year = row.get("year")
    genres_list = row.get("genres") or []
    avg = row.get("avg_rating")
    count = row.get("num_ratings")

    # Build genres text (fallback to 'Unknown genre')
    genres_text = "/".join(genres_list[:3]) if genres_list else "Unknown genre"
    # Build rating text if available
    rating_text = f"{avg:.1f}★" if isinstance(avg, (int, float)) else "an unrated"
    # Build count text with separators if available
    # count_text = f"{count:,} ratings" if isinstance(count, int) else "unknown rating count"
    count_text = f"{format_count(count)} ratings" if isinstance(count, int) else "unknown rating count"

    # Build the core sentence parts
    if isinstance(year, int) and isinstance(avg, (int, float)):
        # Full details case
        return f"{title} is an {genres_text} movie from {year} with a {rating_text} rating and {count_text}."
    if isinstance(year, int):
        # No average rating case
        return f"{title} is an {genres_text} movie from {year} with {count_text}."
    # No year either
    return f"{title} is an {genres_text} movie with a {rating_text} rating and {count_text}."


# Create a helper to join a few items in a human way
def natural_join(items: List[str]) -> str:
    """
    Join 1–3 items naturally: "A", "A and B", "A, B, and C"
    """
    # Handle empty list
    if not items:
        return ""
    # Handle one item
    if len(items) == 1:
        return items[0]
    # Handle two items
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    # Handle three or more (but we usually pass <=3)
    return f"{', '.join(items[:-1])}, and {items[-1]}"



# Create the main function to render a conversational answer for any intent
def render_conversational_answer(intent: str, context: Dict[str, Any], results: List[Dict[str, Any]], max_items: int = 5) -> str:
    """
    Render a short, conversational answer for a given intent and results.
    Supports: TOP_N, RECOMMEND, RECOMMEND_BY_FILTER, GET_DETAILS, SIMILAR_MOVIES.
    Falls back gracefully if intent is unknown or results are empty.
    """
    # Normalize intent to uppercase
    intent_key = (intent or "").upper()
    # Clip results to the requested maximum
    rows = results[:max_items]
    # Build per-movie sentences
    sentences = [format_movie_sentence(r) for r in rows]
    # Extract a human hint from context filters, if present
    hint = context.get("filters_text")

    # Handle GET_DETAILS: usually a single item
    if intent_key == "GET_DETAILS":
        # If we have a row, return a single clean sentence
        if rows:
            return sentences[0]
        # If no row is available, say we could not find details
        return "I could not find details for that title."

    # Handle SIMILAR_MOVIES: mention seed and 2–3 recommendations
    if intent_key == "SIMILAR_MOVIES":
        # Read the seed title from context
        seed = context.get("seed_title")
        # Extract titles from available rows
        title_list = [r.get("title") for r in rows if r.get("title")]
        # If we have titles, produce a short one-liner
        if title_list:
            # Join up to three titles
            joined = natural_join(title_list[:3])
            # If we know the seed, mention it
            if seed:
                return f"If you liked {seed}, you might also enjoy {joined}."
            # If seed is unknown, just present the recommendations
            return f"You might also enjoy {joined}."
        # If no titles available, say none found
        return "I could not find similar movies to recommend."

    # Handle TOP_N / RECOMMEND* intents: quick count + highlights
    if intent_key in {"TOP_N", "RECOMMEND", "RECOMMEND_BY_FILTER"}:
        # If there are no rows, offer a gentle suggestion
        if not rows:
            return "I could not find any matches. Try lowering the rating or widening the year range."
        # Build a short highlights line from the first two rows using the brief formatter
        highlights = natural_join([format_movie_brief(r) for r in rows[:2]])
        # Compute how many more items we have beyond the highlights
        more_count = max(len(rows) - 2, 0)
        # If we have a hint and more items, include both
        if hint and more_count > 0:
            return f"I found {len(rows)} title(s) matching your filters ({hint}): {highlights}, and {more_count} more."
        # If we only have a hint, include it
        if hint:
            return f"I found {len(rows)} title(s) matching your filters ({hint}): {highlights}."
        # If no hint but more items remain, mention the count
        if more_count > 0:
            return f"I found {len(rows)} title(s): {highlights}, and {more_count} more."
        # Otherwise report what we have
        return f"I found {len(rows)} title(s): {highlights}."

    # Fallback for unknown intents with some rows
    if rows:
        # Join the first two titles as a quick answer
        first_two = natural_join([r.get("title") for r in rows[:2] if r.get("title")])
        # If we have a hint, include it
        if hint:
            return f"Here are the matches for your filters ({hint}): {first_two}."
        # Otherwise just present the titles
        return f"Here are the matches: {first_two}."
    # If nothing at all, generic no-result line
    return "No matching movies found."
