"""" DB Test Scripts"""
import sqlite3
import pandas as pd
from typing import Dict

# DB sanity check - to get the movielens stats using sqlite DB
def get_sqlite_movielens_stats(db_file_path: str) -> Dict:
    """Function to connect to a SQLite database and return simple stats.
        This function reports:
        - how many movies are in the movies table
        - how many ratings are in the ratings table
        - which rating score is most common (1–5)
        - which movie is most rated (id, title, count)

    Args
        db_file_path (str): Path to the SQLite database file.

    Returns: 
        Dict: Dictionary with database stats - 
            {
                "movie_count": int,
                "rating_count": int,
                "most_common_rating": {"score": int, "count": int},
                "most_rated_movie": {"id": int, "title": str, "count": int}
            }
    """
    # open a connection to the SQLite database
    conn = sqlite3.connect(db_file_path)

    try:
        # initiate the cursor
        cur = conn.cursor()

        # define the total count - COUNT
        cur.execute("SELECT COUNT(*) FROM movies;")
        movie_count = int(cur.fetchone()[0])

        # define the total ratings
        cur.execute("SELECT COUNT(*) FROM ratings;")
        rating_count = int(cur.fetchone()[0])

        # select the most common rating
        cur.execute("""
            SELECT rating, COUNT(*) as c
            FROM ratings
            GROUP BY rating
            ORDER BY c DESC
            LIMIT 1;""")
        # cursor to fetch single row
        row = cur.fetchone()
        # get the most common rating
        most_common_rating = {"score": int(row[0]), "count": int(row[1])} if row else {}

        # select most common rating
        cur.execute("""
            SELECT r.movie_id, m.title, COUNT(*) as c
            FROM ratings r
            JOIN movies m ON m.movie_id = r.movie_id
            GROUP BY r.movie_id
            ORDER BY c DESC
            LIMIT 1;""")
        # cursor to fetch single row
        row = cur.fetchone()
        # get most rating movie
        most_rated_movie = {
            "id": int(row[0]),
            "title": row[1],
            "count": int(row[2]),} if row else {}

        # return all stats in a dictionary
        return {
            "movie_count": movie_count,
            "rating_count": rating_count,
            "most_common_rating": most_common_rating,
            "most_rated_movie": most_rated_movie,}

    finally:
        conn.close()