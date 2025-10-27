""" Unittest TestSuite -> MovieLens Data Loader"""
import os
import logging
import tempfile
import shutil
import unittest
import pandas as pd
from movie_reccommender_system.data_ingestor import data_loader
# define the basic config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# data loader  logger
logger = logging.getLogger("TestLoadMovieLensData")


# TestSuite - MovieLensData
class TestLoadMovieLensData(unittest.TestCase):
    """TestSuite for loading and exploring MovieLens data."""
    # setup function runs before each test
    def setUp(self):
        """ Prepare temporary files before each test. """
        logger.info(f"Setting up temporary MovieLens test files.")
        # make a temporary folder
        self.temp_dir = tempfile.mkdtemp()
        # set movies file path
        self.movies_path = os.path.join(self.temp_dir, "u.item")
        # set ratings file path
        self.ratings_path = os.path.join(self.temp_dir, "u.data")
        # open movies file to write
        with open(self.movies_path, "w", encoding="latin-1") as f:
            # write two movie rows with full 24 fields
            f.write("1|Toy Story (1995)|01-Jan-1995||http://example.com|0|1|0|0|0|1|0|0|1|0|0|0|0|0|0|0|1|0|0\n")
            f.write("2|Jumanji (1995)|01-Jan-1995||http://example.com|0|0|1|0|0|1|0|0|1|0|0|0|0|0|0|0|1|0|0\n")
        # open ratings file to write
        with open(self.ratings_path, "w", encoding="utf-8") as f:
            # write three rating rows
            f.write("1\t1\t5\t874965758\n")
            f.write("2\t1\t4\t874965759\n")
            f.write("1\t2\t3\t874965760\n")

    # remove temporary files after each tests 
    def removeTmpFiles(self):
        """Remove temporary files after each tests."""
        logger.info(f"Cleanning up temporary MovieLens test files.")
        # remove the temp folder
        shutil.rmtree(self.temp_dir)

    # test for load_movielens_data
    def test_load_files_ok(self):
        """Test that MovieLens data loads correctly from raw files."""
        logger.info(f"Loading the files after data loader..")
        # call loader
        movies_df, ratings_df = data_loader.load_movielens_data(self.temp_dir)
        # check movies count
        self.assertEqual(len(movies_df), 2)
        # check ratings count
        self.assertEqual(len(ratings_df), 3)
        # check movie title column exists
        self.assertIn("title", movies_df.columns)
        # check genre column exists
        self.assertIn("Comedy", movies_df.columns)
        logger.info("Files loaded succussfully, Test Passed.")


    # test for eda_movies
    def test_eda_movies(self):
        """Test EDA function on movies dataframe."""
        logger.info(f"Loading the data for basic EDA for movies exploration.")
        # load movies only
        movies_df, _ = data_loader.load_movielens_data(self.temp_dir)
        # run eda
        out = data_loader.eda_movies(movies_df)
        # check total movies count
        self.assertEqual(out["total_movies"], 2)
        # check genre counts is dict
        self.assertIsInstance(out["genre_counts"], dict)
        logger.info(f"Movies EDA passed.")


    # test for eda_ratings
    def test_eda_ratings(self):
        """Test EDA function on ratings dataframe."""
        logger.info(f"Loading the data for movies rating exploration.")
        # load both data
        movies_df, ratings_df = data_loader.load_movielens_data(self.temp_dir)
        # run eda
        out = data_loader.eda_ratings(ratings_df, movies_df)
        # check ratings count
        self.assertEqual(out["total_ratings"], 3)
        # check common rating key
        self.assertIn("most_common_rating", out)
        # check most rated movie key
        self.assertIn("most_rated_movie", out)
        logger.info("Movies Rating EDA Test passed.")


# if __name__ == "__main__":
#     unittest.main(verbosity=2)

    ## cli cmd
    # python -m unittest tests/test_data_ingestion\test_data_loader.py