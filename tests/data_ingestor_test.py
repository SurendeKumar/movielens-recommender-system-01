# # tests/test_ingestor_flow.py
# import sqlite3
# import math
# import pandas as pd
# import numpy as np
# import pytest
# from movie_reccommender_system.data_ingestor.data_ingestor_main import MovieLensSqliteIngestor


# # test - if movielens is a type of DataFrame
# def test_sample_movies_df():
#     """Funciton to make a tiny movies dataframe with the correct 24 columns"""
#     # columns used into dataframe
#     cols = [
#         "movie_id", "title", "release_date", "video_release_date", "imdb_url",
#         "unknown", "Action", "Adventure", "Animation", "Children", "Comedy", "Crime",
#         "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "Musical",
#         "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western",]
    
#     # return dataframe
#     assert pd.DataFrame([{
#         "movie_id": 1,
#         "title": "Toy Story (1995)",
#         "release_date": "01-Jan-1995",
#         "video_release_date": None,
#         "imdb_url": np.nan,   # tests NaN -> NULL
#         "unknown": 0,
#         "Action": 1,
#         "Adventure": 1,
#         "Animation": 1,
#         "Children": 1,
#         "Comedy": 1,
#         "Crime": 0,
#         "Documentary": 0,
#         "Drama": 0,
#         "Fantasy": 0,
#         "Film-Noir": 0,
#         "Horror": 0,
#         "Musical": 0,
#         "Mystery": 0,
#         "Romance": 0,
#         "Sci-Fi": 0,
#         "Thriller": 0,
#         "War": 0,
#         "Western": 0,
#     }], columns=cols)


# # test - ratings dataframe
# def test_sample_ratings_df():
#     """Function to make a tiny ratings dataframe for one movie with two ratings"""
#     # return dataframe
#     assert pd.DataFrame([
#         {"user_id": 10, "movie_id": 1, "rating": 4, "unix_time": 1000},
#         {"user_id": 11, "movie_id": 1, "rating": 5, "unix_time": 1001},
#     ], columns=["user_id", "movie_id", "rating", "unix_time"])


# # test db file paths for insertion
# def test_all_files_path(
#         tmp_path, 
#         monkeypatch):
#     """Test function to run the whole flow and check the key things
#     - tables exist and have correct row counts
#     - NaN in movies becomes NULL in sqlite
#     - genre tables are built and have links
#     - movie stats are computed (avg=4.5, count=2)
#     - indexes exist for speed
#     - the return dict from the orchestrator is marked success

#     Args:
#         tmp_path (str): db file temporary path. 
#         monkeypatch (obj): pytest patcher object to return fake dataframe

#     """
#     # make the db file path using temporary path
#     db_file = tmp_path / "movies.db"

#     # stub the raw loader to avoid real files
#     def fake_load_movielens_data(_):
#         return test_sample_movies_df(), test_sample_ratings_df()

#     # 
#     monkeypatch.setattr(
#         "movie_reccommender_system.data_ingestor.data_loader.load_movielens_data",
#         fake_load_movielens_data,)

#     # run everything through the class
#     ingestor = MovieLensSqliteIngestor(
#         data_folder_path="not_used_here",
#         db_file_path=str(db_file),
#         chunk_size=2,)
    
#     # run data ingestor
#     result = ingestor.run_data_ingestor()

#     # check the high-level response
#     assert result["success"] is True
#     assert result["message"] == "All steps completed."
#     assert result["steps"]["insert_movielens"]["status"] == "success"
#     assert result["steps"]["genres_movie_ratings"]["success"] is True
#     assert result["steps"]["movie_rating_stats"]["success"] is True

#     # check the database details
#     con = sqlite3.connect(str(db_file))
#     try:
#         # tables exist
#         tables = {r[0] for r in con.execute(
#             "SELECT name FROM sqlite_master WHERE type='table'")}
#         assert {"movies", "ratings", "genres", "movie_genres"} <= tables

#         # row counts correct
#         assert con.execute("SELECT COUNT(*) FROM movies").fetchone()[0] == 1
#         assert con.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == 2

#         # NaN -> NULL worked
#         assert con.execute(
#             "SELECT imdb_url FROM movies WHERE movie_id=1").fetchone()[0] is None

#         # genres created and links present
#         assert con.execute("SELECT COUNT(*) FROM genres").fetchone()[0] == 19
#         assert con.execute("SELECT COUNT(*) FROM movie_genres").fetchone()[0] >= 1

#         # stats computed
#         avg_rating, num_ratings = con.execute(
#             "SELECT avg_rating, num_ratings FROM movies WHERE movie_id=1"
#         ).fetchone()
#         assert math.isclose(avg_rating, 4.5, rel_tol=1e-9)
#         assert num_ratings == 2

#         # helpful indexes exist
#         idx_movies = {r[1] for r in con.execute("PRAGMA index_list('movies')")}
#         idx_ratings = {r[1] for r in con.execute("PRAGMA index_list('ratings')")}
#         assert "idx_movies_title" in idx_movies
#         assert "idx_ratings_movie" in idx_ratings
#         assert "idx_ratings_user" in idx_ratings
#     finally:
#         con.close()


# # stop process when insertion is completed
# def test_stop_when_insert_fails(
#         tmp_path, 
#         monkeypatch):
#     """Test function to make the first step return an error and confirm the class stops
#     - insert step returns {"status": "error"}
#     - run_data_ingestor() should mark success=False and skip later steps
#     - later step payloads should be None

#     Args:
#         tmp_path (str): db file temporary path. 
#         monkeypatch (obj): pytest patcher object to return fake dataframe
#     """
#     db_file = tmp_path / "movies.db"

#     # stub loader (not used in failure flow but fine to keep)
#     monkeypatch.setattr(
#         "movie_reccommender_system.data_ingestor.data_loader.load_movielens_data",
#         lambda _: (test_sample_movies_df(), test_sample_ratings_df()),)

#     # force the insert step to "fail" per your function contract
#     monkeypatch.setattr(
#         "movie_reccommender_system.data_ingestor.db_ingestor.insert_movies_and_ratings_into_sqlite",
#         lambda **kwargs: {"status": "error", "message": "insert failed"},)

#     # initiate the sqlite ingestor class
#     ingestor = MovieLensSqliteIngestor(
#         data_folder_path="not_used",
#         db_file_path=str(db_file),
#         chunk_size=2,)
    
#     # run data igenstor
#     out = ingestor.run_data_ingestor()

#     assert out["success"] is False
#     assert "insertion step failed" in out["message"].lower()
#     assert out["steps"]["insert_movielens"] == {"status": "error", "message": "insert failed"}
#     assert out["steps"]["genres_movie_ratings"] is None
#     assert out["steps"]["movie_rating_stats"] is None
