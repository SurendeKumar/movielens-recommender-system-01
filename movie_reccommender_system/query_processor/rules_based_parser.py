"""Script for Rule-based Parser"""
import re
import logging
from movie_reccommender_system.query_processor import query_preprocessing
from movie_reccommender_system.response_basemodel_validator.query_processor_model import QueryParser
# basic log info 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# deifne single logger for context builder
logger=logging.getLogger("Query_Rule_Based_Parser")

# define dict of known genres from DB
KNOWN_GENRES = {
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "children": "Children",
    "comedy": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "fantasy": "Fantasy",
    "film-noir": "Film-Noir",
    "noir": "Film-Noir",
    "horror": "Horror",
    "musical": "Musical",
    "mystery": "Mystery",
    "romance": "Romance",
    "sci-fi": "Sci-Fi",
    "scifi": "Sci-Fi",
    "science fiction": "Sci-Fi",
    "thriller": "Thriller",
    "war": "War",
    "western": "Western",}

# define dict for numbers (words to numnbers)
WORD_NUMBERs = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,}



# parse user textGET_DE
def user_query_parser(text: str):
    """Function to parse the user queries into an intent and slots.

    Args:
        text (str): Incoming user's query text.

    Steps:
        - detect SIMILAR_MOVIES if 'movies like' appears
        - detect TOP_N if 'top N' appears
        - RECCOMEND_BY_FILTER
        - otherwise, if genres/years/min rating present or 'recommend' present → RECOMMEND_BY_FILTER
        - else UNKNOWN
    """
    # keep original text for the model
    raw_text = text
    
    logger.info(f"Converting text to lowercase..")
    convert_to_lowercase = query_preprocessing.covnert_text_to_lower_case(text)
    
    logger.info(f"Collecting the TOP_N from text..")
    top_n_value = get_top_number_from_text(text)
    
    logger.info(f"Collecting year values from text.")
    year, year_from, year_to = get_years_from_text(text)
    
    logger.info(f"Collecting rating values from text.")
    minimal_ratings, rating_compare = get_min_rating_from_text(text)
    
    logger.info(f"Collecting generes from text.")
    genres = get_genres_from_text(text)
    
    logger.info(f"Collecting the title from text..")
    title = get_title_from_text(text)

    # check phrase 'tell me about' for details intent
    if "tell me about" in convert_to_lowercase or "who directed" in convert_to_lowercase or "who starred" in convert_to_lowercase:
        # build a QueryParser for GET_DETAILS
        return QueryParser(
            intent="GET_DETAILS",
            raw_text=raw_text,
            title=title,
            genres=[],
            year=year or None,
            year_from=year_from or None,
            year_to=year_to or None,
            min_rating=minimal_ratings or None,
            top_n=top_n_value,)

    # check phrase 'movies like' for similar movies intent
    if "movies like" in convert_to_lowercase:
        # build a QueryParser for SIMILAR_MOVIES
        return QueryParser(
            intent="SIMILAR_MOVIES",
            raw_text=raw_text,
            title=title,
            genres=[],
            year=None,
            year_from=None,
            year_to=None,
            min_rating=minimal_ratings or None,
            top_n=top_n_value,)

    # check for 'top' presence for top-n intent
    if "top" in query_preprocessing.split_text_into_words_corpus(convert_to_lowercase):
        # build a QueryParser for TOP_N
        return QueryParser(
            intent="TOP_N",
            raw_text=raw_text,
            title="",
            genres=genres,
            year=year or None,
            year_from=year_from or None,
            year_to=year_to or None,
            min_rating=minimal_ratings or None,
            rating_compare=rating_compare, 
            top_n=top_n_value,
            sort="rating",)

    # check for recommend intent or presence of filters
    if "recommend" in convert_to_lowercase or genres or year or year_from:
        # build a QueryParser for RECOMMEND_BY_FILTER
        return QueryParser(
            intent="RECOMMEND_BY_FILTER",
            raw_text=raw_text,
            title="",
            genres=genres,
            year=year or None,
            year_from=year_from or None,
            year_to=year_to or None,
            min_rating=minimal_ratings or None,
            top_n=top_n_value,
            sort="rating",)

    # fallback to unknown if no rules matched
    return QueryParser(
        intent="UNKNOWN",
        raw_text=raw_text,)


# 1. find 'top' from text
def get_top_number_from_text(text: str):
    """Function to find 'top N' in user text.
        - clamps to 1..50
        - defaults to 10 if not found

    Args:
        text (str): Incoming text from user's query.

    Returns:
        Number (int): returns the number after 'top' if present (digit or word)
    
    """
    # 1. convert text to lower case
    convert_to_lower_Case = query_preprocessing.covnert_text_to_lower_case(text)
    # 2. split into words 
    words_list = query_preprocessing.split_text_into_words_corpus(convert_to_lower_Case)

    # check if "top" is not present, if not return default 10
    if "top" not in words_list:
        return 10
    
    # get the position of the first "top"
    position_index = words_list.index("top")
    # if there is no word after "top" then return default 10
    if position_index + 1 >= len(words_list):
        return 10
    
    # read the next word after "top"
    next_word = words_list[position_index + 1]
    # if the next word is a number like "10" then parse it
    if next_word.isdigit():
        num = int(next_word)
        # clamp to 1..50 and return
        return max(1, min(50, num))
    
    # if the next word is a number word like "ten" then map it
    if next_word in WORD_NUMBERs:
        num = WORD_NUMBERs[next_word]
        # clamp to 1..50 and return
        return max(1, min(50, num))
    
    # if nothing matched then return default 10
    return 10


# 2. find years value
def get_years_from_text(text: str):
    """Function to extract year info from text.
        - detects a single year (e.g., '2010')
        - detects 'since 2015' (year_from)
        - detects '2010-2015' or '2010 to 2015' (range)

    Args: 
        text (str): Incoming text from user's query.

    Returns 
        Tuple: (single_year, year_from, year_to).

    """
    # convert text into lower case
    convert_to_lower_Case = query_preprocessing.covnert_text_to_lower_case(text)
    # split into words
    word_list = query_preprocessing.split_text_into_words_corpus(convert_to_lower_Case)

    # start with no years found - None as placeholder
    single_year= None
    year_from= None
    year_to= None

    # scan for "since Y" pattern - loop over all word positions
    for i in range(len(word_list)):
        # check for the word "since"
        if word_list[i] == "since":
            # check if there is a word after "since"
            if i + 1 < len(word_list) and query_preprocessing.is_four_digit_year(word_list[i + 1]):
                # set year_from to that year
                year_from = int(word_list[i + 1])

    # scan for a hyphenated range like "2010-2015" - loop over all words
    for word in word_list:
        # check if the token contains a hyphen
        if "-" in word:
            # try to split into two parts
            parts = word.split("-")
            # ensure we got exactly two parts like ["2010", "2015"]
            if len(parts) == 2 and query_preprocessing.is_four_digit_year(parts[0]) and query_preprocessing.is_four_digit_year(parts[1]):
                # set from and to in sorted order
                y1, y2 = int(parts[0]), int(parts[1])
                year_from, year_to = (min(y1, y2), max(y1, y2))

    # scan for "Y to Z" pattern - loop over positions
    for i in range(len(word_list) - 2):
        # read three consecutive tokens
        a, b, c = word_list[i], word_list[i + 1], word_list[i + 2]
        # check for pattern "2010 to 2015"
        if query_preprocessing.is_four_digit_year(a) and b == "to" and query_preprocessing.is_four_digit_year(c):
            # set from and to in sorted order
            y1, y2 = int(a), int(c)
            year_from, year_to = (min(y1, y2), max(y1, y2))

    # check for "between Y and Z" pattern
    for i in range(len(word_list) - 3):
        # take four consecutive words
        a, b, c, d = word_list[i], word_list[i + 1], word_list[i + 2], word_list[i + 3]
        # if pattern matches "between 2015 and 2020"
        if a == "between" and query_preprocessing.is_four_digit_year(b) and c == "and" and query_preprocessing.is_four_digit_year(d):
            # assign year_from and year_to in sorted order
            y1, y2 = int(b), int(d)
            year_from, year_to = (min(y1, y2), max(y1, y2))

    # if we still do not have a range or a 'since' try to capture a single year - loop over all words
    if year_from is None and year_to is None:
        # collect all years present
        all_years = [int(word) for word in word_list if query_preprocessing.is_four_digit_year(word)]
        # if exactly one year is present, assign it to single_year
        if len(all_years) == 1:
            single_year = all_years[0]

    # return years value tuple
    return (single_year, year_from, year_to)


# 3. find minimal movie ratings
def get_min_rating_from_text(text: str):
    """Find a minimal rating threshold (1..5) from user text.
    Supports:
      - "rating 4"
      - "rating at least 4"
      - "rating greater than 3"
      - "rating less than 3.5"
      - "min 4" / "minimum 4"
    Returns: (rating_value, comparator) or (None, None)
             comparator ∈ {"greater_than_or_equal", "less_than_or_equal"}
    """
    # make a lower-case copy
    lower_text = query_preprocessing.covnert_text_to_lower_case(text)
    # normalise a common join error: "atleast" -> "at least"
    lower_text = lower_text.replace("atleast", "at least")
    # split into words/tokens
    word_list = query_preprocessing.split_text_into_words_corpus(lower_text)
    # cache length for bounds checks
    token_count = len(word_list)

    # helper: clamp to 1..5
    def clamp_1_to_5(value):
        return max(1.0, min(5.0, value))

    # patterns that begin with the word "rating"
    for index in range(token_count):
        # check for the token "rating"
        if word_list[index] != "rating":
            continue

        # pattern "rating at least X"  -> >= X
        if (index + 3 < token_count
            and word_list[index + 1] == "at"
            and word_list[index + 2] == "least"):
            rating_value = query_preprocessing.parse_float_safe(word_list[index + 3])
            if rating_value is not None:
                return (clamp_1_to_5(rating_value), "greater_than_or_equal")

        # pattern "rating greater than X" -> >= X
        if (index + 3 < token_count
            and word_list[index + 1] == "greater"
            and word_list[index + 2] == "than"):
            rating_value = query_preprocessing.parse_float_safe(word_list[index + 3])
            if rating_value is not None:
                return (clamp_1_to_5(rating_value), "greater_than_or_equal")

        # pattern "rating less than X" -> <= X
        if (index + 3 < token_count
            and word_list[index + 1] == "less"
            and word_list[index + 2] == "than"):
            rating_value = query_preprocessing.parse_float_safe(word_list[index + 3])
            if rating_value is not None:
                return (clamp_1_to_5(rating_value), "less_than_or_equal")

        # pattern "rating X" -> >= X
        if index + 1 < token_count:
            rating_value = query_preprocessing.parse_float_safe(word_list[index + 1])
            if rating_value is not None:
                return (clamp_1_to_5(rating_value), "greater_than_or_equal")

    # patterns "min X" / "minimum X" -> >= X
    for index in range(token_count - 1):
        # check for "min" or "minimum"
        if word_list[index] in ("min", "minimum"):
            # ensure a next token exists and parse it
            rating_value = query_preprocessing.parse_float_safe(word_list[index + 1])
            if rating_value is not None:
                return (clamp_1_to_5(rating_value), "greater_than_or_equal")

    # return none if nothing matched
    return (None, None)



# 4. find genres 
def get_genres_from_text(text: str):
    """Function to find any known genres (KNOWN_GENRES dict) mentioned in the text.

    Args:
        text (str): Incoming text from user's query.

    Returns:
        list: containing the genres found.
    """
    # make a lower-case copy
    convert_to_lowercase = query_preprocessing.covnert_text_to_lower_case(text)

    # start an empty list for found genres
    found_genres_list = []

    # check multi-word genre first e.g. 'science fiction'
    if "science fiction" in convert_to_lowercase:
        # append canonical form if present
        found_genres_list.append(KNOWN_GENRES["science fiction"])

    # check for single-word or dash forms by simple substring match with word boundaries approximated - loop over the keys in KNOWN_GENRES
    for key, value in KNOWN_GENRES.items():
        # skipping the 'science fiction' here because we already handled it
        if key == "science fiction":
            continue
        # if the key appears as a substring surrounded by spaces or at edges then accept it
        if key in convert_to_lowercase:
            # append canonical form if not already present
            if value not in found_genres_list:
                found_genres_list.append(value)

    # return the list of unique canonical genre names
    return found_genres_list



# 5 find title from text
def get_title_from_text(text: str):
    """Function to extract a movie title from text.
        main steps:
            1) quoted text: "..." or '...'
            2) after 'about '
            3) after 'like '
            4) after 'who directed '
            5) after 'who starred ' or 'who starred in '
        
    Args:
        text (str): Incoming text from user's query.
    
    Returns: 
        empty string if not confident.
    """
    # using the raw text to preserve original casing for titles
    raw_text = text.strip()
    # 1. search for first and second double-quote characters
    if '"' in raw_text:
        # find the first double-quote position
        i = raw_text.find('"')
        # find the next double-quote after i
        j = raw_text.find('"', i + 1)
        # if both quotes exist and surround content, return the inside
        if i != -1 and j != -1 and j > i + 1:
            # return the substring inside the quotes
            return raw_text[i + 1 : j].strip()

    # 2. search for first and second single-quote characters
    if "'" in raw_text:
        # find the first single-quote position
        i = raw_text.find("'")
        # find the next single-quote after i
        j = raw_text.find("'", i + 1)
        # if both quotes exist and surround content, return the inside
        if i != -1 and j != -1 and j > i + 1:
            # return the substring inside the quotes
            return raw_text[i + 1 : j].strip()

    # make a lower-case copy for simple phrase checks
    convert_to_lowercase = query_preprocessing.covnert_text_to_lower_case(raw_text)

    # 3. if the text contains 'about ', return everything after it
    if "about " in convert_to_lowercase:
        # find where 'about ' starts
        pos = convert_to_lowercase.find("about ")
        # slice the raw text after that phrase to keep original casing
        return raw_text[pos + len("about ") :].strip()

    # 4. if the text contains 'like ', return everything after it 
    if "like " in convert_to_lowercase:
        # find where 'like ' starts
        pos = convert_to_lowercase.find("like ")
        # slice the raw text after that phrase to keep original casing
        return raw_text[pos + len("like ") :].strip()
    
    # 5. if the text contains 'who directed', return everything after it  
    if "who directed " in convert_to_lowercase:
        # find where 'who directed ' starts
        pos = convert_to_lowercase.find("who directed ")
        # slice the raw text after that phrase to keep original casing
        return raw_text[pos + len("who directed ") :].strip()

    # 6. if the text contains 'who starred in', everything after it
    if "who starred in " in convert_to_lowercase:
        # find where 'who starred in ' starts
        pos = convert_to_lowercase.find("who starred in ")
        # slice the raw text after that phrase to keep original casing
        return raw_text[pos + len("who starred in ") :].strip()

    # handle 'who starred ' without 'in',  everything after it
    if "who starred " in convert_to_lowercase:
        # find where 'who starred in ' starts
        pos = convert_to_lowercase.find("who starred ")
        # slice the raw text after that phrase to keep original casing
        return raw_text[pos + len("who starred ") :].strip()

    return ""