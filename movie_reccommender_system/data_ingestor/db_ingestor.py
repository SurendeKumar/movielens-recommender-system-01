""" SQLITE data ingestor """
import os         
import sqlite3    
import logging    
from typing import Dict  
import pandas as pd 
from movie_reccommender_system.data_ingestor import data_loader

# define basic config
logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# loger as liner
logger = logging.getLogger("sqlite_inserter")  


# insert data into DB 
def insert_movies_and_ratings_into_sqlite(
    movies_df: pd.DataFrame,
    ratings_df: pd.DataFrame,
    db_file_path: str = "movie_reccommender_system/db/movies.db",
    chunk_size: int = 5000):
    """Function to insert MovieLens data frames into a SQLite database.
        Function:
        1) opens (or creates) the database file,
        2) tunes PRAGMAs for faster bulk insert,
        3) creates the tables with a fixed schema,
        4) inserts rows in chunks for speed,
        5) builds useful indexes,
        6) returns row counts for tests.

    Args
        movies_df (pandas.DataFrame): Data frame with ALL 24 MovieLens movie columns.
        ratings_df : pandas.DataFrame
            Data frame with columns (user_id, movie_id, rating, unix_time).
        db_file_path : str
            Path for the SQLite database file (it will be created if missing).
        chunk_size : int
            How many rows to send per batch insert (bigger is faster, but uses more memory).

    Returns:
        Dict[str, int] Dictionary with row counts:
            {"movie_rows": <int>, "rating_rows": <int>}
    """
    # make sure the folder for the database file exists
    os.makedirs(os.path.dirname(db_file_path), exist_ok=True) 

    # open a connection to the SQLite file
    with sqlite3.connect(db_file_path) as db:
        # tune SQLite to be faster for bulk inserts
        # use write-ahead logging
        db.execute("PRAGMA journal_mode=WAL;")    
        # fewer fsyncs during bulk writes
        db.execute("PRAGMA synchronous=NORMAL;")  
         # keep foreign keys checks on
        db.execute("PRAGMA foreign_keys=ON;")    

        # create fresh tables so schema is always correct
        logger.info("Creating tables 'movies' and 'ratings'...")
        # make both tables from scratch
        create_movies_ratings_tbl(db) 

        # prepare SQL for inserting into the movies table
        movies_sql = """
            INSERT INTO movies (
                movie_id, title, release_date, video_release_date, imdb_url,
                unknown, Action, Adventure, Animation, Children, Comedy, Crime,
                Documentary, Drama, Fantasy, "Film-Noir", Horror, Musical,
                Mystery, Romance, "Sci-Fi", Thriller, War, Western
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""

        # turn the movies data frame into an iterator of pure Python tuples
        # convert NaN to None for each value
        movies_rows = (
            tuple(change_none_if_nan(v) for v in row)  
            for row in movies_df.itertuples(index=False, name=None))  

        # insert the movies in chunks for speed and low memory
        logger.info(f"Inserting movies in chunks of rows: {chunk_size}")  
        # keep a running count
        total_movie_rows = 0               
        # get next batch           
        for chunk in split_into_chunks(movies_rows, chunk_size): 
            # insert the whole batch at once 
            db.executemany(movies_sql, chunk)         
            # add how many we just inserted  
            total_movie_rows += len(chunk)              

        # prepare SQL for inserting into the ratings table
        ratings_sql = """
            INSERT INTO ratings (user_id, movie_id, rating, unix_time)
            VALUES (?, ?, ?, ?);"""

        # turn the ratings data frame into an iterator of pure Python tuples
        # convert NaN to None for each value
        ratings_rows = (
            tuple(change_none_if_nan(v) for v in row)   
            for row in ratings_df.itertuples(index=False, name=None) )

        # insert the ratings in chunks
        logger.info(f"Inserting ratings in chunks of rows: {chunk_size}")
        # keep a running count
        total_rating_rows = 0        
        # get next batch                   
        for chunk in split_into_chunks(ratings_rows, chunk_size):  
            # insert the whole batch at once
            db.executemany(ratings_sql, chunk) 
            # add how many we just inserted         
            total_rating_rows += len(chunk)             

        # create helpful indexes for faster queries later
        logger.info(f"Creating indexes for faster lookups...") 
        # find by title fast 
        db.execute(f"CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title);")   
        # find movie ratings fast   
        db.execute(f"CREATE INDEX IF NOT EXISTS idx_ratings_movie ON ratings(movie_id);") 
        # find user ratings fast
        db.execute(f"CREATE INDEX IF NOT EXISTS idx_ratings_user  ON ratings(user_id);")  

        # verify row counts with a simple SELECT (defensive check)
         # how many movies now in DB
        movie_count = db.execute("SELECT COUNT(*) FROM movies;").fetchone()[0]  
        # how many ratings now in DB
        rating_count = db.execute("SELECT COUNT(*) FROM ratings;").fetchone()[0] 

        # log final counts so we can see what happened
        logger.info(f"Inserted movies: {movie_count} and ratings: {rating_count}") 

        # return counts so tests can assert exact numbers
        return {
            "status":"success",
            "message":"Successfully inserting records.",
            "movie_rows": int(movie_count), 
            "rating_rows": int(rating_count)}  



# split data into chunks
def split_into_chunks(
        row_iterator, 
        chunk_size: int):
    """Function to split an iterator of rows into small lists of rows.
        This is to helps us send many rows to SQLite in one call
        (executemany), which is faster than one-by-one inserts.

    Args
        row_iterator: An iterator that gives us one row (tuple) at a time.
        chunk_size (int): size to define the how many rows to group together in each chunk.

    Yield: 
        list: A list of rows (each row is a tuple), up to chunk_size long.
    """
    # start with an empty list to collect rows
    chunk = [] 
    # go over each row that comes from the iterator
    for row in row_iterator: 
        # add the row into the current batch 
        chunk.append(row)    
        # if the batch is big enough, give it back to the caller - check if we reached the limit
        if len(chunk) >= chunk_size: 
            # send the batch to the caller
            yield chunk         
             # reset the batch for the next rows      
            chunk = []               
    # after the loop, if any rows are left, send them too
    if chunk:    
        # send the final, smaller batch       
        yield chunk    


# handle the NaNs
def change_none_if_nan(value):
    """Function to change a NaN (Not a Number) into None so SQLite stores NULL.

    Args
        value : The value to check.

    Returns:
        The same value if it is not missing, or None if it is missing.
    """
    # if the value is considered missing by pandas, return None
    if pd.isna(value): 
        return None     
    # otherwise return the value as-is
    return value       



# create the tables into sqlite
def create_movies_ratings_tbl(db_connection: sqlite3.Connection):
    """Function to create the 'movies' and 'ratings' tables with a fixed schema.

    Args
        db_connection (sqlite3.Connection): An open SQLite connection where tables should be created.

    Returns:
        None
    """
    # drop old movies table if it exists
    db_connection.execute("DROP TABLE IF EXISTS movies;")  # start clean
    # create a new movies table with 24 columns (MovieLens spec)
    db_connection.execute("""
        CREATE TABLE movies (
            movie_id INTEGER PRIMARY KEY,
            title TEXT,              
            release_date TEXT,                 
            video_release_date TEXT,            
            imdb_url TEXT,                
            unknown INTEGER,              
            Action INTEGER,
            Adventure INTEGER,
            Animation INTEGER,
            Children INTEGER,
            Comedy INTEGER,
            Crime INTEGER,
            Documentary INTEGER,
            Drama INTEGER,
            Fantasy INTEGER,
            "Film-Noir" INTEGER,
            Horror INTEGER,
            Musical INTEGER,
            Mystery INTEGER,
            Romance INTEGER,
            "Sci-Fi" INTEGER,
            Thriller INTEGER,
            War INTEGER,
            Western INTEGER);""")

    # drop old ratings table if it exists
    db_connection.execute("DROP TABLE IF EXISTS ratings;")
    # create a new ratings table for user ratings
    db_connection.execute("""
        CREATE TABLE ratings (
            user_id INTEGER, 
            movie_id INTEGER, 
            rating INTEGER,
            unix_time INTEGER );""")




# creating the genre table
def create_genres_tbl(db_file_path: str) -> Dict:
    """Function to create and fill the 'genres' and 'movie_genres' tables.

    Args:
        db_file_path (str): Path to the SQLite database file that already has a 'movies' table.

    Returns:
        Dict: Containing the success message and logs.
    """
    # list of genre column names as they appear in u.item
    genre_names= [
        "unknown", "Action", "Adventure", "Animation", "Children", "Comedy", "Crime",
        "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "Musical",
        "Mystery", "Romance", "Sci-Fi", "Thriller", "War", "Western"]

    # open a connection to the SQLite database file
    conn = sqlite3.connect(db_file_path)
    # create a cursor so we can run SQL commands
    cur = conn.cursor()

    try:
        # start a transaction so all changes apply together
        conn.execute("BEGIN")
        # drop the 'genres' table if it exists so we start clean
        cur.execute("DROP TABLE IF EXISTS genres;")
        # create the 'genres' table with an id and a unique name
        cur.execute("""
            CREATE TABLE genres (
                genre_id INTEGER PRIMARY KEY,
                genre_name TEXT UNIQUE);""")

        # insert each genre name as one row into the 'genres' table
        for name in genre_names:
            # insert or ignore so we do not fail if it already exists
            cur.execute("INSERT OR IGNORE INTO genres (genre_name) VALUES (?);", (name,))

        # drop the 'movie_genres' table if it exists so we start clean
        cur.execute("DROP TABLE IF EXISTS movie_genres;")
        # create the link table between movies and genres
        cur.execute("""
            CREATE TABLE movie_genres (
                movie_id INTEGER,
                genre_id INTEGER,
                PRIMARY KEY (movie_id, genre_id));""")

        # define total count of link placehlder
        link_count=0
        # for each genre, we select all movie_id where the flag is 1 and insert links
        for name in genre_names:
            # get the numeric id for this genre name
            cur.execute("SELECT genre_id FROM genres WHERE genre_name = ?;", (name,))
            row = cur.fetchone()
            # if the genre id is not found, skip
            if not row:
                continue
            genre_id = int(row[0])

            # build SQL that picks movie_id where this genre flag equals 1
            sql = f"SELECT movie_id FROM movies WHERE \"{name}\" = 1;"
            # run the query to get all matching movie ids
            cur.execute(sql)
            movie_rows = cur.fetchall()

            # insert one row into movie_genres for each (movie_id, genre_id) pair
            for (movie_id,) in movie_rows:
                cur.execute(
                    "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?);",
                    (int(movie_id), genre_id),)
                # increament the total link count
                link_count += 1

        # create indexes to make genre queries fast
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_genres_name ON genres(genre_name);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_movie_genres_genre ON movie_genres(genre_id);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_movie_genres_movie ON movie_genres(movie_id);")

        # commit the transaction so all changes are saved
        conn.commit()
        # execute the count select
        cur.execute("SELECT COUNT(*) FROM genres;")
        genre_count = int(cur.fetchone()[0])
        logger.info(f"Built {genre_count} genres and {link_count} movie-genre links.")
        return {
            "success": True,
            "message": "Genres normalized successfully.",
            "genre_count": genre_count,
            "movie_genre_links": link_count,}

    except Exception as ex:
        # if something goes wrong, roll back all changes
        conn.rollback()
        logger.error(f"Failed to normalize genres: {str(ex)}")
        return {
            "success": False, 
            "message": str(ex), 
            "genre_count": 0, 
            "movie_genre_links": 0}

    finally:
        # always close the connection at the end
        conn.close()



# update movie status
def create_movie_rating_stats_tbl(db_file_path: str) -> Dict:
    """Function to add 'avg_rating' and 'num_ratings' to 'movies' and fill them from 'ratings'.

    Args
        db_file_path (str): Path to the SQLite database file.

    Returns:
        Dict: containing the success message and log.
    """
    # open a connection to the SQLite database file
    conn = sqlite3.connect(db_file_path)
    # create a cursor so we can run SQL commands
    cur = conn.cursor()

    try:
        # start a transaction so updates are applied together
        conn.execute("BEGIN")
        # add 'avg_rating' column if it does not exist yet
        cur.execute("""ALTER TABLE movies ADD COLUMN avg_rating REAL""")
    except sqlite3.OperationalError:
        # if the column already exists, SQLite raises an error; we ignore it
        pass

    try:
        # add 'num_ratings' column if it does not exist yet
        cur.execute("""ALTER TABLE movies ADD COLUMN num_ratings INTEGER""")
    except sqlite3.OperationalError:
        # if the column already exists, ignore the error
        pass

    try:
        # compute average rating and number of ratings per movie using the ratings table
        cur.execute("""
            WITH stats AS (
                SELECT
                    movie_id,
                    AVG(rating) AS avg_rating,
                    COUNT(*) AS num_ratings
                FROM ratings
                GROUP BY movie_id
            )
            UPDATE movies
            SET
                avg_rating = (SELECT stats.avg_rating FROM stats WHERE stats.movie_id = movies.movie_id),
                num_ratings = (SELECT stats.num_ratings FROM stats WHERE stats.movie_id = movies.movie_id);""")

        # create indexes so sorting and filtering by these fields is fast
        cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_avg ON movies(avg_rating);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_num ON movies(num_ratings);")

        # commit all changes
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM movies WHERE num_ratings IS NOT NULL;")
        updated_count = int(cur.fetchone()[0])
        logger.info(f"Updated {updated_count} movies with avg_rating and num_ratings.")
        return {
            "success": True,
            "message": "Movie stats updated successfully.",
            "updated_movies": updated_count}

    except Exception as ex:
        # if anything fails, roll back to keep the database clean
        conn.rollback()
        conn.rollback()
        logger.error(f"Failed to update movie stats: {ex}")
        return {
            "success": False, 
            "message": str(ex), 
            "updated_movies": 0}

    finally:
        # always close the connection
        conn.close()



# if __name__ == "__main__":
#     movies_df, ratings_df = data_loader.load_movielens_data("./movie_reccommender_system/data_ingestor/data_raw/archive/ml-100k/")
#     summary = insert_movies_and_ratings_into_sqlite(movies_df, ratings_df)
#     print(summary)  # {'movie_rows': 1682, 'rating_rows': 100000}