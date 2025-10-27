import os
import json
import logging
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, HTTPException
# from movie_reccommender_system.db import db_select
# from movie_reccommender_system.data_ingestor import sqlite_ingestor, data_loader
from router.query_response_router import router as movielens_response_router

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


# initiate the movielens response router
app.include_router(movielens_response_router, prefix="/api")