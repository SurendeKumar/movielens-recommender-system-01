""" Movielens Query Responder """
import os
import logging
from fastapi import APIRouter
from pydantic import ValidationError
from fastapi import HTTPException, status
from movie_reccommender_system.query_processor.rules_based_parser import user_query_parser
from movie_reccommender_system.response_basemodel_validator import query_processor_model
from movie_reccommender_system.query_processor.query_processor_main import MovielensQueryProcessor
from movie_reccommender_system.response_basemodel_validator import llm_response_model
from movie_reccommender_system.query_responder import llm_client
# define basic config
logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# logger for this router
logger = logging.getLogger("LLM_Responder_API")

# initialise the router
router = APIRouter(tags=["LLM_RESPONDER"])
# read db path (use same env as ingestion)
DB_PATH = os.getenv("SQLITE_DB_PATH", "./movie_reccommender_system/db/movies.db")
# initiate the query processor class
queryProcessor = MovielensQueryProcessor(db_file_path=DB_PATH)

# llm client
# HUGGINGFACE_MODEL_ID="meta-llama/Llama-3.2-1B-Instruct"
HUGGINGFACE_MODEL_ID_3B="meta-llama/Llama-3.2-3B-Instruct"
HUGGINGFACE_HUB_TOKEN="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"


@router.post("/query/responder")
def api_query_responder(req:query_processor_model.ParseRequest):
    """ POST LLM Client Responder."""
    try:
        logger.info("Started to parse the user query..")
        parsed = user_query_parser(req.text)
        if not parsed or not getattr(parsed, "intent", None):
            logger.error("Parser did not return a valid intent.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to parse the query. Please provide a valid request.")

        logger.info(f"Parsed query -> intent: {parsed.intent}, slots: {parsed.dict() if hasattr(parsed,'dict') else parsed}")
    
        logger.info(f"Started to process the user's query after parser..")
        try:
            query_processor_output, _=queryProcessor.query_executor_output_handler(parsed, limit=10)
        except Exception as query_processor_erorr:
            logger.exception("Query processor failed.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query processor failed: {str(query_processor_erorr)}")
        

        logger.info(f"Validate the request format before LLM inference..")
        try:
            requested_query=llm_response_model.AnswerRequest(
                executor_payload=query_processor_output, 
                max_results=5, 
                tone="concise",
                diversify=True)
        except ValidationError as llm_basemodel_res_error:
            logger.exception("Invalid request payload for AnswerRequest.")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid request payload: {llm_basemodel_res_error.errors()}")

        logger.info(f"Starting to responder the user's query.")
        try:
            output_response = llm_client.generate_query_response(requested_query)
        except Exception as llm_response_error:
            logger.exception("LLM client failed.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM client error: {str(llm_response_error)}")

        logger.info(f"Successfully completed the Query's reponse..")
        return output_response
    
    except HTTPException:
        raise
    except Exception as server_eror:
        logger.exception("Unexpected error occurred.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(server_eror)}")
