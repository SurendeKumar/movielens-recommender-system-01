"""FastAPI endpoints for ingestion with Pydantic response models."""
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel, Field
from movie_reccommender_system.data_ingestor.db_ingestor_main import MovieLensSqliteIngestor
# initiate load_dotenv
load_dotenv()
# set up router
router = APIRouter(tags=["movielens-data-ingestion"])

# read paths from env or use defaults
DATA_PATH = os.getenv("MOVIELENS_DATA_PATH", "./movie_reccommender_system/data_raw")
DB_PATH = os.getenv("SQLITE_DB_PATH", "./movie_reccommender_system/db/movies.db")

# initiate the class - MovieLensSqliteIngestor() as single instances
DataIngestor = MovieLensSqliteIngestor(
    data_folder_path=DATA_PATH, 
    db_file_path=DB_PATH, 
    chunk_size=5000)


# define Pydantic response model
class MovieLensInsertResponse(BaseModel):
    status: str = Field(..., description="success or failure string")
    message: str
    movie_rows: int
    rating_rows: int


class GenresResponse(BaseModel):
    success: bool
    message: str
    genre_count: int
    movie_genre_links: int


class MovieRatingStatsResponse(BaseModel):
    success: bool
    message: str
    updated_movies: int


class MovielensCompleteResponse(BaseModel):
    insert_movielens: MovieLensInsertResponse
    genres_movie_ratings: GenresResponse
    movie_rating_stats: MovieRatingStatsResponse


class MovieLensIgenstorResponse(BaseModel):
    success: bool
    message: str
    steps: MovielensCompleteResponse


# 1. movielens data insertion
@router.post(
        "/ingest/data-insertion", 
        response_model=MovieLensInsertResponse)
def ingest_insert_only():
    """
    - Insert movies and ratings. 
    - POST because it mutates the DB.
    """
    return DataIngestor.run_movielens_data_insertion()


# 2. genres per movies
@router.post(
        "/ingest/genres", 
        response_model=GenresResponse)
def ingest_genres_only():
    """
    - Build genres and movie_genres tables from the movies table. 
    - POST because it mutates the DB.
    """
    return DataIngestor.run_genres_insertion()


# 3. movies & ratings stats compuation insertion
@router.post(
        "/ingest/movie-ratings-stats",
        response_model=MovieRatingStatsResponse)
def ingest_movie_stats_only():
    """
    - Compute and update avg_rating and num_ratings per movie. 
    - POST because it mutates the DB.
    """
    return DataIngestor.run_movie_ratings_stats_insertion()



# 4. run all ingestors in order
@router.post(
        "/ingest/data-ingestor", 
        response_model=MovieLensIgenstorResponse)
def ingest_full():
    """
    - Run the whole ingestion flow in the right order. 
    - POST because it mutates the DB.
    """
    return DataIngestor.run_data_ingestor()
