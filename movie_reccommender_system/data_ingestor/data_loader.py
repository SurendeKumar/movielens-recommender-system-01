"""Script to load the movielens data """
import os
import sqlite3
import logging
import pandas as pd
from dotenv import load_dotenv
from typing import Dict, Tuple

# initiate load_dotenv class
load_dotenv()

# basic logging config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# define the logger
logger = logging.getLogger("movielens_loader")


# load movie data
def load_movielens_data(data_folder_path: str):
    """Function to load MovieLens 100k raw files into pandas DataFrames.

    Args:
        data_folder_path : str (Path to the folder with 'u.item' and 'u.data').

    Returns
        Tuple[pandas.DataFrame, pandas.DataFrame]: (movies_df, ratings_df)
    """
    # build file paths for the MovieLens files
    movies_file_path = os.path.join(data_folder_path, "u.item")
    logger.info(f"Movies file path: {movies_file_path}")
    ratings_file_path = os.path.join(data_folder_path, "u.data")
    logger.info(f"Ratings file path: {ratings_file_path}")

    # check both files exist under data_raw dir
    if not os.path.isfile(movies_file_path):
        logger.error(f"Movies file not found: {movies_file_path}")
        raise FileNotFoundError(f"Missing file: {movies_file_path}")
    if not os.path.isfile(ratings_file_path):
        logger.error(f"Ratings file not found: {ratings_file_path}")
        raise FileNotFoundError(f"Missing file: {ratings_file_path}")

    # read movies file (pipe-separated)
    logger.info("Loading movies data...")
    movies_df = pd.read_csv(
        movies_file_path,
        sep="|",
        header=None,
        encoding="latin-1",
        # usecols=[0,1,2,3,4],
        dtype={
            0: "int64",
            1: "string",
            2: "string",
            3: "string",
            4: "string",},)
    # defien the columns
    # movies_df.columns = ["movie_id", "title", "release_date", "video_release_date", "imdb_url"]
    # define all 24 column names
    movies_df.columns = [
        "movie_id",
        "title",
        "release_date",
        "video_release_date",
        "imdb_url",
        "unknown",
        "Action",
        "Adventure",
        "Animation",
        "Children",
        "Comedy",
        "Crime",
        "Documentary",
        "Drama",
        "Fantasy",
        "Film-Noir",
        "Horror",
        "Musical",
        "Mystery",
        "Romance",
        "Sci-Fi",
        "Thriller",
        "War",
        "Western",]

    # convert data types
    movies_df["movie_id"] = movies_df["movie_id"].astype("int64")
    for col in movies_df.columns[5:]:
        movies_df[col] = movies_df[col].astype("int8")
    logger.info(f"Movies data loaded successfully with rows: {len(movies_df)}")

    # read ratings file (tab-separated)
    logger.info("Loading ratings data...")
    ratings_df = pd.read_csv(
        ratings_file_path,
        sep="\t",
        header=None,
        dtype={
            0: "int64",
            1: "int64",
            2: "int8",
            3: "int64",
        },)
    # define the rating columns
    ratings_df.columns = ["user_id", "movie_id", "rating", "unix_time"]
    logger.info(f"Ratings data loaded successfully with rows: {len(ratings_df)}")

    return movies_df, ratings_df



# item EDA
def eda_movies(movies_df):
    """ Function to explore the simple EDA for u.item data.

    Args:
        movies_df : pandas.DataFrame
            DataFrame containing all movie metadata and genres.

    Returns:
        dict: A dictionary with answers to:
            - How many movies are there?
            - Which genres are most common?
    """
    # count unique movie IDs (should be 1682 in ML-100k)
    total_movies = movies_df["movie_id"].nunique()

    # check which genres are most common: 
    # genre flags start from column index 5 (after imdb_url).
    # each genre column is binary (0/1).
    # summing them gives the number of movies in each genre.
    genre_counts = movies_df.iloc[:, 5:].sum().sort_values(ascending=False)

    # return results in a dictionary for easy testing or logging
    return {
        "total_movies": total_movies,
        "genre_counts": genre_counts.to_dict(),}


# rating EDA
def eda_ratings(
        ratings_df, 
        movies_df):
    """Function to explore the simple EDA for u.data.

    Args:
        ratings_df: pandas.DataFrame
            DataFrame containing user–movie ratings.
        movies_df: pandas.DataFrame
            DataFrame containing the title details.

    Returns: 
        dict: A dictionary with answers to:
            - How many ratings do we have?
            - What’s the most common rating score?
            - Which movie is most rated?
    """

    # how many ratings do we have -> Simply the number of rows in the ratings dataframe
    total_ratings = len(ratings_df)

    # what is the most common rating score -> count how many times each rating value (1–5) occurs
    rating_distribution = ratings_df["rating"].value_counts().sort_index()
    # get the score with the maximum count
    most_common_rating = int(rating_distribution.idxmax())
    most_common_rating_count = int(rating_distribution.max())


    # which movie is most rated -> group by movie_id and count how many ratings each movie received
    ratings_per_movie = ratings_df.groupby("movie_id")["rating"].count()
    # find the movie ID with the most ratings
    most_rated_movie_id = int(ratings_per_movie.idxmax())
    most_rated_count = int(ratings_per_movie.max())

    # get the movie title for most rated movie
    most_rated_movie_title = movies_df.loc[
        movies_df["movie_id"] == most_rated_movie_id, "title"].values[0]

    # return results in dictionary form
    return {
        "total_ratings": total_ratings,
        "most_common_rating": {
            "score": most_common_rating,
            "count": most_common_rating_count,
        },
        "most_rated_movie": {
            "movie_id": most_rated_movie_id,
            "most_rated_title": most_rated_movie_title,
            "count": most_rated_count
        },}



# if __name__ == "__main__":
#     data_folder_path="./movie_reccommender_system/data_ingestor/data_raw/archive/ml-100k/"
#     movies_df, ratings_df=load_movielens_data(data_folder_path)

#     # print("movies_df: \n", movie_df)
#     # print(" ========= "*20)
#     # print("ratings_df: \n", rating_df)

#     ####################### EDA ########################
#     movies_summary = eda_movies(movies_df)
#     ratings_summary = eda_ratings(ratings_df, movies_df)

#     print("Number of movies:", movies_summary["total_movies"])
#     print("Top 5 genres:", list(movies_summary["genre_counts"].items())[:5])
#     print("Number of ratings:", ratings_summary["total_ratings"])
#     print("Most common rating:", ratings_summary["most_common_rating"])
#     print("Most rated movie:", ratings_summary["most_rated_movie"])
    