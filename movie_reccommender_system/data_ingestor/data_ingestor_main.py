""" Ingestor Class to run MovieLens ingestion in order.

Class handles: 
    - Loads raw files (u.item and u.data)
    - Inserts movies and ratings into SQLite
    - Builds genres and movie_genres tables
    - Computes avg_rating and num_ratings per movie
    - Can run steps individually or all at once
    - Returns small dicts suitable for API responses
"""
import os
import logging
from typing import Dict
import pandas as pd
from movie_reccommender_system.data_ingestor import data_loader, db_ingestor

# set up basic logging once
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s")
# define single logger
logger = logging.getLogger("ingestion_service")


# movie lens ingestion class
class MovieLensSqliteIngestor:
    """Class to coordinate ingestion steps.

    Methods:
      - run_insert_only(): only insert movies and ratings
      - run_genres_only(): only build genres and movie_genres
      - run_movie_stats_only(): only compute avg_rating and num_ratings
      - run_all(): run all three in order with checks
      - get_db_stats(): quick sanity stats from DB (optional helper)
    """

    # initiate the data, db file paths
    def __init__(
            self, 
            data_folder_path: str, 
            db_file_path: str, 
            chunk_size: int = 5000):
        """Function to instantiate the objects to save the paths and chunk settings.

        Args
            data_folder_path (str): Folder that contains 'u.item' and 'u.data'.
            db_file_path (str): Path to the SQLite database file.
            chunk_size (int): Batch size used for bulk inserts. Larger is faster, but uses more memory.
        """
        # define self variables - data folder, db file path and chunk size
        self.data_folder_path = data_folder_path
        self.db_file_path = db_file_path
        self.chunk_size = chunk_size


    # insertion step
    def run_movielens_data_insertion(self):
        """Function to load u.item and u.data, then insert into SQLite.

        Returns: 
            Dict
                {
                "status": "success",
                "message": "...",
                "movie_rows": 1682,
                "rating_rows": 100000
                }
        """
        logger.info("Loading raw files and inserting movies + ratings")
        # initiate load_movielens_data() -  load raw MovieLens files into DataFrames
        movies_df, ratings_df = data_loader.load_movielens_data(self.data_folder_path)
        # initiate  insert_movies_and_ratings_into_sqlite() - insert both tables into SQLite using indexes for fast queries
        result = db_ingestor.insert_movies_and_ratings_into_sqlite(
            movies_df=movies_df,
            ratings_df=ratings_df,
            db_file_path=self.db_file_path,
            chunk_size=self.chunk_size)

        return result


    # normalise genres
    def run_genres_insertion(self):
        """Function to build 'genres' and 'movie_genres' by reading genre flags from movies.

        Returns
            Dict:
                {
                "success": true,
                "message": "...",
                "genre_count": 19,
                "movie_genre_links": 2890
                }
        """
        logger.info("Creating genres and movie_genres tables..")
        # initiate create_genres_tbl() - to create the genres table
        result = db_ingestor.create_genres_tbl(db_file_path=self.db_file_path)

        return result


    # collect movies and ratings stats
    def run_movie_ratings_stats_insertion(self):
        """Function to compute avg_rating and num_ratings per movie, update the movies table.

        Returns:
            Dict:
                {
                "success": true,
                "message": "...",
                "updated_movies": 1682
                }
        """
        logger.info("Computing avg_rating and num_ratings..")
        # initiaite create_movie_rating_stats_tbl() to create the movie rating stats tbl
        result = db_ingestor.create_movie_rating_stats_tbl(db_file_path=self.db_file_path)

        return result


    # run all steps in the correct order with simple checks
    def run_data_ingestor(self):
        """Function to wrap all ingestion services in order:
            1) insert movies and ratings
            2) build genres and movie_genres
            3) compute per-movie rating stats

        Returns: 
            Dict:
                {
                "success": true,
                "message": "All steps completed.",
                "steps": {
                    "insert_movielens": {...},
                    "genres_movie_ratings": {...},
                    "movie_rating_stats": {...}
                }}
        """
        # create a summary container
        ingestion_output_dict = {
            "success": False,
            "message": "",
            "steps": {
                "insert_movielens": None, 
                "genres_movie_ratings": None, 
                "movie_rating_stats": None},}

        # run the insert step first
        movielens_insertion_output = self.run_movielens_data_insertion()
        ingestion_output_dict["steps"]["insert_movielens"] = movielens_insertion_output
        # stop early if insert step failed
        if movielens_insertion_output.get("status") != "success":
            ingestion_output_dict["message"] = "Movielens insertion step failed. Stopping ingestion."
            return ingestion_output_dict

        # run the genres step next
        genres_ratings_output = self.run_genres_insertion()
        ingestion_output_dict["steps"]["genres_movie_ratings"] = genres_ratings_output
        # stop early if genres step failed
        if not genres_ratings_output.get("success", False):
            ingestion_output_dict["message"] = "Genres step failed. Stopping ingestion."
            return ingestion_output_dict

        # run the movie stats step last
        rating_stats_output= self.run_movie_ratings_stats_insertion()
        ingestion_output_dict["steps"]["movie_rating_stats"] = rating_stats_output
        # fail if stats failed
        if not rating_stats_output.get("success", False):
            ingestion_output_dict["message"] = "Movie stats step failed."
            return ingestion_output_dict

        # mark success if all three steps passed
        ingestion_output_dict["success"] = True
        ingestion_output_dict["message"] = "All steps completed."
        return ingestion_output_dict