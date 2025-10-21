""" Script to preprocess the user  queries 
    1. convert incoming query as lower case
    2. split incoming text into words adter striping the leading or trailing spaces.
    3. check if the year value is 4-digits
    4. check if floats are in the user's queries - ratings

"""

# convert text as lower text and strip the outer spaces
def covnert_text_to_lower_case(text: str):
    """Function to convert the text lower-case and strip outer spaces.
    
    Args:
        text (str): Incoming text from user's query.

    Returns:
        text (str): lower case and striped from outer spaces.
    """
    # convert to lower case
    text_lower = text.lower()
    # remove leading and trailing spaces
    return text_lower.strip()


# split text into words
def split_text_into_words_corpus(text: str):
    """Function to split text into words by spaces.

    Args: 
        text (str): Incoming text from user's query.
    
    Returns:
        list containing the words after split.
    """
    # split text into words
    split_into_words = text.split()
    # list containing words after text split
    return split_into_words


# check for year in text
def is_four_digit_year(text: str) -> bool:
    """Function to check if a string is a valid year like '1999' or '2015'.

    Args:
        text (str): Incoming text from user's query.

    Returns:
        Boolean(True/False)

    """
    # check if length is 4 and all digits
    if len(text) != 4 or not text.isdigit():
        return False
    
    # convert to integer
    year_value = int(text)
    # accept years from 1900 to 2099 for this dataset
    return 1900 <= year_value <= 2099



# parse float value from text
def parse_float_safe(text: str):
    """Function to parse a float from a text string.
    
    Args:
        text (str): Incoming text from user's query.
    
    Returns: 
        Return None on failure.
    """
    # wrap in try/except to avoid ValueError
    try:
        # attempt to convert to float
        return float(text)
    except Exception:
        # return None if conversion fails
        return None
    

# year value processor from date text
def extract_year_from_text(date_text: str) -> int:
    """Function to extract a 4-digit year from a date string.
        - Checks if the last 4 characters form a valid year.
        - If not, scans through the string to find the first 4-digit number.
        - Returns the year as an integer, or 0 if nothing found.

    Args: 
        date_text (str): Input text containing a year value.

    Returns:
        int: Extracted 4-digit year or 0 if not found.
    """
    # if the input is empty or None then return 0 
    if not date_text:
        return 0

    # check the last 4 characters of the text
    last_four_chars = str(date_text)[-4:]

    # if the last 4 characters are digits then assume they form a year
    if last_four_chars.isdigit():
        return int(last_four_chars)

    # else scan the text from start to end
    for i in range(len(date_text) - 3):
        # take a chunk of 4 consecutive characters
        four_char_segment = date_text[i : i + 4]

        # if this chunk is all digits, treat it as a year
        if four_char_segment.isdigit():
            return int(four_char_segment)

    # if no 4-digit number was found, return 0
    return 0
