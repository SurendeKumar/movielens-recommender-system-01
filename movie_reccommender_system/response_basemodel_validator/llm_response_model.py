""" LLM Response Validator using pydantic basemodel"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


# Define a request object that holds SQL executor results + options
class AnswerRequest(BaseModel):
    """Input object for the answering pipeline."""
    # excutor payload containing - {intent, slots, results}
    executor_payload: Optional[Dict[str, Any]] = Field(default=None)
    # maximum results to keep after edge handling
    max_results: int = Field(default=5)
    # whether to diversify across genres when too many results
    diversify: bool = Field(default=True)
    # tone hint for the LLM output (e.g., concise, friendly)
    tone: str = Field(default="concise")
    # maximum number of tokens the LLM should generate
    max_new_tokens: int = Field(default=120)
    # sampling temperature for generation
    temperature: float = Field(default=0.3)
    # Top-p nucleus sampling
    top_p: float = Field(default=0.9)


# Define a response object for the pipeline
class AnswerResponse(BaseModel):
    """Output object for the conversation answering."""
    # intent
    intent: str
    # slots
    slots: Dict[str, Any]
    # final results after edge handling
    results: list
    # compact context with metadata
    context: Dict[str, Any]
    # LLM model info and params
    llm: Dict[str, Any]
    # preview of the generated prompt for debugging
    prompt_preview: str
    # final answer from the LLM
    answer: str
    # timing metrics in milliseconds
    timing_ms: Dict[str, int]
    llm: Optional[Dict[str, Any]]