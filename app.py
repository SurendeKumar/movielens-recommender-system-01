import os
import json
import logging
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException
from movie_reccommender_system.db import db_select
# initiate the load_dotenv
load_dotenv()

# basic logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)

#  define sqlite db path 
DB_PATH="./movie_reccommender_system/db/movies.db"

# initiate the app 
API_VERSION="1.0.0"
API_TITLE="Advance Movie Recommender System"
app = FastAPI(
    title=API_TITLE, 
    version=API_VERSION)

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

# decorator to get the movielens db stats
@app.get("/db/stats")
def read_db_stats():
    """GET endpoint to fetch database stats."""
    return db_select.get_sqlite_movielens_stats(DB_PATH)