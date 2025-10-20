"""Script using the Pydantic models for user intent and slots for rule based parser."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ParsedQuery(BaseModel):
    """
    A clean result of parsing user text into an intent and slots.
    """

    # the intent name as a simple literal string
    intent: Literal[
        "GET_DETAILS",
        "RECOMMEND_BY_FILTER",
        "TOP_N",
        "WHO_DIRECTED",
        "WHO_STARRED",
        "SIMILAR_MOVIES",
        "UNKNOWN",
    ] = Field(..., description="The type of user intent detected.")

    # the raw user text we parsed
    raw_text: str = Field(..., description="The original user text.")

    # the movie title mentioned by the user, if any
    title: Optional[str] = Field(None, description="Movie title if present.")

    # one or more genres mentioned by the user (normalized names)
    genres: List[str] = Field(default_factory=list, description="Genres requested.")

    # single year like 2020
    year: Optional[int] = Field(None, description="Single year filter.")

    # starting year like 2015 for 'since 2015'
    year_from: Optional[int] = Field(None, description="Start year of range.")

    # ending year like 2020 for 'until 2020'
    year_to: Optional[int] = Field(None, description="End year of range.")

    # minimum rating threshold 1..5
    min_rating: Optional[float] = Field(None, description="Minimum avg rating filter (1..5).")

    # how many items user wants (top N)
    top_n: int = Field(10, description="How many results to return, default 10.")

    # sort preference, if any; defaults handled in SQL layer
    sort: Optional[Literal["rating", "popularity", "recent"]] = Field(
        None, description="Sort preference.")



class ParseRequest(BaseModel):
    """
    Request body for /query/parse — contains user text.
    """
    # user free text to parse
    text: str = Field(..., description="User text to parse.")


class ParseResponse(BaseModel):
    """
    Response body from /query/parse — returns the parsed intent and slots.
    """

    # the parsed query object
    parsed: ParsedQuery


class ExecuteRequest(BaseModel):
    """
    Request body for /query/execute — parse then retrieve in one step.
    """

    # user free text to parse and execute
    text: str = Field(..., description="User text to parse and execute.")

    # optional limit override
    limit: int = Field(10, ge=1, le=50, description="Max rows to return (1..50).")



class RowMovie(BaseModel):
    """
    One row returned from SQL — a minimal movie record.
    """

    # movie title to display
    title: str
    # release year for display
    year: Optional[int] = None
    # average rating if available
    avg_rating: Optional[float] = None
    # number of ratings if available
    num_ratings: Optional[int] = None


class ExecuteResponse(BaseModel):
    """
    Response body from /query/execute — parsed intent + rows.
    """

    # the parsed query object
    parsed: ParsedQuery
    # a list of row results
    results: List[RowMovie] = Field(default_factory=list)