import os
import json
import logging
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException
# from movie_reccommender_system.db import db_select
# from movie_reccommender_system.data_ingestor import sqlite_ingestor, data_loader
from router.data_ingestor_router import router as movielens_sqlite_data_ingestor
from router.query_processor_router import router as movielens_query_processor
from router.hf_llama_inference_router import router as movielens_query_responder

# initiate the load_dotenv
load_dotenv()

# basic logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)


# initiate the app 
API_VERSION="1.0.0"
API_TITLE="Advance Movie Recommender System"
app = FastAPI(
    title=API_TITLE, 
    version=API_VERSION)

SQLITE_DB_PATH=os.getenv("DB_PATH")

# app webhook validation - OPTION
# Allow all origins
# allow all http methods
# allow all header
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],)


# app health check
@app.get("/status")
async def status():
    return {
        "status": "running", 
        "message": "Movie Recommender System API is up & running!"}


# app version check endpoint
@app.get("/version")
async def version():
    logging.info(f"Version endpoint called")
    return {
        "version": API_VERSION, 
        "title": API_TITLE}


# # decorator to get the movielens db stats
# @app.get("/db/stats")
# def read_db_stats():
#     """GET endpoint to fetch database stats."""
#     return db_select.get_sqlite_movielens_stats(db_file_path=os.getenv("DB_PATH"))


# # decorator to insert data into movielens DB
# @app.get("/db/insertion")
# def movies_ratings_ingestor():
#     """GET endpoint to insert data into SQLITE DB."""
#     logging.info(f"Started to load the data into for DB insertion..")
#     movies_df, ratings_df = data_loader.load_movielens_data(data_folder_path=os.getenv("MOVIELENS_DATA_PATH"))
#     logging.info(f"Started to insert the data..")
#     ingester_summary = sqlite_ingestor.insert_movies_and_ratings_into_sqlite(
#         movies_df, 
#         ratings_df)
#     logging.info(f"Successfully inserted the data.")
#     return ingester_summary


# @app.get("/db/genres")
# def genres_ingestor():
#     return sqlite_ingestor.create_genres_tbl(db_file_path=SQLITE_DB_PATH)


# @app.get("/db/movie-rating-stats")
# def rating_stats_ingestor():
#     return sqlite_ingestor.create_movie_rating_stats_tbl(db_file_path=SQLITE_DB_PATH)


app.include_router(movielens_sqlite_data_ingestor, prefix="/api")
app.include_router(movielens_query_processor, prefix="/api")
app.include_router(movielens_query_responder, prefix="/api")