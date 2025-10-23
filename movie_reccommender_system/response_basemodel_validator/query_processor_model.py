"""Pydantic basemodel for user intent and slots for rule based parser."""
from pydantic import BaseModel, Field, validator, computed_field
from typing import List, Optional, Literal, Dict, Any


# query parser Class - using the FastAPI Pydantic basemodel
class QueryParser(BaseModel):
    """Clsss - parsing user text into an intent and slots.
    
    User intents as literal - 
        - GET_DETAILS → user wants info about a specific movie (e.g. tell me about Inception).
        - RECOMMEND_BY_FILTER → user wants recommendations with conditions (e.g. recommend action movies from 2020).
        - TOP_N → user wants the top X movies by rating/popularity (e.g. top 10 dramas since 2015).
        - SIMILAR_MOVIES → user wants movies like a given movie (e.g. movies like Inception).
        - UNKNOWN → query did not match any known intent (fallback or LLM needed).
    """
    # user's intent  as a simple literal string (mentioned in above comments)
    # intent_list =["GET_DETAILS", "RECOMMEND_BY_FILTER", "TOP_N", "SIMILAR_MOVIES", "UNKNOWN"]
    intent: Literal[
        "GET_DETAILS",
        "RECOMMEND_BY_FILTER",
        "TOP_N",
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

     # rating comparison, None means not specified
    rating_compare: Optional[
        Literal["greater_than_or_equal", "less_than_or_equal"]] = Field(
            None,
            description="How to compare rating: greater_than_or_equal (>=) or less_than_or_equal (<=).",)

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


# compute top_n field if required
class ExecuteParsedRequest(BaseModel):
    text: str
    limit: int = Field(10, ge=1, le=50)

    @computed_field
    def top_n(self) -> int:
        return self.limit


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
    avg_rating: Optional[float]=None
    # number of ratings if available
    num_ratings: Optional[int]=None


# # Old version -> response executor basemodel
# class ExecuteResponse(BaseModel):
#     """Response body from /query/execute — parsed intent + rows."""
#     # the parsed query object
#     parsed: QueryParser
#     # a list of row results
#     results: List[SingleRowMovieRecord]=Field(default_factory=list)



# validate response after query exectuor handler for slot 
class ExecuteFullResponse(BaseModel):
    """Response body from /query/execute — parsed intent + rows + prepared expected output."""
    # the parsed query object
    parsed: QueryParser
    # a list of row results -> without llm inference
    results: List[SingleRowMovieRecord] = Field(default_factory=list)
    # expected payload from your main query processor - dispatcher/handler -> for LLM inference
    prepared: Dict[str, Any] = Field(
        default_factory=dict,
        description="Expected output with keys: intent (str), slots (dict), results (list).")

    @validator("prepared")
    def validate_prepared_shape(
        cls, 
        value: Dict[str, Any]):
        """Ensure prepared has the minimal required shape for the before the LLM inference."""
        # allow empty {} when not provided
        if not value:
            return value
        
        # prepared must be a dict
        if not isinstance(value, dict):
            raise ValueError("prepared must be a dictionary.")
        
        # required top-level keys
        for key in ("intent", "slots", "results"):
            if key not in value:
                raise ValueError(f"prepared is missing required key: '{key}'")
            
        # intent must be a non-empty string
        intent_value = value.get("intent")
        if not isinstance(intent_value, str) or not intent_value.strip():
            raise ValueError("prepared.intent must be a non-empty string.")
        
        # slots must be a dict
        if not isinstance(value.get("slots"), dict):
            raise ValueError("prepared.slots must be a dictionary.")
        
        # results must be a list
        results_list = value.get("results")
        if not isinstance(results_list, list):
            raise ValueError("prepared.results must be a list.")
        
        # basic per-row sanity (only if rows exist)
        normalized_rows = []
        for row in results_list:
            # convert BaseModel to dict if needed
            if isinstance(row, BaseModel):
                row_dict = row.dict()
            elif isinstance(row, dict):
                row_dict = row
            else:
                raise ValueError("Each item in prepared.results must be a dict or a Pydantic model.")

            # title present and non-empty
            title_val = row_dict.get("title")
            if not isinstance(title_val, str) or not title_val.strip():
                raise ValueError("Each prepared.results row must include a non-empty 'title'.")

            # movieId must be present for downstream normaliser (normalize_result_row)
            if "movieId" not in row_dict:
                raise ValueError("Each prepared.results row must include 'movieId'.")

            normalized_rows.append(row_dict)

        # replace with normalized dict rows to keep shape consistent
        value["results"] = normalized_rows
            
        return value


# prepare results for final response
class PreparedResultRow(BaseModel):
    movieId: int
    title: str
    year: Optional[int] = None
    avg_rating: Optional[float] = None
    num_ratings: Optional[int] = None
    genres: Optional[Any] = None


class ExecutePreparedResponse(BaseModel):
    """Final response body from /query/execute -> (intent, slots, results)."""
    intent: str
    slots: Dict[str, Any] = Field(default_factory=dict)
    results: List[PreparedResultRow] = Field(default_factory=list)

    @validator("intent")
    def validate_intent_is_not_empty(cls, intent_value: str) -> str:
        """Ensure intent is a non-empty string."""
        if not isinstance(intent_value, str) or not intent_value.strip():
            raise ValueError("intent must be a non-empty string.")
        return intent_value


