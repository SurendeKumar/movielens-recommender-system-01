""" Script to build the summary field from normlaised data from LLM Preprocessing (llm_preprocessing.py)"""
import logging
# basic log info 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# deifne single logger for context builder
logger=logging.getLogger("LLM_Context_Builder")

# Extract compact context object
def extract_compact_context(
        normalised_data, 
        max_filters_length=140):
    """Function to build a compact context object from canonicalized query data.

    Args:
      normalised_data: dict returned by normalise_query_output()

    Output:
      dict with keys:
        result_count: int
        seed_title: str|None
        filters_text: str|None
        time_window: str|None
        rating_bounds: str|None
    """
    # extract intent
    intent = normalised_data.get("intent")
    # extract slots dictionary
    slots = normalised_data.get("slots", {})
    # extract results list
    results = normalised_data.get("results", [])

    # count number of results
    result_count = len(results)


    logger.info(f"Handling the time window.")
    time_window_text = build_time_window(slots)

    logger.info(f"Handling the rating bounding phrase.")
    rating_text = build_rating_bounds(slots)

    logger.info(f"Handling the title string.")
    seed_title = to_str_safe(slots.get("title"))

    logger.info(f"Building tghe final filter text.")
    filters_text = build_filters_text(
        intent, 
        slots, 
        time_window_text, 
        rating_text, 
        max_length=max_filters_length)

    # collect all movie titles from results
    titles = [r.get("title") for r in results if r.get("title")]

    logger.info(f"Successfully comleting the LLM Context builder tasks..")
    return {
        "result_count": result_count,
        "seed_title": seed_title,
        "filters_text": filters_text,
        "time_window": time_window_text,
        "rating_bounds": rating_text,
        "titles": titles,}



# Safely convert a value to string
def to_str_safe(value):
    """Function to convert a value to a stripped string, return None if empty.

    Args: 
        vlaue (str): Incoming value to be stripped as string.

    Returns:

    """
    # If input is None, return None
    if value is None:
        return None
    # convert to string and strip whitespace
    stripped_str_val = str(value).strip()
    # return None if result is empty after stripping
    return stripped_str_val if stripped_str_val else None


# normalize 'genres' values
def normalize_slot_genres(slots):
    """Function to normalize 'genres' or 'genre' from slots into a list of clean strings.

    Args:
        slots (dict): slot output after query processor output.
    
    Returns:
        List: containing the normalised genres 

    """
    # read from either "genres" or "genre"
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
    """FUnction to construct a human-readable time window phrase.
        Examples:
        start_year + end_year -> "between 2000 and 2010"
        start_year only -> "since 2000"
        end_year only -> "until 2010"
        year only -> "in 2005"

    Args: 
        slots (dict): Containung the year values.

    Returns:
        cleanned year value for LLM context. None is no slot for year.
    """
    # read slot values
    year = slots.get("year")
    start_year = slots.get("start_year")
    end_year = slots.get("end_year")

    # if both start and end provided
    if start_year is not None and end_year is not None:
        return f"between {start_year} and {end_year}"
    # if only start year provided
    if start_year is not None:
        return f"since {start_year}"
    # if only end year provided
    if end_year is not None:
        return f"until {end_year}"
    # if only year provided
    if year is not None:
        return f"in {year}"
    # if nothing provided
    return None


# Build rating bounds phrase
def build_rating_bounds(slots):
    """Function to construct a human-readable rating constraint phrase.
        Examples:
        min + max -> "between 3.5 and 4.5"
        min only -> "≥ 4.0"
        max only -> "≤ 3.0"
        exact rating -> "= 5.0"

    Args: 
        slots (dict): Containung the rating values.

    Returns:
        cleanned rating value for LLM context. None is no slot for rating.
    """
    # read slot values
    min_rating = slots.get("min_rating")
    max_rating = slots.get("max_rating")
    exact_rating = slots.get("rating")

    # if exact rating provided
    if exact_rating is not None:
        return f"= {round(float(exact_rating), 1)}"
    # if both min and max provided
    if min_rating is not None and max_rating is not None:
        return f"between {round(float(min_rating), 1)} and {round(float(max_rating), 1)}"
    # if only min rating provided
    if min_rating is not None:
        return f"≥ {round(float(min_rating), 1)}"
    # if only max rating provided
    if max_rating is not None:
        return f"≤ {round(float(max_rating), 1)}"
    return None


# Build a combined filters text line
def build_filters_text(
        intent, 
        slots, 
        time_window_text, 
        rating_text, 
        max_length=140):
    """Function to combine filters into one short text string.
        Order:
        - intent hint
        - genres
        - time window
        - rating bounds
        - seed title

    Args:
        intent (str): Incoming intent such as TOP_N.
        slots, 
        time_window_text, 
        rating_text,
        max_length (int): Default to 140.

    Returns:
        text (str): combined text for LLM context.
    """
    # list to store the each text as parts
    parts = []

    # add intent hint based on type
    if to_str_safe(intent) in {"RECOMMEND_BY_FILTER"}:
        parts.append("recommendations by filters")
    elif to_str_safe(intent) == "TOP_N":
        parts.append("top titles")
    elif to_str_safe(intent) == "SIMILAR_MOVIES":
        parts.append("similar titles")
    elif to_str_safe(intent) == "GET_DETAILS":
        parts.append("title details")

    # add genres from slots
    genres_list = normalize_slot_genres(slots)
    if genres_list:
        parts.append("genres=" + ", ".join(genres_list))

    # add time window if present
    if to_str_safe(time_window_text):
        parts.append(time_window_text)

    # add rating bounds if present
    if to_str_safe(rating_text):
        parts.append(rating_text)

    # add seed title if present
    seed_title = to_str_safe(slots.get("title"))
    if seed_title:
        parts.append(f'title="{seed_title}"')

    # join all parts with semicolons
    text = "; ".join(parts)

    # if too long, trim and add ellipsis
    if len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "…"

    # return final text or None
    return text if text else None




if __name__ == "__main__":
    # normalised_data_expected={
    #         "intent": "TOP_N",
    #         "slots": {
    #             "min_rating": 4.0,
    #             "start_year": 2000,
    #             "end_year": 2010
    #         },
    #         "results": [
    #             {
    #                 "movieId": "1",
    #                 "title": "The Dark Knight",
    #                 "year": 2008,
    #                 "avg_rating": 4.7,
    #                 "num_ratings": 5000,
    #                 "genres": [
    #                     "Action",
    #                     "Crime",
    #                     "Drama"
    #                 ]
    #             },
    #             {
    #                 "movieId": "2",
    #                 "title": "Inception",
    #                 "year": 2010,
    #                 "avg_rating": 4.6,
    #                 "num_ratings": 4500,
    #                 "genres": [
    #                     "Action",
    #                     "Sci-Fi",
    #                     "Thriller"
    #                 ]
    #             }
    #         ]
    #     }

    query_executor = {
            "intent": "TOP_N",
            "slots": {
                "start_year": "1998"
            },
            "results": [
                {
                    "movieId": 1,
                    "title": "Tokyo Fist (1995)",
                    "year": 1998,
                    "avg_rating": 4.0,
                    "num_ratings": 1,
                    "genres": "Action"
                },
                {
                    "movieId": 2,
                    "title": "Men With Guns (1997)",
                    "year": 1998,
                    "avg_rating": 3.5,
                    "num_ratings": 2,
                    "genres": "Action"
                },
                {
                    "movieId": 3,
                    "title": "Mercury Rising (1998)",
                    "year": 1998,
                    "avg_rating": 3.429,
                    "num_ratings": 7,
                    "genres": "Action"
                },
                {
                    "movieId": 4,
                    "title": "Man in the Iron Mask, The (1998)",
                    "year": 1998,
                    "avg_rating": 3.417,
                    "num_ratings": 12,
                    "genres": "Action"
                },
                {
                    "movieId": 5,
                    "title": "Replacement Killers, The (1998)",
                    "year": 1998,
                    "avg_rating": 3.308,
                    "num_ratings": 39,
                    "genres": "Action"
                }
            ]
        }

    
    import json
    response= extract_compact_context(query_executor, max_filters_length=140)
    # print("response: \n", response)
    print("response: \n", json.dumps(response, indent=4, ensure_ascii=False))
