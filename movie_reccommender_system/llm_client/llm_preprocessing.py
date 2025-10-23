"""Script to handle the pre-processing steps for incoming output from query executor """
import logging
# basic log info 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# deifne single logger for context builder
logger=logging.getLogger("LLM_Preprocessing")

# normalise the query output for LLM
def normalise_query_output(data, max_results=10):
    """Main function to trigger the preprocessing steps.

    Args:
        data (dict): Incoming data after query executor.
    
    Returns:
        Dict: containing cleanned inputs manners for LLM inference..
    """
    logger.info(f"Starting to validate the input data for LLM inference.")
    intent, slots, results = validate_input(data)
    
    logger.info(f"Normalising the slots from input data.")
    clean_slots = normalize_slots(slots)
    
    logger.info(f"Validating the result for dedupes..")
    clean_results = dedupe_and_collect(results)
    
    logger.info(f"Sorting & limiting the result size..")
    capped_results = sort_and_limit_result_size(intent, clean_results, max_results)

    logger.info(f"Successfully completed the LLM Preprocessing tasks..")
    return {
        "intent": intent,
        "slots": clean_slots,
        "results": capped_results}



# convert values to integer
def to_int(value, default=None):
    """ Function to convert a value to int.

    Args: 
        value (str): incoming value from inttent.
    
    Returns: 
        Int value, default to None if conversation fails.
    """
    # try to convert to integer
    try:
        return int(value)
    # if value is invalid or None, return default
    except (TypeError, ValueError):
        return default


# convert values to float
def to_float(value, default=None):
    """ Function to convert a value to float.

    Args: 
        value (str): incoming value from intent.
    
    Returns: 
        float value, default to None if conversation fails.
    """
    # try to convert to floatt
    try:
        return float(value)
    # if value is invalid or None, return default
    except (TypeError, ValueError):
        return default


# input validator
def validate_input(data):
    """Function to validate that the input is a dictionary with expected keys:
        - intent: str
        - slots: dict
        - results: list

    Args: 
        data (dict): Incoming dict after query executor.
    
    Returns:
        tuple: containing (intent, slots, results).
    """
    # raise error if input is not a dict
    if not isinstance(data, dict):
        raise ValueError("Input must be a dictionary with keys: intent, slots, results")

    # extract intent and clean up whitespace
    intent = data.get("intent", "").strip() if isinstance(data.get("intent"), str) else ""
    # extract slots dict, fallback to empty dict
    slots = data.get("slots", {}) if isinstance(data.get("slots"), dict) else {}
    # extract results list, fallback to empty list
    results = data.get("results", []) if isinstance(data.get("results"), list) else []
    # return validated values
    return intent, slots, results


# normalize slot values -> (years, ratings)
def normalize_slots(slots):
    """Function to Normalize slot values:
        - Convert year-related fields to int
        - Convert rating-related fields to float
        - Leave others unchanged

    Args:
        slots (dict): Incoming slots as dict.

    Returns:
        Dict: containing cleaned slots dictionary.
    """
    # define dict for cleaned slots
    clean_slots = {}
    # iterate over all slot keys and values
    for key, value in slots.items():
        # if key is a year field, convert to int
        if key in {"year", "start_year", "end_year"}:
            clean_slots[key] = to_int(value)
        # if key is a rating field, convert to float
        elif key in {"min_rating", "max_rating", "rating"}:
            clean_slots[key] = to_float(value)
        # else slot as it is
        else:
            clean_slots[key] = value
  
    return clean_slots


# text normaliser - single row per movie
def normalize_result_row(row):
    """Function to normalize one movie result row into a consistent schema:
        {movieId, title, year, avg_rating, num_ratings, genres, similarity?}

    Args: 
        row (dict): results containing movie the single row as dict
    
    Returns: 
        None if row is invalid.
    """
    # skip invalid rows - if not a dict
    if not isinstance(row, dict):
        return None

    # extract movie id (accept multiple possible keys)
    movie_id = row.get("movieId") or row.get("movie_id")
    # extract title
    title = row.get("title")
    # skip if id or title missing
    if movie_id is None or not isinstance(title, str):
        return None

    # normalize numeric fields -> year, ratings, similarity
    year = to_int(row.get("year"))
    avg_rating = to_float(row.get("avg_rating") or row.get("rating") or row.get("avgRating"))
    num_ratings = to_int(row.get("num_ratings") or row.get("ratings_count") or row.get("numRatings"))
    similarity = to_float(row.get("similarity"))

    # normalize genres into a list
    genres = row.get("genres")
    if isinstance(genres, str):
        # split by commas or pipes, clean whitespace
        genres_list = [g.strip() for g in genres.replace("|", ",").split(",") if g.strip()]
    elif isinstance(genres, list):
        # ensure every genre is a clean string
        genres_list = [str(g).strip() for g in genres if str(g).strip()]
    else:
        # default to empty list if missing
        genres_list = []

    # build normalized row dictionary
    clean_row = {
        "movieId": str(movie_id),         
        "title": title.strip(),           
        "year": year,                     
        "avg_rating": avg_rating,          
        "num_ratings": num_ratings,        
        "genres": genres_list}

    # include similarity only if it exists
    if similarity is not None:
        clean_row["similarity"] = similarity

    return clean_row


# deduplicate results by movieId
def dedupe_and_collect(results):
    """Function to deduplicate and normalize all results.
        - Removes duplicates by movieId.
        - Returns a list of cleaned movie rows.

    Args: 
        results (list): containing the movies row as dict.

    Returns:
        list: containing  the moview row as dict after cleanning.
    """
    # empty set to avoid the duplicates rows
    movie_row_set = set()
    # empty list to store the movies row
    clean_rows = []
    # iterate over raw results
    for row in results:
        # normalise result row - invoking (normalize_result_row)
        clean_row = normalize_result_row(row)
        # keep valid and unique rows
        if clean_row and clean_row["movieId"] not in movie_row_set:
            movie_row_set.add(clean_row["movieId"])
            clean_rows.append(clean_row)
    return clean_rows


# Sort results according to intent and limit the size
def sort_and_limit_result_size(
        intent, 
        results,
        max_results=10):
    """Function to sort results according to intent rules:
        - TOP_N → rating desc, num_ratings desc, title
        - SIMILAR_MOVIES → similarity desc, rating desc, title
        - RECOMMEND → rating desc, num_ratings desc, title
        - GET_DETAILS → title asc, year asc
        - Default → rating desc, title asc
        Then limit the list to max_results.

    Args:
        intent (str): Intent after query executor.
        results (list): containing the movie rows as dict.
        max_result (int): maximum reuslts default to 10.

    Returns: 
        List: result list after sorting and limiting the size to max_results.

    """
    ### intent sorting logic ##
    # check if TOP_N
    if intent == "TOP_N":
        results.sort(key=lambda r: (
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            -(r["num_ratings"] if r["num_ratings"] is not None else -1),
            r["title"]
        ))
    
    # check if SIMILAR_MOVIES
    elif intent == "SIMILAR_MOVIES":
        results.sort(key=lambda r: (
            -(r.get("similarity") if r.get("similarity") is not None else float("-inf")),
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            r["title"]
        ))
    
    # check if RECOMMEND_BY_FILTER or RECOMMEND
    elif intent in {"RECOMMEND_BY_FILTER", "RECOMMEND"}:
        results.sort(key=lambda r: (
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            -(r["num_ratings"] if r["num_ratings"] is not None else -1),
            r["title"]
        ))
    
    # check if GET_DETAILS
    elif intent == "GET_DETAILS":
        results.sort(key=lambda r: (r["title"], r["year"] if r["year"] is not None else 0))
    else:
        results.sort(key=lambda r: (
            -(r["avg_rating"] if r["avg_rating"] is not None else float("-inf")),
            r["title"]
        ))

    # return only up to max_results items
    return results[:max_results if isinstance(max_results, int) and max_results > 0 else 10]





## driver scripts
if __name__ == "__main__": 
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
    response = normalise_query_output(data=query_executor, max_results=10)
    print("response: \n", json.dumps(response, indent=4, ensure_ascii=False))