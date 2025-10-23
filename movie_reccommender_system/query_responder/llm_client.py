""" LLM Client - meta-llama/Llama-3.2-3B-Instruct """
import os
import time
import json
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from transformers import pipeline
from movie_reccommender_system.query_responder.llm_preprocessing import normalise_query_output
from movie_reccommender_system.query_responder.llm_context_builder import extract_compact_context
from movie_reccommender_system.query_responder.llm_edgecase_handling import apply_edgecase_handling
from movie_reccommender_system.query_responder.llm_prompt_builder import make_facts_lines, build_llm_prompt
from movie_reccommender_system.query_responder.llm_conversational_renderer import render_conversational_answer
from movie_reccommender_system.response_basemodel_validator import llm_response_model
# basic log info 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# deifne single logger for context builder
logger=logging.getLogger("LLM_Edgecase_Handler")


# create the main function that wires Points 1–5 + conversational rendering
def generate_query_response(req: llm_response_model.AnswerRequest):
    """
    Assemble the full pipeline without LLM:
      1) normalised results
      2) build compact context
      3) apply edge handling
      4) text afterprompt builder
      4) conversational answer based on intent
    """
    # ensure we have an executor payload
    if not req.executor_payload:
        raise ValueError("executor_payload is required (intent, slots, results).")

    # start total timer & start preprocessing timer
    start_time, preprocessing_timer = time.time(), time.time()

    logger.info(f"Normalising results..")
    normalised_data = normalise_query_output(req.executor_payload, max_results=max(5, req.max_results))
    # Build context (Point 2)
    logger.info(f"Building the context..")
    context = extract_compact_context(normalised_data, max_filters_length=160)
    # Add the titles list for convenience and potential future use
    context["titles"] = [r.get("title") for r in normalised_data.get("results", []) if r.get("title")]
    # Apply edge handling (Point 5)
    normalised_data, context = apply_edgecase_handling(
        normalised_data,
        context,
        max_results=req.max_results,
        min_count_threshold=50,
        diversify=req.diversify)
    # define stop preprocessing timer
    preprocessing_end_time = time.time()

    # extract fields we need to render
    intent = normalised_data.get("intent", "")
    slots = normalised_data.get("slots", {})
    results = normalised_data.get("results", [])

    # quick test - render a short conversational answer string (deterministic)
    logger.info(f"Conversational Render...")
    answer_text = render_conversational_answer(intent, context, results, max_items=req.max_results)
    
    logger.info(f"Building the system prompt.")    
    system_prompt= build_llm_prompt(
        context, 
        normalised_data["results"], 
        tone="concise", 
        max_items=5)

    # build the final response
    response = llm_response_model.AnswerResponse(
        intent=intent,
        slots=slots,
        results=results,
        context=context,
        prompt_preview=system_prompt,
        answer=answer_text,
        timing_ms={
            "preproc": int((preprocessing_end_time - start_time) * 1000),
            "total": int((time.time() - preprocessing_timer) * 1000),},
        llm={"model": "rule-based", "params": {}} )
    # return the response
    return response



# # Allow running as a script for quick local testing
# if __name__ == "__main__":
#     # URL - model_id=https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
#     # HUGGINGFACE_MODEL_ID="meta-llama/Llama-3.2-1B-Instruct"
#     HUGGINGFACE_MODEL_ID_3B="meta-llama/Llama-3.2-3B-Instruct"
#     HUGGINGFACE_HUB_TOKEN="hf_xxxxx"
#     # Build a small sample executor payload
#     # sample_payload = {
#     #     "intent": "TOP_N",
#     #     "slots": {"min_rating": "4.0", "start_year": "2000", "end_year": "2010"},
#     #     "results": [
#     #         {"movieId": 1, "title": "The Dark Knight", "year": "2008", "avg_rating": "4.7", "num_ratings": "5000", "genres": "Action|Crime|Drama"},
#     #         {"movieId": 2, "title": "Inception", "year": "2010", "avg_rating": "4.6", "num_ratings": "4500", "genres": ["Action", "Sci-Fi", "Thriller"]}
#     #     ]
#     # }

#     sample_payload = {
#             "intent": "TOP_N",
#             "slots": {
#                 "start_year": 1998
#             },
#             "results": [
#                 {
#                     "movieId": "1",
#                     "title": "Tokyo Fist (1995)",
#                     "year": 1998,
#                     "avg_rating": 4.0,
#                     "num_ratings": 1,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "2",
#                     "title": "Men With Guns (1997)",
#                     "year": 1998,
#                     "avg_rating": 3.5,
#                     "num_ratings": 2,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "3",
#                     "title": "Mercury Rising (1998)",
#                     "year": 1998,
#                     "avg_rating": 3.429,
#                     "num_ratings": 7,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "4",
#                     "title": "Man in the Iron Mask, The (1998)",
#                     "year": 1998,
#                     "avg_rating": 3.417,
#                     "num_ratings": 12,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "5",
#                     "title": "Replacement Killers, The (1998)",
#                     "year": 1998,
#                     "avg_rating": 3.308,
#                     "num_ratings": 39,
#                     "genres": [
#                         "Action"
#                     ]
#                 }
#             ]
#         }
#     # create a request object
#     req = llm_response_model.AnswerRequest(
#         executor_payload=sample_payload, 
#         max_results=5, 
#         tone="concise",
#         diversify=True)
#     # run the pipeline
#     res = generate_query_response(req)
#     # Print the output with Unicode preserved (no \u escapes) and pretty formatting
#     print(json.dumps(res.model_dump(), indent=4, ensure_ascii=False))