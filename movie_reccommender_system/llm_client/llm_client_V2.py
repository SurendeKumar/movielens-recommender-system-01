# app_query_answer.py
# -------------------------------------------------------
# FastAPI endpoint: /query/answer
# Wires together:
#  - Point 1: canonicalize_query_output
#  - Point 2: extract_compact_context  (with titles list)
#  - Point 5: apply_edge_handling
#  - Point 3&4: build_llm_prompt (facts block)
#  - Point 6: call Hugging Face LLM (Llama 3 family), with a safe fallback
# -------------------------------------------------------
import os
import time
import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from llm_preprocessing import canonicalize_query_output
from llm_context_builder import extract_compact_context
from llm_edgecase_handling import apply_edge_handling
from llm_prompt_builder import build_llm_prompt
from llm_prompt_builder import make_facts_lines
from llm_conversational_renderer import render_conversational_answer
from transformers import pipeline



# Define a request object that holds SQL executor results + options
class AnswerRequest(BaseModel):
    """
    Input object for the answering pipeline.
    """
    # Executor payload must contain {intent, slots, results}
    executor_payload: Optional[Dict[str, Any]] = Field(default=None)
    # Maximum results to keep after edge handling
    max_results: int = Field(default=5)
    # Whether to diversify across genres when too many results
    diversify: bool = Field(default=True)
    # Tone hint for the LLM output (e.g., concise, friendly)
    tone: str = Field(default="concise")
    # Maximum number of tokens the LLM should generate
    max_new_tokens: int = Field(default=120)
    # Sampling temperature for generation
    temperature: float = Field(default=0.3)
    # Top-p nucleus sampling
    top_p: float = Field(default=0.9)


# Define a response object for the pipeline
class AnswerResponse(BaseModel):
    """
    Output object for the answering pipeline.
    """
    # Canonical intent
    intent: str
    # Canonical slots
    slots: Dict[str, Any]
    # Final results after edge handling
    results: list
    # Compact context with metadata
    context: Dict[str, Any]
    # LLM model info and params
    llm: Dict[str, Any]
    # Preview of the generated prompt for debugging
    prompt_preview: str
    # Final answer from the LLM
    answer: str
    # Timing metrics in milliseconds
    timing_ms: Dict[str, int]
    llm: Optional[Dict[str, Any]]


# Create the main function that wires Points 1–5 + conversational rendering
def query_answer(req: AnswerRequest) -> AnswerResponse:
    """
    Assemble the full pipeline without LLM:
      1) Canonicalize results
      2) Build compact context
      3) Apply edge handling
      4) Render a deterministic, conversational answer based on intent
    """
    # Ensure we have an executor payload
    if not req.executor_payload:
        raise ValueError("executor_payload is required (intent, slots, results).")

    # Start total timer
    t0_total = time.time()

    # Start preprocessing timer
    t0_pre = time.time()
    # Run canonicalization (Point 1)
    canonical = canonicalize_query_output(req.executor_payload, max_results=max(5, req.max_results))
    # Build context (Point 2)
    context = extract_compact_context(canonical, max_filters_length=160)
    # Add the titles list for convenience and potential future use
    context["titles"] = [r.get("title") for r in canonical.get("results", []) if r.get("title")]
    # Apply edge handling (Point 5)
    canonical, context = apply_edge_handling(
        canonical,
        context,
        max_results=req.max_results,
        min_count_threshold=50,
        diversify=req.diversify
    )
    # Stop preprocessing timer
    t1_pre = time.time()

    # Extract fields we need to render
    intent = canonical.get("intent", "")
    slots = canonical.get("slots", {})
    results = canonical.get("results", [])

    # Render a short conversational answer string (deterministic)
    answer_text = render_conversational_answer(intent, context, results, max_items=req.max_results)

    # Build a tiny "prompt_preview" string that shows what we summarized (for debug)
    # This is NOT an LLM prompt—just a human-readable trace.
    if results:
        # Build a compact comma-separated list of first few titles
        preview_titles = ", ".join([r.get("title", "Unknown") for r in results[:req.max_results]])
        # Include filters hint if present
        hint = context.get("filters_text")
        # Build the preview line
        prompt_preview = f"Summarized {len(results)} result(s): {preview_titles}" + (f" | filters: {hint}" if hint else "")
    else:
        # If no results, keep it short
        prompt_preview = "Summarized 0 results."

    # Build the final response
    response = AnswerResponse(
        intent=intent,
        slots=slots,
        results=results,
        context=context,
        prompt_preview=prompt_preview,
        answer=answer_text,
        timing_ms={
            "preproc": int((t1_pre - t0_pre) * 1000),
            "total": int((time.time() - t0_total) * 1000),
        },
        llm={"model": "rule-based", "params": {}} 
    )
    # Return the response
    return response



# Allow running as a script for quick local testing
if __name__ == "__main__":
    # URL - model_id=https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
    # HUGGINGFACE_MODEL_ID="meta-llama/Llama-3.2-1B-Instruct"
    HUGGINGFACE_MODEL_ID_3B="meta-llama/Llama-3.2-3B-Instruct"
    HUGGINGFACE_HUB_TOKEN="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"
    # Build a small sample executor payload
    sample_payload = {
        "intent": "TOP_N",
        "slots": {"min_rating": "4.0", "start_year": "2000", "end_year": "2010"},
        "results": [
            {"movieId": 1, "title": "The Dark Knight", "year": "2008", "avg_rating": "4.7", "num_ratings": "5000", "genres": "Action|Crime|Drama"},
            {"movieId": 2, "title": "Inception", "year": "2010", "avg_rating": "4.6", "num_ratings": "4500", "genres": ["Action", "Sci-Fi", "Thriller"]}
        ]
    }
    # Create a request object
    req = AnswerRequest(executor_payload=sample_payload, max_results=5, tone="concise", diversify=True)
    # Run the pipeline
    res = query_answer(req)
    # Print the output with Unicode preserved (no \u escapes) and pretty formatting
    print(json.dumps(res.model_dump(), indent=4, ensure_ascii=False))