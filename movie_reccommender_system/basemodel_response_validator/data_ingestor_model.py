"""Pydantic basemodel for data ingestor response parser."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# define Pydantic response model validator
class MovieLensInsertResponse(BaseModel):
    status: str = Field(..., description="success or failure string")
    message: str
    movie_rows: int
    rating_rows: int

# genres response validator
class GenresResponse(BaseModel):
    success: bool
    message: str
    genre_count: int
    movie_genre_links: int

# movie rating stats reponse validator
class MovieRatingStatsResponse(BaseModel):
    success: bool
    message: str
    updated_movies: int


# movielens complete response validator
class MovielensCompleteResponse(BaseModel):
    insert_movielens: MovieLensInsertResponse
    genres_movie_ratings: GenresResponse
    movie_rating_stats: MovieRatingStatsResponse


# movie lens ingestor response validator 
class MovieLensIgenstorResponse(BaseModel):
    success: bool
    message: str
    steps: MovielensCompleteResponse

