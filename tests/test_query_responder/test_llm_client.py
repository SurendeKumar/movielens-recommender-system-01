""" TestSuite - MovieLens Query Respnder LLM Client """
import unittest
import logging
from types import SimpleNamespace
from movie_reccommender_system.query_responder import llm_client
# set up logging for this test file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# logger- LLM CLient
logger = logging.getLogger("TestLLMClient")


# define the test class for llm_client
class TestLLMClient(unittest.TestCase):
    """Tests for the full non-LLM pipeline in llm_client.generate_query_response"""

    # test for path response generation
    def test_generate_query_response_path(self):
        """generate_query_response produces AnswerResponse with fields"""
        logger.info("Running test_generate_query_response_happy_path")
        # build a request namespace with executor payload
        req = SimpleNamespace(
            executor_payload={
                "intent": "RECOMMEND_BY_FILTER",
                "slots": {"min_rating": "4.0", "start_year": "2010", "title": "A"},
                "results": [
                    {"movieId": "1", "title": "A", "year": 2012, "avg_rating": 4.6, "num_ratings": 2000, "genres": ["Drama"]},
                    {"movieId": "2", "title": "B", "year": 2013, "avg_rating": 4.2, "num_ratings": 1200, "genres": ["Drama"]},],},
            max_results=5,
            diversify=True,)
        # call generate_query_response to get the structured answer
        resp = llm_client.generate_query_response(req)
        # assert the response has the intent field
        self.assertTrue(hasattr(resp, "intent"))
        # assert the response has the answer field
        self.assertTrue(hasattr(resp, "answer"))
        # assert the answer starts with an expected phrase
        self.assertIn("I found", resp.answer)

    # test asserting payload is required
    def test_generate_query_response_requires_payload(self):
        """generate_query_response raises on missing payload"""
        logger.info(f"Running test_generate_query_response_requires_payload")
        # build a request namespace with missing payload
        req = SimpleNamespace(executor_payload=None, max_results=5, diversify=True)
        # assert that calling the function raises ValueError
        with self.assertRaises(ValueError):
            llm_client.generate_query_response(req)


# add the standard unittest entry point
if __name__ == "__main__":
    # run tests with verbosity 2 as requested
    unittest.main(verbosity=2)

    # cli cmd
    # python -m unittest tests/test_query_responder/test_llm_client.py

