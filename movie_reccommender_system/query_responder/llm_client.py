""" LLM Client - meta-llama/Llama-3.2-3B-Instruct """
import os
import time
import json
import torch
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from transformers import pipeline
from huggingface_hub import InferenceClient
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
logger=logging.getLogger("LLM_Client_Responder")


### only for text-generation pipe
# initialise the hf-> llama 3B instruct 
# try:
#     pipe = pipeline(
#         "text-generation",
#         model="meta-llama/Llama-3.2-3B-Instruct",
#         torch_dtype=torch.float32,
#         device_map="auto",)
#     logger.info("Llama 3.2-3B-Instruct model successfully loaded.")
# except Exception as e:
#     logger.error(f"Failed to load model: {e}")
#     pipe = None



# create the main function that wires Points 1–5 + conversational rendering
def generate_query_response(
        req: llm_response_model.AnswerRequest,
        model_id:str, 
        hf_token:str):
    """Function to generate the Query response using LLM inference:
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
    # build context
    logger.info(f"Building the context..")
    context = extract_compact_context(normalised_data, max_filters_length=160)
    # add the titles list for convenience and potential future use
    context["titles"] = [r.get("title") for r in normalised_data.get("results", []) if r.get("title")]
    # apply edge handling
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
    fallback_answer = render_conversational_answer(intent, context, results, max_items=req.max_results)
    
    logger.info(f"Building the system prompt.")    
    system_prompt, user_message= build_llm_prompt(
        context, 
        normalised_data["results"], 
        tone="concise", 
        max_items=5)
    
    logger.info(f"Calling llm -Llama-3.2-3B-Instruct..")
    llm_query_response=run_hf_llm_inference_client(
        system_prompt=system_prompt,
        user_message=user_message, 
        model_id=model_id, 
        provider="novita",
        hf_token=hf_token,
        temperature=getattr(req, "temperature", 0.3),
        top_p=getattr(req, "top_p", 0.9),
        max_new_tokens=getattr(req, "max_new_tokens", 350))
    # get the answer text after LLM
    answer_text=llm_query_response if llm_query_response else fallback_answer

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
        llm={"provider": "local-transformers",
            "model": "meta-llama/Llama-3.2-3B-Instruct",
            "params": {
                "temperature": getattr(req, "temperature", 0.3),
                "top_p": getattr(req, "top_p", 0.9),
                "max_new_tokens": getattr(req, "max_new_tokens", 350),
                "do_sample": getattr(req, "do_sample", True),
            },
            "used_fallback": not bool(llm_query_response),
        },)
    # return the response
    return response



# huggingface inference client using novita
def run_hf_llm_inference_client(
    system_prompt: str, 
    user_message:str,
    model_id: str, 
    provider: str = "novita",
    hf_token: Optional[str] = None,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_new_tokens: int = 350) -> str:
    """Funcion to call Hugging Face Inference API (provider='novita') for chat completions.

    Args:
        system_prompt: The compiled prompt from `build_llm_prompt()` (already includes your system-style instruction).
        model_id: HF model id to use.
        provider: Inference provider; for your case it's "novita".
        hf_token: Your HF access token. If None, reads from env var HF_TOKEN.
        temperature: Sampling temperature (0.1–0.4 factual; 0.7–1.0 creative).
        top_p: Nucleus sampling cutoff (0.8–0.95 typical).
        max_new_tokens: Upper bound on generated tokens.

    Returns:
        str: Assistant text, or "" if the request fails.
    """
    try:
        hf_inference_client = InferenceClient(
            provider=provider,
            api_key=hf_token)
        logger.info("HF InferenceClient (novita) is ready.")
    except Exception as e:
        logger.error(f"Failed to initialize InferenceClient: {e}")
        return ""

    try:
        # Send your compiled prompt as a single user message.
        # (You already include instructions inside the prompt; no extra system role needed.)
        completion = hf_inference_client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_new_tokens,)

        # Extract assistant message text safely
        choice = completion.choices[0]
        msg = choice.message
        text = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)) or ""
        return text.strip()

    except Exception as e:
        logger.error(f"HF Inference API call failed: {e}")
        return ""




# llm client infernce using pipe as text-generation
def run_hf_llm_client_with_text_generation_pipe(
    system_prompt: str,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_new_tokens: int = 350,
    do_sample: bool = True) -> str:
    """Funciton to run the LLM inference using the Llama 3.2 3B Instruct model via the Hugging Face Transformers pipeline.

        Handles:
        - Lazy loading of the model (loads once globally)
        - Safe text generation using Hugging Face's pipeline
        - Clear parameter control for creativity, sampling, and tone

    Args:
        prompt_text (str): text to generate a response for.
        system_prompt (str, optional): system prompt after prompt compilation.
        temperature (float, optional): Controls randomness in text generation.
            - Low (0.1–0.4): factual, deterministic.
            - Medium (0.5–0.7): balanced tone.
            - High (0.8–1.0): creative or variable tone.
        top_p (float, optional): Probability cutoff for nucleus sampling (0.8–0.95 recommended).
            Ensures the model samples only from the most likely tokens.
        max_new_tokens (int, optional): Maximum number of tokens to generate in the response.
        do_sample (bool, optional): Whether to sample randomly (True) or deterministically (False).
            Generally True if temperature > 0.0.

    Returns:
        str:
            The generated model response as plain text. Returns an empty string on failure.
    """
    # initalise the pipeline
    global pipe

    # prepare the structured messages (Llama 3 uses chat-style input)
    messages = [{"role": "user", "content": system_prompt},]

    logger.info("Generating response using Llama 3.2-3B-Instruct...")
    try:
        # run inference using the pipeline
        outputs = pipe(
            messages,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,)

        # extract generated text safely
        generated_conversation = outputs[0].get("generated_text", "")

        # case 1: Newer format → list of messages
        if isinstance(generated_conversation, list) and generated_conversation:
            last_msg = generated_conversation[-1]
            if isinstance(last_msg, dict) and "content" in last_msg:
                reply = last_msg["content"].strip()
                logger.info(f"Successfully generated response.")
                return reply

        # case 2: Fallback for plain string
        if isinstance(generated_conversation, str):
            reply = generated_conversation.strip()
            logger.info(f"Successfully generated response (plain string).")
            return reply

    except Exception as e:
        logger.error(f"Local LLM generation failed: {e}")

    # return fallback empty string if anything goes wrong
    return ""






# # Allow running as a script for quick local testing
# if __name__ == "__main__":
#     # URL - model_id=https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
#     # HUGGINGFACE_MODEL_ID="meta-llama/Llama-3.2-1B-Instruct"
#     HUGGINGFACE_MODEL_ID_3B="meta-llama/Llama-3.2-3B-Instruct"
#     HUGGINGFACE_HUB_TOKEN="hf_xxx"

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
#     res = generate_query_response(
#         req, 
#         HUGGINGFACE_MODEL_ID_3B,
#           HUGGINGFACE_HUB_TOKEN)
#     # Print the output with Unicode preserved (no \u escapes) and pretty formatting
#     # print(res)
#     print(json.dumps(res.model_dump(), indent=4, ensure_ascii=False))