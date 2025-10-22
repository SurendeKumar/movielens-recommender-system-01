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
from llm_prompt_builder import render_conversational_answer
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


# Define a helper that creates a generator client for text-generation
def build_ultra_compact_prompt(context: Dict[str, Any], results: list, tone: str = "concise", max_items: int = 5) -> str:
    """
    Create a very short prompt that tiny models handle better:
    - one instruction line
    - facts block only (no headings or extra scaffolding)
    """
    # Build a one-line instruction tuned for tiny models
    instruction = f"Summarize these movies in one short, {tone} sentence."
    # Build deterministic bullet-point fact lines from results
    facts_lines = make_facts_lines(results, max_items=max_items)
    # If there are no facts, include a single sentinel bullet
    if not facts_lines:
        facts_lines = ["• No matching items."]
    # Join the instruction and facts with a newline
    return instruction + "\n" + "\n".join(facts_lines)


# Build a deterministic one-line summary if the LLM returns nothing
def deterministic_summary_from_results(context: Dict[str, Any], results: list) -> str:
    """
    Create a safe one-line summary directly from context/results without using an LLM.
    """
    # Pull a short filters hint if available
    hint = context.get("filters_text") or ""
    # Create a container for compact triples (Title, Year, Rating)
    triples = []
    # Iterate over up to three results to keep it short
    for r in results[:3]:
        # Read title safely
        title = r.get("title")
        # Read year safely
        year = r.get("year")
        # Read rating safely
        rating = r.get("avg_rating")
        # If we have title, year, and rating, build the richest triple
        if title and isinstance(year, int) and isinstance(rating, (int, float)):
            triples.append(f"{title} ({year}, {rating:.1f})")
        # Else fall back to title + year when available
        elif title and isinstance(year, int):
            triples.append(f"{title} ({year})")
        # Else just use the title
        elif title:
            triples.append(f"{title}")
    # If we collected triples and have a hint, mention the filters
    if triples and hint:
        return f"{', '.join(triples)} match your filters ({hint})."
    # If we collected triples but no hint, produce a simple sentence
    if triples:
        return f"{', '.join(triples)} match your request."
    # If nothing at all, produce a minimal no-results line
    return "No matching movies found. Try lowering the rating or widening the year range."


# Create a tiny-model-friendly text-generation client
def get_text_generation_client(model_id: str, hf_token: Optional[str]):
    """
    Prepare a text-generation callable and return it with model metadata.
    """
    # If no model id is provided, return a deterministic fallback generator
    if not model_id:
        # Define a simple fallback that lists titles from the facts block
        def fallback_generate(prompt_text: str, params: Dict[str, Any]) -> str:
            # Ensure the prompt is a string
            if not isinstance(prompt_text, str):
                return "No matching movies found. Try relaxing your filters."
            # Extract non-empty lines
            lines = [ln.strip() for ln in prompt_text.splitlines() if ln.strip()]
            # Collect bullet-point facts
            facts = [ln for ln in lines if ln.startswith("• ")]
            # If no facts exist, return a polite fallback message
            if not facts:
                return "No matching movies found. Try relaxing your filters."
            # Extract titles from each bullet line
            titles = []
            for ln in facts:
                head = ln.replace("• ", "", 1)
                title = head.split("(", 1)[0].strip()
                if title:
                    titles.append(title)
            # Compose a short, readable sentence with up to five titles
            return f"Here are the matching movies: {', '.join(titles[:5])}."
        # Return the fallback callable with a label
        return fallback_generate, {"model": "local-fallback"}

    # Build kwargs for the HF pipeline (pass token only if provided)
    pipeline_kwargs: Dict[str, Any] = {"model": model_id, "trust_remote_code": True}
    # If we were given a HF token, pass it directly (no login())
    if hf_token:
        pipeline_kwargs["token"] = hf_token
    # Create the text-generation pipeline
    textgen = pipeline("text-generation", **pipeline_kwargs)

    # Define a wrapper around the pipeline with tiny-model-safe defaults
    def hf_generate(prompt_text: str, params: Dict[str, Any]) -> str:
        """
        Generate a short completion with settings that reduce empty/echo outputs.
        """
        # Guard that the prompt is a plain string
        if not isinstance(prompt_text, str):
            raise TypeError("Prompt must be a string.")
        # Use greedy decoding for tiny models to reduce EOS-on-first-token behavior
        gen_kwargs = {
            "max_new_tokens": params.get("max_new_tokens", 60),
            "do_sample": False,}
        # Ask for completion-only text where supported (ignored otherwise)
        try:
            gen_kwargs["return_full_text"] = False
        except Exception:
            pass
        # Call the pipeline with the compact prompt
        out = textgen(prompt_text, **gen_kwargs)
        # Extract the generated text robustly
        raw_text = out[0].get("generated_text", "") if isinstance(out, list) else str(out)
        # Return the stripped text (may be empty; caller will fallback)
        return (raw_text or "").strip()

    # Return the HF generator and model info
    return hf_generate, {"model": model_id}


# Define the main orchestration function that wires together Points 1–6
def query_answer(req: AnswerRequest, model_id: str, hf_token: Optional[str] = None) -> AnswerResponse:
    """
    Run the full pipeline: canonicalize → context → edge handling → ultra-compact prompt → LLM.
    """
    # Validate that the executor payload is present
    if not req.executor_payload:
        raise ValueError("executor_payload is required (intent, slots, results).")

    # Start total runtime timer
    t0_total = time.time()

    # Start preprocessing timer
    t0_pre = time.time()
    # Run Point 1: canonicalize the raw executor payload
    canonical = canonicalize_query_output(req.executor_payload, max_results=max(5, req.max_results))
    # Run Point 2: build compact context object
    context = extract_compact_context(canonical, max_filters_length=160)
    # Add a quick list of titles for convenience in prompts/UI
    context["titles"] = [r.get("title") for r in canonical.get("results", []) if r.get("title")]
    # Run Point 5: apply edge handling (overflow, quality floor, suggestions)
    canonical, context = apply_edge_handling(
        canonical,
        context,
        max_results=req.max_results,
        min_count_threshold=50,
        diversify=req.diversify
    )
    # Stop preprocessing timer
    t1_pre = time.time()

    # Build an ultra-compact prompt tailored for tiny models
    wrapped_prompt = build_ultra_compact_prompt(
        context=context,
        results=canonical.get("results", []),
        tone=req.tone,
        max_items=req.max_results
    )

    # Prepare the text-generation client with the selected model and token
    llm_client, llm_info = get_text_generation_client(model_id, hf_token)

    # Start LLM generation timer
    t0_llm = time.time()
    # Generate text using tiny-model-friendly decoding settings
    answer_text = llm_client(wrapped_prompt, {
        "max_new_tokens": req.max_new_tokens,
    })
    # Stop LLM generation timer
    t1_llm = time.time()

    # If the model returned nothing, synthesize a deterministic one-liner
    if not answer_text:
        answer_text = deterministic_summary_from_results(context, canonical.get("results", []))

    # Build the final structured response
    response = AnswerResponse(
        intent=canonical.get("intent", ""),
        slots=canonical.get("slots", {}),
        results=canonical.get("results", []),
        context=context,
        llm={
            "model": llm_info.get("model"),
            "params": {
                "max_new_tokens": req.max_new_tokens,
            }
        },
        prompt_preview=wrapped_prompt,
        answer=answer_text,
        timing_ms={
            "preproc": int((t1_pre - t0_pre) * 1000),
            "llm": int((t1_llm - t0_llm) * 1000),
            "total": int((time.time() - t0_total) * 1000),
        }
    )
    # Return the complete response
    return response



# Entry point for running the script directly
if __name__ == "__main__":
    # HUGGINGFACE_MODEL_ID="meta-llama/Llama-3.2-1B-Instruct"
    HUGGINGFACE_MODEL_ID_3B="meta-llama/Llama-3.2-3B-Instruct"
    HUGGINGFACE_HUB_TOKEN="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"
    # Build a sample payload (simulating SQL executor output)
    sample_payload = {
        "intent": "TOP_N",
        "slots": {"min_rating": "4.0", "start_year": "2000", "end_year": "2010"},
        "results": [
            {"movieId": 1, "title": "The Dark Knight", "year": "2008", "avg_rating": "4.7", "num_ratings": "5000", "genres": "Action|Crime|Drama"},
            {"movieId": 2, "title": "Inception", "year": "2010", "avg_rating": "4.6", "num_ratings": "4500", "genres": ["Action", "Sci-Fi", "Thriller"]}
        ]
    }


    # Build the request with sensible defaults tuned for small models
    req = AnswerRequest(
        executor_payload=sample_payload,
        max_results=5,
        tone="concise",
        temperature=0.25,
        top_p=0.92,
        max_new_tokens=80,
    )

    # Call the full pipeline with explicit model id and token
    res = query_answer(
        req,
        model_id=HUGGINGFACE_MODEL_ID_3B,
        hf_token=HUGGINGFACE_HUB_TOKEN
    )

    # Pretty-print the response
    print(json.dumps(res.model_dump(), indent=4, ensure_ascii=False))