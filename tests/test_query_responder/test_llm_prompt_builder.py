""" Unittest TestSuite -> MovieLens Query Responder - LLM Prompt Builder """
import unittest
import logging
from movie_reccommender_system.query_responder import llm_prompt_builder
# set up logging for this test file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# create a module-level logger
logger = logging.getLogger("TestLLMPromptBuilder")


# TestSuite -  for prompt builder
class TestLLMPromptBuilder(unittest.TestCase):
    """Tests for prompt construction and facts building in llm_prompt_builder.py"""
    # test for make_facts_lines formatting
    def test_make_facts_lines(self):
        """make_facts_lines builds deterministic bullet lines"""
        logger.info(f"Running test_make_facts_lines")
        # build example rows for facts
        rows = [
            {"title": "A", "year": 2012, "avg_rating": 4.6, "num_ratings": 2000, "genres": ["Drama"]},
            {"title": "B", "year": None, "avg_rating": None, "num_ratings": None, "genres": []},]
        # call the facts builder
        lines = llm_prompt_builder.make_facts_lines(rows, max_items=10)
        # assert first line format content
        self.assertTrue(lines[0].startswith("• A (2012) — 4.6/5 — 2000 ratings"))
        # assert second line mentions rating n/a
        self.assertIn("rating n/a", lines[1])

    # test for build_llm_prompt composition
    def test_build_llm_prompt(self):
        """build_llm_prompt composes sections into one prompt"""
        logger.info("Running test_build_llm_prompt")
        # build a context dictionary
        context = {
            "result_count": 2,
            "filters_text": "since 2010; ≥ 4.0",
            "time_window": "since 2010",
            "rating_bounds": "≥ 4.0",
            "titles": ["A", "B"],}
        # build result rows for facts
        results = [{
            "title": "A", 
            "year": 2012,
            "avg_rating": 4.6, 
            "num_ratings": 2000, 
            "genres": ["Drama"]}]
        # call prompt builder
        prompt = llm_prompt_builder.build_llm_prompt(
            context, 
            results, 
            tone="concise", 
            max_items=5)
        # assert system guidance is present
        self.assertIn("You are a helpful movie assistant", prompt)
        # assert context summary is present
        self.assertIn("Context: since 2010; ≥ 4.0", prompt)
        # assert found count is present
        self.assertIn("Found: 2 result(s).", prompt)
        # assert facts header is present
        self.assertIn("Facts:", prompt)



# if __name__ == "__main__":
#     unittest.main(verbosity=2)

    # cli cmd
    # python -m unittest tests/test_query_responder/test_llm_prompt_builder.py

