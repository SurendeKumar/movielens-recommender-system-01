""" Movielens Query Processor Router """
import os
import logging
from fastapi import APIRouter
from movie_reccommender_system.query_processor.rules_based_parser import user_query_parser
from movie_reccommender_system.response_basemodel_validator import query_processor_model
from movie_reccommender_system.query_processor.query_processor_main import MovielensQueryProcessor
# define basic config
logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# logger for this router
logger = logging.getLogger("query_processor_api")

# initialise the router
router = APIRouter(tags=["query-processing"])
# read db path (use same env as ingestion)
DB_PATH = os.getenv("SQLITE_DB_PATH", "./movie_reccommender_system/db/movies.db")
# initiate the query processor class
queryProcessor = MovielensQueryProcessor(db_file_path=DB_PATH)


# 1. parse query - only if we want to understand the query structure like debugging or showing the parsed query
@router.post(
        "/query/parse", 
        response_model=query_processor_model.ParseResponse)
def api_parse(req: query_processor_model.ParseRequest):
    """Parse the user text into an intent and slots."""
    logger.info(f"Received /query/parse request -> text: {req.text}")
    # run rule-based parser
    parsed = user_query_parser(req.text)
    logger.info(f"Parsed result -> intent: {parsed.intent}, slots: {parsed.dict()}")
    # return parsed result as model
    return query_processor_model.ParseResponse(parsed=parsed)



# 2. execute - query executor - main decorator which parse text and give the actual answers from the DB
@router.post(
        "/query/execute", 
        response_model=query_processor_model.ExecutePreparedResponse)
def api_execute(req: query_processor_model.ExecuteRequest):
    """ Parse the user text, then run a structured SQL retrieval."""
    logger.info(f"Received /query/execute request -> text: {req.text}, limit: {req.limit}")
    # parse first
    parsed = user_query_parser(req.text)
    logger.info(f"Parsed query -> intent: {parsed.intent}, slots: {parsed.dict()}")
   
    # trigger main dispatcher - movie_row variable if we want to check full results
    query_processor_output, _=queryProcessor.query_executor_output_handler(parsed, limit=10)
    # return both the parse and results after query processor
    # return query_intent_parser_model.ExecuteResponse(
        # parsed=parsed,
        # results=movie_row,
        # prepared=query_processor_output)

    # return final preprared results for LLM inference
    return query_processor_model.ExecutePreparedResponse(**query_processor_output)
