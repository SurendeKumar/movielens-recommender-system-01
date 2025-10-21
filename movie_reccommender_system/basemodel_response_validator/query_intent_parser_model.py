"""Pydantic basemodel for user intent and slots for rule based parser."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# query parser Class - using the FastAPI Pydantic basemodel
class QueryParser(BaseModel):
    """Clsss - parsing user text into an intent and slots.
    
    User intents as literal - 
        - GET_DETAILS → user wants info about a specific movie (e.g. tell me about Inception).
        - RECOMMEND_BY_FILTER → user wants recommendations with conditions (e.g. recommend action movies from 2020).
        - TOP_N → user wants the top X movies by rating/popularity (e.g. top 10 dramas since 2015).
        - WHO_DIRECTED → user asks who directed a given movie.
        - WHO_STARRED → user asks who acted/starred in a given movie.
        - SIMILAR_MOVIES → user wants movies like a given movie (e.g. movies like Inception).
        - UNKNOWN → query did not match any known intent (fallback or LLM needed).
    """
    # user's intent  as a simple literal string (mentioned in above comments)
    # intent_list =["GET_DETAILS", "RECOMMEND_BY_FILTER", "TOP_N", "WHO_DIRECTED", "WHO_STARRED", "SIMILAR_MOVIES", "UNKNOWN"]
    intent: Literal[
        "GET_DETAILS",
        "RECOMMEND_BY_FILTER",
        "TOP_N",
        "WHO_DIRECTED",
        "WHO_STARRED",
        "SIMILAR_MOVIES",
        "UNKNOWN",] = Field(..., description="The type of user intent detected.")

    # raw user text we parsed
    raw_text: str=Field(..., description="The original user text.")

    # movie title mentioned by the user, if any
    title: Optional[str]=Field(None, description="Movie title if present.")

    # one or more genres mentioned by the user (normalized names)
    genres: List[str]=Field(default_factory=list, description="Genres requested.")

    # single year like 2020
    year: Optional[int]=Field(None, description="Single year filter.")

    # starting year like 2015 for 'since 2015'
    year_from: Optional[int]=Field(None, description="Start year of range.")

    # ending year like 2020 for 'until 2020'
    year_to: Optional[int]=Field(None, description="End year of range.")

    # minimum rating threshold 1..5
    min_rating: Optional[float]=Field(None, description="Minimum avg rating filter (1..5).")

    # how many items user wants (top N)
    top_n: int=Field(10, description="How many results to return, default 10.")

    # sort preference, if any (defaults handled in SQL layer)
    sort: Optional[Literal["rating", "popularity", "recent"]] = Field(
        None, description="Sort preference.")


# request parser basemodel
class ParseRequest(BaseModel):
    """Request body for /query/parse — contains user text."""
    # user free text to parse
    text: str= Field(..., description="User text to parse.")


# response parser basemodel
class ParseResponse(BaseModel):
    """Response body from /query/parse — returns the parsed intent and slots."""
    # parsed the response as - QueryParser
    parsed: QueryParser


# request executor basemodel
class ExecuteRequest(BaseModel):
    """Request body for /query/execute — parse then retrieve in one step."""
    # user free text to parse and execute
    text: str=Field(..., description="User text to parse and execute.")

    # optional limit override
    limit: int=Field(10, ge=1, le=50, description="Max rows to return (1..50).")


# movie record basemodel
class SingleRowMovieRecord(BaseModel):
    """One row returned from SQL — a minimal movie record.
        - Single row representation for the movie records.
    """
    # movie title to display
    title: str
    # release year for display
    year: Optional[int]=None
    # average rating if available
    avg_rating: Optional[int]=None
    # number of ratings if available
    num_ratings: Optional[int]=None


# response executor basemodel
class ExecuteResponse(BaseModel):
    """Response body from /query/execute — parsed intent + rows."""
    # the parsed query object
    parsed: QueryParser
    # a list of row results
    results: List[SingleRowMovieRecord]=Field(default_factory=list)