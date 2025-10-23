""" Script to render the conversation tasks. Best for small text use cases.
Still need to work on it - as this is plan B
"""
import logging
from typing import Dict, List, Any, Optional
# basic log info 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# deifne single logger for context builder
logger=logging.getLogger("LLM_Conversational_Renderer")


# render a conversational answer for any intent
def render_conversational_answer(
        intent: str, 
        context: Dict[str, Any], 
        results: List[Dict[str, Any]], 
        max_items: int = 5) :
    """Function to render a short, conversational answer for a given intent and results.
            Supports: TOP_N, RECOMMEND_BY_FILTER, GET_DETAILS, SIMILAR_MOVIES.
            Falls back gracefully if intent is unknown or results are empty.

    Args:
        intent (str): Incoming intents.
        context (dict): Incoming context after context builder.
        reuslts (list): containing the results after normalised data.
        max_items (int): Default to 5.

    Returns:
        Final conversation response.
    """
    # normalize intent to uppercase
    intent_key = (intent or "").upper()
    # clip results to the requested maximum
    rows = results[:max_items]
    # build per-movie sentences
    logger.info(f"Formatting the movie sentence.")
    sentences = [format_movie_sentence(r) for r in rows]
    # extract a human hint from context filters, if present
    hint = context.get("filters_text")

    # handle GET_DETAILS: usually a single item
    if intent_key == "GET_DETAILS":
        # if we have a row, return a single clean sentence
        if rows:
            return sentences[0]
        # if no row is available, say we could not find details
        return "I could not find details for that title."

    # handle SIMILAR_MOVIES: mention seed and 2–3 recommendations
    if intent_key == "SIMILAR_MOVIES":
        # read the seed title from context
        seed = context.get("seed_title")
        # extract titles from available rows
        title_list = [r.get("title") for r in rows if r.get("title")]
        # if we have titles, produce a short one-liner
        logger.info(f"Joining the title in list..")
        if title_list:
            # join up to three titles
            joined = natural_join(title_list[:3])
            # if we know the seed, mention it
            if seed:
                return f"If you liked {seed}, you might also enjoy {joined}."
            # if seed is unknown, just present the recommendations
            return f"You might also enjoy {joined}."
        # if no titles available, say none found
        return "I could not find similar movies to recommend."

    # handle TOP_N / RECOMMEND* intents: quick count + highlights
    if intent_key in {"TOP_N", "RECOMMEND_BY_FILTER"}:
        # If there are no rows, offer a gentle suggestion
        if not rows:
            return "I could not find any matches. Try lowering the rating or widening the year range."
        # build a short highlights line from the first two rows using the brief formatter
        logger.info(f"Joining the title in list..")
        highlights = natural_join([format_movie_brief(r) for r in rows[:2]])
        # compute how many more items we have beyond the highlights
        more_count = max(len(rows) - 2, 0)
        # If we have a hint and more items, include both
        if hint and more_count > 0:
            return f"I found {len(rows)} title(s) matching your filters ({hint}): {highlights}, and {more_count} more."
        # if we only have a hint, include it
        if hint:
            return f"I found {len(rows)} title(s) matching your filters ({hint}): {highlights}."
        # if no hint but more items remain, mention the count
        if more_count > 0:
            return f"I found {len(rows)} title(s): {highlights}, and {more_count} more."
        # otherwise report what we have
        return f"I found {len(rows)} title(s): {highlights}."

    # fallback for unknown intents with some rows
    if rows:
        
        # join the first two titles as a quick answer
        logger.info(f"Joining the title in list..")
        first_two = natural_join([r.get("title") for r in rows[:2] if r.get("title")])
        # if we have a hint, include it
        if hint:
            return f"Here are the matches for your filters ({hint}): {first_two}."
        # otherwise just present the titles
        return f"Here are the matches: {first_two}."
    # if nothing at all, generic no-result line
    return "No matching movies found."



# format integer counts into friendly short strings
def format_count(count: Optional[int]):
    """Function to turn an integer count into a short string like '5k', '12k', or '1.2M'.

    Args: 
        count (int): Incoming Count value from results.

    Returns:
        count(str): str value after converting from int to str.
    """
    # return "unknown" when count is not an integer
    if not isinstance(count, int):
        return "unknown"
    # format millions with one decimal when needed
    if count >= 1_000_000:
        # compute millions with one decimal
        text = f"{count/1_000_000:.1f}M"
        # strip any trailing .0 for clean output
        return text.rstrip("0").rstrip(".")
    # format thousands as whole-k (e.g., 5k, 12k)
    if count >= 1000:
        # divide by 1000 and use integer part
        return f"{count//1000}k"
    
    return str(count)



# format a single movie row into a compact phrase
def format_movie_brief(row: Dict[str, Any]):
    """Function to turn one canonical movie row into a compact phrase:
            "Title (Year, Genres, 4.6★, 2,345 ratings)".

    Args: 
        row (dict): Containing the movie row.

    Returns:
        base as final compacgt phrase for movie row
    """
    # read the title safely
    title = row.get("title") or "Unknown Title"
    # read the year safely
    year = row.get("year")
    # read the genres list safely
    genres_list = row.get("genres") or []
    # join genres with slash for brevity
    genres_text = "/".join(genres_list[:3]) if genres_list else "Genre N/A"
    # read average rating safely
    avg = row.get("avg_rating")
    # read ratings count safely
    count = row.get("num_ratings")

    # build the rating part with a star if available
    rating_part = f"{avg:.1f}★" if isinstance(avg, (int, float)) else "rating N/A"
    # build the count part with a simple thousands separator
    # count_part = f"{count:,} ratings" if isinstance(count, int) else "count N/A"
    logger.info(f"Formatting the rating counts..")
    count_part = f"{format_count(count)} ratings" if isinstance(count, int) else "unknown rating count"
    # start with title
    base = title
    # add year if present
    if isinstance(year, int):
        base += f" ({year}"
        # add genres, rating, and count inside the same parentheses
        base += f", {genres_text}, {rating_part}, {count_part})"
    else:
        # if no year, add everything after a dash
        base += f" — {genres_text}, {rating_part}, {count_part}"

    return base



# format a single movie in an even simpler sentence
def format_movie_sentence(row: Dict[str, Any]):
    """Function to turn one movie row into a short sentence:
        "Title is an Action/Drama movie from 2008 with a 4.7★ rating and 5,000 ratings."

    Args: 
        row (dict): Containing the movie row.

    Returns:
        base as final compacgt phrase for movie row

    """
    # read fields with safe defaults
    title = row.get("title") or "This title"
    year = row.get("year")
    genres_list = row.get("genres") or []
    avg = row.get("avg_rating")
    count = row.get("num_ratings")

    # build genres text (fallback to 'Unknown genre')
    genres_text = "/".join(genres_list[:3]) if genres_list else "Unknown genre"
    # build rating text if available
    rating_text = f"{avg:.1f}★" if isinstance(avg, (int, float)) else "an unrated"
    # build count text with separators if available
    # count_text = f"{count:,} ratings" if isinstance(count, int) else "unknown rating count"
    logger.info(f"Formatting the rating counts..")
    count_text = f"{format_count(count)} ratings" if isinstance(count, int) else "unknown rating count"

    # build the core sentence parts
    if isinstance(year, int) and isinstance(avg, (int, float)):
        # full details case
        return f"{title} is an {genres_text} movie from {year} with a {rating_text} rating and {count_text}."
    if isinstance(year, int):
        # no average rating case
        return f"{title} is an {genres_text} movie from {year} with {count_text}."
    # no year either
    return f"{title} is an {genres_text} movie with a {rating_text} rating and {count_text}."



# join a few items in a human way
def natural_join(items: List[str]) -> str:
    """Function to join 1–3 items naturally: "A", "A and B", "A, B, and C".

    Args: 
        items (list): Containing the items.

    Returns:
        List containing the items after join.
    """
    # handle empty list
    if not items:
        return ""
    # handle one item
    if len(items) == 1:
        return items[0]
    # handle two items
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    # handle three or more but no more than 3
    return f"{', '.join(items[:-1])}, and {items[-1]}"
