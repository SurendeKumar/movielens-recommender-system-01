""" Movielens Data Ingestor Router """
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel, Field
from movie_reccommender_system.response_basemodel_validator import data_ingestor_model
from movie_reccommender_system.data_ingestor.data_ingestor_main import MovieLensSqliteIngestor
# initiate load_dotenv
load_dotenv()
# define basic config
logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# logger for this router
logger = logging.getLogger("data_ingestor_api")

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


# 1. movielens data insertion
@router.post(
        "/ingest/data-insertion", 
        response_model=data_ingestor_model.MovieLensInsertResponse)
def ingest_insert_only():
    """
    - Insert movies and ratings. 
    - POST because it mutates the DB.
    """
    logger.info("Starting /ingest/data-insertion request")
    result = DataIngestor.run_movielens_data_insertion()
    logger.info(f"Completed /ingest/data-insertion: inserted {result.get('movie_rows', 0)} movies, {result.get('rating_rows', 0)} ratings")
    return result


# 2. genres per movies
@router.post(
        "/ingest/genres", 
        response_model=data_ingestor_model.GenresResponse)
def ingest_genres_only():
    """
    - Build genres and movie_genres tables from the movies table. 
    - POST because it mutates the DB.
    """
    logger.info(f"Starting /ingest/genres request..")
    result=DataIngestor.run_genres_insertion()
    logger.info(f"Completed /ingest/genres -> created {result.get('genre_count', 0)} genres, {result.get('movie_genre_links', 0)} movie-genre links")
    return result


# 3. movies & ratings stats compuation insertion
@router.post(
        "/ingest/movie-ratings-stats",
        response_model=data_ingestor_model.MovieRatingStatsResponse)
def ingest_movie_stats_only():
    """
    - Compute and update avg_rating and num_ratings per movie. 
    - POST because it mutates the DB.
    """
    logger.info(f"Starting /ingest/movie-ratings-stats request..")
    result = DataIngestor.run_movie_ratings_stats_insertion()
    logger.info(f"Completed /ingest/movie-ratings-stats -> updated {result.get('updated_movies', 0)} movies")
    return result



# 4. run all ingestors in order
@router.post(
        "/ingest/data-ingestor", 
        response_model=data_ingestor_model.MovieLensIgenstorResponse)
def ingest_full():
    """
    - Run the whole ingestion flow in the right order. 
    - POST because it mutates the DB.
    """
    logger.info(f"Starting /ingest/data-ingestor..")
    result = DataIngestor.run_data_ingestor()
    logger.info(f"Completed /ingest/data-ingestor -> success: {result.get('success', False)} , message: {result.get('message', '')}")
    return result