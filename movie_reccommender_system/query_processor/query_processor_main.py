"""Build and run SQL for parsed intents against the SQLite DB.
 
 Existing schema:
- movies(title, release_date, avg_rating, num_ratings, ...)
- genres(genre_id, genre_name)
- movie_genres(movie_id, genre_id)
- ratings(user_id, movie_id, rating, unix_time)

We keep queries simple, parameterized, and fast with your indexes.
"""

# import sqlite and typing
import os
import sqlite3
import logging
from pydantic import BaseModel
from typing import List, Tuple, Dict
from movie_reccommender_system.query_processor import query_preprocessing
from movie_reccommender_system.response_basemodel_validator.query_processor_model import QueryParser, SingleRowMovieRecord
# define basic config
logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# loger as liner
logger = logging.getLogger("Movielens Query_processor")  

# movielen - query process class
class MovielensQueryProcessor:
    """SQLITE service to execute structured queries for parsed intents."""

    # save db path
    def __init__(
            self, 
            db_file_path: str):
        """Initialise to save SQLite DB file path.
        
        Args: 
            db_file_path (str):  Path to the SQLite database file.
        """
        self.logger = logging.getLogger("Main_Query_Processor")
        self.logger.info(f"Initialising MovielensQueryProcessor with DB path: {os.path.basename(db_file_path)}")
        # instantiate db_file_path
        self.db_file_path = db_file_path


    # helper to buld sqlite connection
    def build_connection(self):
        """Function to open a SQLite connection."""
        self.logger.info(f"Opening SQLite connection to: {os.path.basename(self.db_file_path)}")
        # connect and return
        return sqlite3.connect(self.db_file_path)

    # convert rows to response models
    def convert_rows_to_response_model(
            self, 
            rows: List[Tuple]):
        """Function to urn SQL tuples (title, release_date, avg_rating, num_ratings) into SingleRowMovieRecord list.

        Args: 
            rows (list): Containing the movie records as single rows.

        Returns:
            output_list (list): Containing the response.
        """
        logger.info(f"Converting {len(rows) if rows is not None else 0} SQL rows to response model")
        # define output list
        output_response_list= []
        # go over each row and convert
        for title, release_date, avg_rating, num_ratings in rows:
            # compute display year from release_date
            year = query_preprocessing.extract_year_from_text(release_date)
            # define avg_rating float vlaue
            avg_rating_value=float(round(avg_rating, 3)) if avg_rating is not None else None
            # define num rating value
            num_ratings_value=int(num_ratings) if num_ratings is not None else None
            # append one SingleRowMovieRecord
            output_response_list.append(
                SingleRowMovieRecord(
                    title=title,
                    year=year if year else None,
                    avg_rating=avg_rating_value,
                    num_ratings=num_ratings_value))
        
        logger.info(f"Converted to {len(output_response_list)} response rows")
        return output_response_list
    

    # 1. run a GET_DETAILS lookup
    def run_get_movie_details(
            self, 
            parsed: QueryParser, 
            limit: int = 5):
        """Function to return a small list of movies that match the title (LIKE match).

        Args: 
            parsed: QueryParser to return the parsed intent and slots.
            limit (int): default 5.

        Returns:
            list: containing the SingleRowMovieRecord.

        """
        logger.info(f"GET_DETAILS -> title: {parsed.title}, limit: {limit}")
        # open connection - sqlite
        with self.build_connection() as conn:
            # create cursor
            cur = conn.cursor()
            # build pattern with wildcards
            patterns = f"%{parsed.title.strip()}%"
            logger.info(f"Executing title LIKE search with pattern {patterns}")
            # execute a simple selection by title
            cur.execute(
                """
                SELECT 
                    title, 
                    release_date, 
                    avg_rating, 
                    num_ratings
                FROM movies
                WHERE title LIKE ?
                ORDER BY num_ratings DESC, avg_rating DESC
                LIMIT ?;
                """,
                (patterns, limit),)
            # fetch rows
            rows = cur.fetchall()
            logger.info(f"GET_DETAILS: fetched {len(rows)} rows")
            # convert to response models - SingleRowMovieRecord
            single_row_response = self.convert_rows_to_response_model(rows)
            return single_row_response
        

    # 2. run a filter-based recommendation
    def run_recommend_movie_by_filter(
            self, 
            parsed: QueryParser, 
            limit: int = 10):
        """Function to recommend by genres and/or year constraints and min rating.

        Args:
            parsed: QueryParser to return the parsed intent and slots.

        Returns:
            list: containing the SingleRowMovieRecord.
        """
        # open connection
        with self.build_connection() as conn:
            # create cursor
            cur = conn.cursor()

            # start base query and params
            sql = """
                SELECT 
                    m.title, 
                    m.release_date,
                    m.avg_rating, 
                    m.num_ratings
                FROM movies m
            """
            # define list to store all params
            params_list = []

            # join with genres if any genre filter exists
            if parsed.genres:
                sql += """
                    JOIN movie_genres mg ON mg.movie_id = m.movie_id
                    JOIN genres g ON g.genre_id = mg.genre_id
                """
            # where clauses collector
            where = []

            # add genre filter
            if parsed.genres:
                placeholders = ",".join(["?"] * len(parsed.genres))
                where.append(f"g.genre_name IN ({placeholders})")
                params_list.extend(parsed.genres)

            # add single year or range
            if parsed.year:
                where.append("substr(m.release_date, -4, 4) = ?")
                params_list.append(str(parsed.year))
            else:
                if parsed.year_from:
                    where.append("CAST(substr(m.release_date, -4, 4) AS INT) >= ?")
                    params_list.append(parsed.year_from)
                if parsed.year_to:
                    where.append("CAST(substr(m.release_date, -4, 4) AS INT) <= ?")
                    params_list.append(parsed.year_to)

            # apply min rating if present
            # if parsed.min_rating:
            #     where.append("m.avg_rating >= ?")
            #     params_list.append(parsed.min_rating)
            
            if parsed.min_rating:
                # choose operator based on plain-english compare
                if parsed.rating_compare == "less_than_or_equal":
                    where.append("m.avg_rating <= ?")
                else:
                    where.append("m.avg_rating >= ?")
                params_list.append(parsed.min_rating)


            # stitch where if any
            if where:
                sql += " WHERE " + " AND ".join(where)

            # add grouping when we joined genres to avoid duplicates
            if parsed.genres:
                sql += " GROUP BY m.movie_id "

            # add sorting policy: rating then popularity
            sql += " ORDER BY m.avg_rating DESC, m.num_ratings DESC NULLS LAST "

            # final limit
            sql += " LIMIT ? "
            params_list.append(limit)

            # execute
            cur.execute(sql, tuple(params_list))
            # fetch result
            rows = cur.fetchall()
            logger.info(f"RECOMMEND_BY_FILTER -> fetched {len(rows)} rows")
            # convert to response model - SingleRowMovieRecord
            output_row_response=self.convert_rows_to_response_model(rows)
            return output_row_response


    # 3. run a top-n query
    def run_top_n_query(
            self, 
            parsed: QueryParser):
        """Function to return a top-N list by rating and popularity with optional genre and year filters.

        Args:
            parsed: QueryParser to return the parsed intent and slots.

        Returns:
            list: containing the SingleRowMovieRecord.

        """
        logger.info(f"TOP_N -> requested top_n: {getattr(parsed, 'top_n', None)}")
        #  reusing the filter recommender with parsed.top_n
        output_row_response=self.run_recommend_movie_by_filter(parsed, limit=parsed.top_n)
        return output_row_response
    

    # 4. a very light 'similar movies' by shared genres
    def run_similar_movie_genres(
            self, 
            parsed: QueryParser, 
            limit: int = 10):
        """Function to find movies sharing genres with the title given.

        Args:
            parsed: QueryParser to return the parsed intent and slots.

        Returns:
            list: containing the SingleRowMovieRecord.
        """
        logger.info(f"SIMILAR_MOVIES -> base title: {parsed.title} and limit: {limit}")
        # open connection
        with self.build_connection() as conn:
            # cursor
            cur = conn.cursor()

            # find target movie id(s) by title
            cur.execute(
                "SELECT movie_id FROM movies WHERE title LIKE ? LIMIT 1;",
                (f"%{parsed.title.strip()}%",),)
            # fetch single row
            fetch_row = cur.fetchone()
            logger.info(f"SIMILAR_MOVIES: base movie found {bool(fetch_row)}")
            
            # if no base movie, fallback to empty results
            if not fetch_row:
                return []
            base_id = int(fetch_row[0])

            # select movies that share genres with base movie
            cur.execute(
                """
                    SELECT 
                        m.title, 
                        m.release_date, 
                        m.avg_rating, 
                        m.num_ratings
                    FROM movie_genres mg0
                    JOIN movie_genres mg1 ON mg1.genre_id = mg0.genre_id
                    JOIN movies m ON m.movie_id = mg1.movie_id
                    WHERE mg0.movie_id = ? 
                    AND mg1.movie_id != ?
                    GROUP BY m.movie_id
                    ORDER BY m.avg_rating DESC, m.num_ratings DESC
                    LIMIT ?;
                """,
                (base_id, base_id, limit),)
            # fetch rows
            rows = cur.fetchall()
            logger.info(f"SIMILAR_MOVIES: fetched: {len(rows)} rows and {base_id}")
            # convert to rfesponse models - SingleRowMovieRecord
            output_row_response=self.convert_rows_to_response_model(rows)
            return output_row_response


    # dispatcher as a query exectuor
    def query_excutor(
            self, 
            parsed: QueryParser, 
            limit: int = 10):
        """Function to run the query based on the user's intent.

        Args:
            parsed: QueryParser to return the parsed intent and slots.

        Returns:
            list: containing the SingleRowMovieRecord.

        """
        logger.info(f"Dispatcher: intent: {parsed.intent}, limit: {limit}")
        # switch on intent
        if parsed.intent == "GET_DETAILS":
            return self.run_get_movie_details(parsed, limit=min(limit, parsed.top_n or limit))
        if parsed.intent == "RECOMMEND_BY_FILTER":
            return self.run_recommend_movie_by_filter(parsed, limit=min(limit, parsed.top_n or limit))
        if parsed.intent == "TOP_N":
            return self.run_top_n_query(parsed)
        if parsed.intent == "SIMILAR_MOVIES":
            return self.run_similar_movie_genres(parsed, limit=min(limit, parsed.top_n or limit))

        logger.info(f"Dispatcher: UNKNOWN intent -> returning empty list")
        return []
    

    # main dispatcher to handle for output to reform what is expected for LLM inference
    def query_executor_output_handler(
            self, 
            parsed: QueryParser,
            limit=10):
        """Function to handle the output format after query exectuor.

        Args:
            parsed: QueryParser object containing parsed intent and slots.
            limit: maximum number of results to keep.

        Returns:
            Dict: containing the {intent, slots, results} for normalise_query_output before the LLM inference.
        """
        # decide the final limit by honoring parsed.top_n if present
        final_limit = min(limit, parsed.top_n or limit)
        # get raw_results - 
        logger.info(f"Executing the query procesor to sample the raw_results.")
        raw_results=self.query_excutor(parsed, limit=min(limit, parsed.top_n or limit))
        # intent string
        intent_value = parsed.intent or ""

        # slots dictionary
        slots_dict = {}
        if getattr(parsed, "min_rating", None) is not None:
            slots_dict["min_rating"] = str(parsed.min_rating)
        if getattr(parsed, "year_from", None) is not None:
            slots_dict["start_year"] = str(parsed.year_from)
        if getattr(parsed, "year_to", None) is not None:
            slots_dict["end_year"] = str(parsed.year_to)

        # parse genres either list or joined string
        parsed_genres = getattr(parsed, "genres", []) or []
        genres_value = "|".join(parsed_genres) if isinstance(parsed_genres, list) else parsed_genres

        # adapt results into expected schema
        final_results = []
        for index, result_row in enumerate(raw_results or [], start=1):
            # check if the row is a Pydantic model, convert to a dict; 
            # if it's already a dict, use as-is
            if isinstance(result_row, BaseModel):
                row_dict = result_row.dict()
            elif isinstance(result_row, dict):
                row_dict = result_row
            else:
                # fallback: try attribute access for known fields
                row_dict = {
                    "title": getattr(result_row, "title", ""),
                    "year": getattr(result_row, "year", None),
                    "avg_rating": getattr(result_row, "avg_rating", None),
                    "num_ratings": getattr(result_row, "num_ratings", None),}
                
            
            # read each value safely from the row dictionary
            title_value = row_dict.get("title", "")
            year_value = row_dict.get("year")
            avg_rating_value = row_dict.get("avg_rating")
            num_ratings_value = row_dict.get("num_ratings")

            # append the normalized row expected by your downstream normaliser
            final_results.append({
                "movieId": index,                
                "title": title_value,            
                "year": year_value,             
                "avg_rating": avg_rating_value,  
                "num_ratings": num_ratings_value, 
                "genres": genres_value or []      })

        logger.info(f"Successfully completes the Query Porcessor workflow.")
        return {
            "intent": intent_value,
            "slots": slots_dict,
            "results": final_results}, raw_results


# if __name__ == "__main__":
#     import json
#     from movie_reccommender_system.query_processor import rules_based_parser
#     queryProcessor=MovielensQueryProcessor()

#     text = {"text": "recommend action movies from 2020 with rating at least 4"}
#     parsed = rules_based_parser.user_query_parser(text)
#     logger.info(f"Parsed query -> intent: {parsed.intent}, slots: {parsed.dict()}")
#     # trigger main dispatcher - movie_row variable if we want to check full results
#     query_processor_output, _=queryProcessor.query_executor_output_handler(parsed, limit=10)
#     print("query_processor_output: \n", json.dumps(query_processor_output, indent=4, ensure_enscii=False))