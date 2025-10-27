""" Unittest TestSuite -> MovieLens LLM Conversational Renderer """
import unittest
import logging
from movie_reccommender_system.query_responder import llm_conversational_renderer
# set up logging for this test file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# create a module-level logger
logger = logging.getLogger("TestLLMConversationalRenderer")


# define the test class for llm_conversational_renderer
class TestLLMConversationalRenderer(unittest.TestCase):
    """Tests for rendering helpers and main renderer in llm_conversational_renderer.py"""
    # test for format_count helper
    def test_format_count(self):
        """format_count handles unknown thousands and millions"""
        logger.info(f"Running test_format_count")
        # assert plain number formatting
        self.assertEqual(llm_conversational_renderer.format_count(999), "999")
        # assert thousands formatting
        self.assertEqual(llm_conversational_renderer.format_count(1200), "1k")
        # assert millions formatting
        self.assertEqual(llm_conversational_renderer.format_count(1500000), "1.5M")
        # assert unknown case formatting
        self.assertEqual(llm_conversational_renderer.format_count(None), "unknown")

    # test for brief and sentence formatters
    def test_format_movie_brief_and_sentence(self):
        """formatters produce compact and sentence outputs"""
        logger.info(f"Running test_format_movie_brief_and_sentence")
        # build an example movie row
        row = {
            "title": "A", 
            "year": 2012, 
            "genres": ["Drama"], 
            "avg_rating": 4.6, 
            "num_ratings": 2345}
        # call brief formatter
        brief = llm_conversational_renderer.format_movie_brief(row)
        # call sentence formatter
        sent = llm_conversational_renderer.format_movie_sentence(row)
        # assert brief contains title and year
        self.assertIn("A (2012", brief)
        # assert brief contains rating star
        self.assertIn("4.6★", brief)
        # assert sentence contains expected phrase
        self.assertIn("A is an Drama movie from 2012", sent)

    # test for natural_join behavior
    def test_natural_join(self):
        """natural_join joins lists naturally"""
        logger.info(f"Running test_natural_join")
        # assert empty list handling
        self.assertEqual(llm_conversational_renderer.natural_join([]), "")
        # assert one item handling
        self.assertEqual(llm_conversational_renderer.natural_join(["A"]), "A")
        # assert two item handling
        self.assertEqual(llm_conversational_renderer.natural_join(["A", "B"]), "A and B")
        # assert three item handling
        self.assertEqual(llm_conversational_renderer.natural_join(["A", "B", "C"]), "A, B, and C")

    # define a test for the main renderer across intent paths
    def test_render_conversational_answer_paths(self):
        """render_conversational_answer handles intents and fallback"""
        logger.info(f"Running test_render_conversational_answer_paths")
        # build a context with filters text and seed title
        context_dict = {
            "filters_text": "since 2010; ≥ 4.0", 
            "seed_title": "Toy Story"}
        # build example rows
        rows = [
            {"title": "A", "year": 2012, "genres": ["Drama"], "avg_rating": 4.6, "num_ratings": 2000},
            {"title": "B", "year": 2013, "genres": ["Drama"], "avg_rating": 4.2, "num_ratings": 1200},]
        # call renderer for TOP_N
        out_top = llm_conversational_renderer.render_conversational_answer(
            "TOP_N", 
            context_dict, 
            rows, 
            max_items=2)
        # call renderer for RECOMMEND_BY_FILTER
        out_rec =llm_conversational_renderer.render_conversational_answer(
            "RECOMMEND_BY_FILTER", 
            context_dict, 
            rows, 
            max_items=2)
        # call renderer for GET_DETAILS
        out_det = llm_conversational_renderer.render_conversational_answer(
            "GET_DETAILS", 
            context_dict, 
            rows[:1], 
            max_items=1)
        # call renderer for SIMILAR_MOVIES
        out_sim = llm_conversational_renderer.render_conversational_answer(
            "SIMILAR_MOVIES", 
            context_dict, 
            rows, 
            max_items=3)
        # call renderer for fallback unknown
        out_fb = llm_conversational_renderer.render_conversational_answer(
            "UNKNOWN", 
            context_dict, 
            rows, 
            max_items=2)
        # assert count phrase for top
        self.assertIn("I found 2 title(s)", out_top)
        # assert count phrase for recommend
        self.assertIn("I found 2 title(s)", out_rec)
        # assert sentence ends properly for details
        self.assertTrue(out_det.endswith("."))
        # assert similar path includes expected wording
        self.assertIn("you might also enjoy", out_sim)
        # assert fallback uses matches wording
        self.assertIn("Here are the matches", out_fb)



if __name__ == "__main__":
    unittest.main(verbosity=2)
    # cli cmd
    # python -m unittest tests/test_query_responder/test_llm_conversational_renderer.py

