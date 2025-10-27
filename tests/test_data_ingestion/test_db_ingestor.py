""" Unittest TestSuite -> MovieLens SQLITEDB Ingestor"""
import os
import logging
import tempfile
import shutil
import sqlite3
import unittest
import pandas as pd
from movie_reccommender_system.data_ingestor import db_ingestor
# define the basic config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# data loader  logger
logger = logging.getLogger("TestSqliteInserts")

# TestSuite - MovieLens Data ingestion into SQLITE DB
class TestSqliteInserts(unittest.TestCase):
    """Create a temporary DB and small dataframes for each test."""
    # setup before each test
    def setUp(self):
        """ Prepare temporary files before each test. """
        logger.info(f"Setting up temporary SQLite DB and sample DataFrames.")
        # make a temp folder
        self.temp_dir = tempfile.mkdtemp()
        # set db path
        self.db_path = os.path.join(self.temp_dir, "movie.db")
        # make sample movies dataframe
        self.movies_df = pd.DataFrame([
            [1, "Toy Story (1995)", "01-Jan-1995", None, "http://example.com"] + [0,1,0,0,0,1,0,0,1,0,0,0,0,0,0,0,1,0,0],
            [2, "Jumanji (1995)", "01-Jan-1995", None, "http://example.com"] + [0,0,1,0,0,1,0,0,1,0,0,0,0,0,0,0,1,0,0],])
        # set columns for movies dataframe
        self.movies_df.columns = [
            "movie_id","title","release_date","video_release_date","imdb_url","unknown","Action","Adventure","Animation",
            "Children","Comedy","Crime","Documentary","Drama","Fantasy","Film-Noir","Horror","Musical","Mystery",
            "Romance","Sci-Fi","Thriller","War","Western"]
        # make ratings dataframe
        self.ratings_df = pd.DataFrame([
            [1,1,5,874965758],
            [2,1,4,874965759],
            [1,2,3,874965760],
        ], columns=["user_id","movie_id","rating","unix_time"])

    # remove temporary files after each tests 
    def removeTmpFiles(self):
        """Remove temporary DB and folder after each test."""
        logger.info("Cleaning up temporary SQLite DB and files.")
        # remove temp folder
        shutil.rmtree(self.temp_dir)


    # test insert into sqlite
    def test_insert_movies_and_ratings(self):
        """Verify movies and ratings are inserted and counted correctly."""
        logger.info("Running test_insert_movies_and_ratings..")
        # call insert
        out = db_ingestor.insert_movies_and_ratings_into_sqlite(
            movies_df=self.movies_df,
            ratings_df=self.ratings_df,
            db_file_path=self.db_path,
            chunk_size=2)
        # check status
        self.assertEqual(out["status"], "success")
        # check movie rows
        self.assertEqual(out["movie_rows"], 2)
        # check rating rows
        self.assertEqual(out["rating_rows"], 3)
        # open db
        with sqlite3.connect(self.db_path) as con:
            # count movies
            count_1 = con.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            # count ratings
            count_2 = con.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
        # assert counts match
        self.assertEqual(count_1, 2)
        self.assertEqual(count_2, 3)
        logger.info("Successfully passed the DB insertion test.")


    # test create genres table
    def test_create_genres_tbl(self):
        """Verify genres and movie_genres tables are created and populated."""
        logger.info("Running test_create_genres_tbl.")
        # insert base tables
        db_ingestor.insert_movies_and_ratings_into_sqlite(
            self.movies_df, self.ratings_df, self.db_path, chunk_size=10)
        # call create genres
        out = db_ingestor.create_genres_tbl(self.db_path)
        # check success
        self.assertTrue(out["success"])
        # check genre count
        self.assertGreater(out["genre_count"], 0)
        # check movie links
        self.assertGreater(out["movie_genre_links"], 0)
        logger.info("Successfully passed the Genres table creation test.")


    # test create movie rating stats
    def test_create_movie_rating_stats_tbl(self):
        """Verify avg_rating and num_ratings are computed and updated in movies."""
        logger.info("Running test_create_movie_rating_stats_tbl.")
        # insert base tables
        db_ingestor.insert_movies_and_ratings_into_sqlite(
            self.movies_df, self.ratings_df, self.db_path, chunk_size=10)
        # call create stats
        out = db_ingestor.create_movie_rating_stats_tbl(self.db_path)
        # check success
        self.assertTrue(out["success"])
        # open db
        with sqlite3.connect(self.db_path) as con:
            # count updated movies
            cupdate_count = con.execute("SELECT COUNT(*) FROM movies WHERE num_ratings IS NOT NULL").fetchone()[0]
        # assert matches
        self.assertEqual(out["updated_movies"], cupdate_count)
        self.assertGreaterEqual(cupdate_count, 1)
        logger.info("Successfully passed the movie's ratings stat table creation test.")



# if __name__ == "__main__":
#     unittest.main(verbosity=2)

    ## cli cmd
    # python -m unittest tests/test_data_ingestion\test_db_ingestor.py