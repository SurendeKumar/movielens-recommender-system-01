""" Unittest TestSuite -> MovieLens Query Processor integration workflow """
import os
import sqlite3
import tempfile
import shutil
import unittest
import logging
from types import SimpleNamespace
from movie_reccommender_system.query_processor.query_processor_main import MovielensQueryProcessor
# set up logging for this test file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TestQueryProcessorMain")


# TestSuite - Query Processor integration workflow 
class TestQueryProcessorMain(unittest.TestCase):
    """Integration tests for MovielensQueryProcessor against a temp SQLite DB."""
    # setup before each test 
    def setUp(self):
        """Create a temporary SQLite DB with minimal schema and seed data."""
        logger.info(f"Setting up temporary SQLite DB with seed data")
        # create temp directory
        self.temp_dir = tempfile.mkdtemp()
        # define db path
        self.db_path = os.path.join(self.temp_dir, "movie.db")
        # open connection
        conn = sqlite3.connect(self.db_path)
        # create cursor
        cur = conn.cursor()
        # create movies table
        cur.execute("""
            CREATE TABLE movies (
                movie_id INTEGER PRIMARY KEY,
                title TEXT,
                release_date TEXT,
                avg_rating REAL,
                num_ratings INTEGER
            );""")
        # create genres table
        cur.execute("""
            CREATE TABLE genres (
                genre_id INTEGER PRIMARY KEY,
                genre_name TEXT UNIQUE
            );""")
        # create movie_genres table
        cur.execute("""
            CREATE TABLE movie_genres (
                movie_id INTEGER,
                genre_id INTEGER,
                PRIMARY KEY (movie_id, genre_id)
            );""")
        # create ratings table
        cur.execute("""
            CREATE TABLE ratings (
                user_id INTEGER,
                movie_id INTEGER,
                rating INTEGER,
                unix_time INTEGER
            );""")
        # insert movies
        cur.executemany(
            "INSERT INTO movies(movie_id, title, release_date, avg_rating, num_ratings) VALUES (?, ?, ?, ?, ?);",
            [
                (1, "Toy Story (1995)", "01-Jan-1995", 4.1, 900),
                (2, "Jumanji (1995)", "01-Jan-1995", 3.8, 500),
                (3, "Interstellar (2014)", "07-Nov-2014", 4.6, 1200),
                (4, "Drama Piece (2012)", "01-Jan-2012", 4.2, 300),
            ],)
        # insert genres
        cur.executemany(
            "INSERT INTO genres(genre_id, genre_name) VALUES (?, ?);",
            [
                (1, "Comedy"),
                (2, "Drama"),
                (3, "Sci-Fi"),
            ],)
        # insert movie_genres
        cur.executemany(
            "INSERT INTO movie_genres(movie_id, genre_id) VALUES (?, ?);",
            [
                (1, 1),
                (2, 1),
                (3, 3),
                (4, 2),
            ],)
        # insert ratings
        cur.executemany(
            "INSERT INTO ratings(user_id, movie_id, rating, unix_time) VALUES (?, ?, ?, ?);",
            [
                (1, 1, 5, 1000),
                (2, 1, 4, 1001),
                (1, 3, 5, 1002),
                (3, 4, 4, 1003),
            ],)
        # commit changes
        conn.commit()
        # close connection
        conn.close()
        # create processor
        self.processor = MovielensQueryProcessor(db_file_path=self.db_path)
        # log end of setup
        logger.info("Temporary DB ready for tests")

    # remove temporary files after each tests 
    def removeTmpFiles(self):
        """Remove temporary files after each tests."""
        logger.info(f"Cleaning up temporary DB")
        # remove temp dir
        shutil.rmtree(self.temp_dir)

    # test - movies details
    def test_run_get_movie_details(self):
        """Test detail lookup by title like search."""
        logger.info(f"Running test_run_get_movie_details")
        # build parsed object
        parsed = SimpleNamespace(intent="GET_DETAILS", title="Toy Story", top_n=5)
        # call method
        rows = self.processor.run_get_movie_details(parsed, limit=5)
        # assert non empty
        self.assertGreaterEqual(len(rows), 1)
        # assert title contains
        self.assertTrue(any("Toy Story" in r.title for r in rows))

    # test - reccommend movie by genres
    def test_run_recommend_movie_by_filter_genre(self):
        """Test recommend by single genre filter."""
        logger.info(f"Running test_run_recommend_movie_by_filter_genre")
        # build parsed object
        parsed = SimpleNamespace(
            intent="RECOMMEND_BY_FILTER", 
            genres=["Comedy"], 
            year=None, 
            year_from=None, 
            year_to=None, 
            min_rating=None, 
            top_n=10, 
            rating_compare=None)
        # call method
        rows = self.processor.run_recommend_movie_by_filter(parsed, limit=10)
        # assert some results
        self.assertGreaterEqual(len(rows), 1)
        # assert titles are present
        self.assertTrue(all(hasattr(r, "title") for r in rows))

    # test - recommend moview by year and min rating
    def test_run_recommend_movie_by_filter_year_and_min_rating(self):
        """Test recommend filtered by year range and min rating greater than or equal."""
        logger.info(f"Running test_run_recommend_movie_by_filter_year_and_min_rating")
        # build parsed object
        parsed = SimpleNamespace(
            intent="RECOMMEND_BY_FILTER", 
            genres=[],
            year=None, 
            year_from=2010, 
            year_to=2015, 
            min_rating=4.0, 
            top_n=10, 
            rating_compare="greater_than_or_equal")
        # call method
        rows = self.processor.run_recommend_movie_by_filter(parsed, limit=10)
        # assert interstellar or drama piece appears
        self.assertTrue(any(r.title.startswith("Interstellar") or r.title.startswith("Drama Piece") for r in rows))


    # test - run top N queries
    def test_run_top_n_query(self):
        """Test top n query path delegates to recommend with limit from parsed."""
        logger.info(f"Running test_run_top_n_query")
        # build parsed object
        parsed = SimpleNamespace(
            intent="TOP_N", 
            genres=["Sci-Fi"], 
            year=None, 
            year_from=None,
            year_to=None, 
            min_rating=None, 
            top_n=1, 
            rating_compare=None)
        # call method
        rows = self.processor.run_top_n_query(parsed)
        # assert exactly one row
        self.assertEqual(len(rows), 1)
        # assert sci-fi title present
        self.assertTrue(any("Interstellar" in r.title for r in rows))

    # run similar movies by genre
    def test_run_similar_movie_genres(self):
        """Test similar movies by shared genres."""
        logger.info(f"Running test_run_similar_movie_genres")
        # build parsed object
        parsed = SimpleNamespace(
            intent="SIMILAR_MOVIES", 
            title="Toy Story", 
            top_n=5)
        # call method
        rows = self.processor.run_similar_movie_genres(parsed, limit=5)
        # assert jumanji may appear since both are comedy
        self.assertTrue(any("Jumanji" in r.title for r in rows))

    # main dispatcher 
    def test_query_executor_dispatch(self):
        """Test the dispatcher routes to correct method and handles unknown intent."""
        logger.info(f"Running test_query_executor_dispatch")
        # build detail case
        p1 = SimpleNamespace(
            intent="GET_DETAILS", 
            title="Toy Story", 
            top_n=5)
        # call dispatcher
        r1 = self.processor.query_excutor(p1, limit=5)
        # assert non empty
        self.assertGreaterEqual(len(r1), 1)
        # build unknown case
        p2 = SimpleNamespace(intent="UNKNOWN")
        # call dispatcher
        r2 = self.processor.query_excutor(p2, limit=5)
        # assert empty
        self.assertEqual(len(r2), 0)

    # test - query dispatcher > output handler
    def test_query_executor_output_handler(self):
        """Test output handler packs normalized dict and raw results."""
        logger.info(f"Running test_query_executor_output_handler")
        # build filter case
        parsed = SimpleNamespace(
            intent="RECOMMEND_BY_FILTER", 
            genres=["Drama"], 
            year=None,
            year_from=2010, 
            year_to=2020, 
            min_rating=3.5, 
            top_n=3, 
            rating_compare="greater_than_or_equal",)
        # call output handler
        packed, raw = self.processor.query_executor_output_handler(parsed, limit=3)
        # assert intent in packed
        self.assertEqual(packed["intent"], "RECOMMEND_BY_FILTER")
        # assert results have expected keys
        self.assertTrue(all({
            "movieId",
            "title",
            "year",
            "avg_rating",
            "num_ratings",
            "genres"} <= set(row.keys()) for row in packed["results"]))
        # assert raw is list
        self.assertIsInstance(raw, list)


# if __name__ == "__main__":
#     # run the tests with verbosity 2
#     unittest.main(verbosity=2)

    ## cli cmd
    # python -m unittest tests/test_data_ingestion\test_data_loader.py
