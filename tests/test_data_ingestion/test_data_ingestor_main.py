""" Unittest TestSuite -> MovieLens Data Ingestor Main Workflow (Integration Test)"""
import os
import logging
import tempfile
import shutil
import unittest
from movie_reccommender_system.data_ingestor.data_ingestor_main import MovieLensSqliteIngestor
# define the basic config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# data loader  logger
logger = logging.getLogger("TestIngestorFlow")


# TestSuite -> Ingestor main workflow
class TestIngestorFlow(unittest.TestCase):
    """Integration tests for the full MovieLens ingestion workflow."""
    # setup before each test
    def setUp(self):
        """Create a temporary data folder and database, then build a small raw dataset."""
        logger.info(f"Setting up temporary folders, DB path, and raw files for ingestor flow.")
        # make a temp folder
        self.temp_dir = tempfile.mkdtemp()
        # set db path
        self.db_path = os.path.join(self.temp_dir, "movie.db")
        # set data folder
        self.data_dir = os.path.join(self.temp_dir, "data_raw")
        # make data folder
        os.makedirs(self.data_dir, exist_ok=True)
        # write movies file
        with open(os.path.join(self.data_dir, "u.item"), "w", encoding="latin-1") as f:
            f.write("1|Toy Story (1995)|01-Jan-1995||http://example.com|0|1|0|0|0|1|0|0|1|0|0|0|0|0|0|0|1|0|0\n")
            f.write("2|Jumanji (1995)|01-Jan-1995||http://example.com|0|0|1|0|0|1|0|0|1|0|0|0|0|0|0|0|1|0|0\n")
        # write ratings file
        with open(os.path.join(self.data_dir, "u.data"), "w", encoding="utf-8") as f:
            f.write("1\t1\t5\t874965758\n")
            f.write("2\t1\t4\t874965759\n")
            f.write("1\t2\t3\t874965760\n")
        # create ingestor
        self.ingestor = MovieLensSqliteIngestor(
            data_folder_path=self.data_dir,
            db_file_path=self.db_path,
            chunk_size=2)
        logger.info(f"Setup complete for ingestor workflow tests.")

    # remove the temp files after each test
    def removeTmpFiles(self):
        """Remove temporary folders and files after each test."""
        logger.info(f"Cleaning up ingestor flow temp folders and DB.")
        # remove temp folder
        shutil.rmtree(self.temp_dir)

    # test run insert only
    def test_run_movielens_data_insertion(self):
        """Verify that insert step loads raw files and inserts correct row counts."""
        logger.info(f"Running test_run_movielens_data_insertion.")
        out = self.ingestor.run_movielens_data_insertion()
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["movie_rows"], 2)
        self.assertEqual(out["rating_rows"], 3)
        logger.info("Successfully passed the movielens data insertion test.")

    # test run genres
    def test_run_genres_insertion(self):
        """Verify that genre normalization step succeeds after base insert."""
        logger.info(f"Running test_run_genres_insertion.")
        self.ingestor.run_movielens_data_insertion()
        out = self.ingestor.run_genres_insertion()
        self.assertTrue(out["success"])
        logger.info("Successfully passed the genres data insertion test.")


    # test run stats
    def test_run_movie_ratings_stats_insertion(self):
        """Verify that rating stats step succeeds after base insert."""
        logger.info(f"Running test_run_movie_ratings_stats_insertion.")
        self.ingestor.run_movielens_data_insertion()
        out = self.ingestor.run_movie_ratings_stats_insertion()
        self.assertTrue(out["success"])
        logger.info(f"Succesfully passed the rating stats data insertion test.")

    # test full pipeline
    def test_run_data_ingestor(self):
        """Verify that the full pipeline runs all steps and returns success with step outputs."""
        logger.info(f"Running test_run_data_ingestor (full pipeline).")
        out = self.ingestor.run_data_ingestor()
        self.assertTrue(out["success"])
        self.assertIn("insert_movielens", out["steps"])
        self.assertIn("genres_movie_ratings", out["steps"])
        self.assertIn("movie_rating_stats", out["steps"])
        logger.info(f"Successfully passed the integration workflow after all execution test.")



# if __name__ == "__main__":
#     unittest.main(verbosity=2)

    ## cli cmd
    # python -m unittest tests/test_data_ingestion\test_data_ingestor_main.py
