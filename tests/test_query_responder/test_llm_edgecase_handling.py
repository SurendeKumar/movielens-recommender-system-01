import unittest
import logging
from movie_reccommender_system.query_responder import llm_edgecase_handling

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TestLLMEdgecaseHandling")


# test - Edgescaser handler LLM
class TestLLMEdgecaseHandling(unittest.TestCase):
    """Tests for edge-case detection and handling in llm_edgecase_handling.py"""
    # test - deteect edge case
    def test_detect_edge_cases_flags(self):
        """detect_edge_cases returns correct flags for simple cases"""
        logger.info(f"Running test_detect_edge_cases_flags")
        # emty data input
        data_empty = {
            "intent": "TOP_N", 
            "slots": {}, 
            "results": []}
        # flags empty
        flags_empty = llm_edgecase_handling.detect_edge_cases(data_empty, max_results=5, min_count_threshold=50)
        self.assertTrue(flags_empty["no_results"])
        self.assertFalse(flags_empty["overflow"])
        # input data overflow
        data_overflow = {
            "intent": "TOP_N", 
            "slots": {}, 
            "results": [{"avg_rating": 4.0, "num_ratings": 10}] * 10}
        # flag overflow
        flags_overflow = llm_edgecase_handling.detect_edge_cases(
            data_overflow, 
            max_results=5,
            min_count_threshold=50)
        self.assertTrue(flags_overflow["overflow"])

    # test - make simple suggestion
    def test_make_simple_suggestions(self):
        """make_simple_suggestions proposes up to three tips"""
        logger.info(f"Running test_make_simple_suggestions")
        # incoming slots
        slots = {
            "min_rating": 4.0, 
            "start_year": 2010, 
            "genres": ["Drama", "Sci-Fi"], "title": "A"}
        # make suggestion
        make_suggestion = llm_edgecase_handling.make_simple_suggestions(slots)
        self.assertLessEqual(len(make_suggestion), 3)
        self.assertTrue(any("Lower the minimum rating" in t for t in make_suggestion))

    # test - diversify and cap, round robin method - 
    def test_diversify_and_cap_round_robin(self):
        """diversify_and_cap spreads picks across genres"""
        logger.info(f"Running test_diversify_and_cap_round_robin")
        rows = [
            {"movieId": "1", "title": "A1", "genres": ["Drama"]},
            {"movieId": "2", "title": "B1", "genres": ["Comedy"]},
            {"movieId": "3", "title": "A2", "genres": ["Drama"]},
            {"movieId": "4", "title": "B2", "genres": ["Comedy"]},]
        # diversify/capp and round robin output
        out = llm_edgecase_handling.diversify_and_cap(rows, max_results=3)
        self.assertEqual(len(out), 3)
        self.assertEqual({r["genres"][0] for r in out[:2]}, {"Drama", "Comedy"})

    # test - quality floor
    def test_apply_quality_floor(self):
        """apply_quality_floor splits preferred and fallback"""
        logger.info(f"Running test_apply_quality_floor")
        rows = [{"num_ratings": 100}, {"num_ratings": 10}, {"num_ratings": 50}]
        # apply quality floor 
        preferred, fallback = llm_edgecase_handling.apply_quality_floor(
            rows, 
            min_count_threshold=50)
        self.assertTrue(all(r["num_ratings"] >= 50 for r in preferred))
        self.assertTrue(all(r["num_ratings"] < 50 for r in fallback))

    # test - annotate context notes
    def test_annotate_context_notes(self):
        """annotate_context attaches flags suggestions and sampling info"""
        logger.info(f"Running test_annotate_context_notes")
        context_dict = {}
        flags = {
            "no_results": True, 
            "overflow": True, 
            "sparse_quality": True, 
            "seed_missing": False, 
            "thin_metadata": True, 
            "ties_possible": True}
        # annotate context
        out = llm_edgecase_handling.annotate_context(
            context_dict, 
            flags, 
            suggestions=["a", "b", "c"], 
            sampled_from={"total": 10, "used": 5, "method": "x"})
        self.assertIn("edge_notes", out)
        self.assertIn("suggestions", out)
        self.assertIn("sampled_from", out)

    # test - entire workflow for edgecase handling
    def test_apply_edgecase_handling_flow(self):
        """apply_edgecase_handling updates normalised_data and context"""
        logger.info(f"Running test_apply_edgecase_handling_flow")
        normalise_query_intent = {"intent": "TOP_N", "slots": {}, "results": [{"movieId": "1", "genres": ["Drama"], "num_ratings": 10}] * 8}
        context_dict = {"filters_text": None}
        # apply edgecase 
        updated_norm, updated_ctx = llm_edgecase_handling.apply_edgecase_handling(
            normalise_query_intent, 
            context_dict, 
            max_results=5,
            min_count_threshold=50, 
            diversify=True)
        self.assertLessEqual(len(updated_norm["results"]), 5)
        self.assertIn("edge_notes", updated_ctx)



# if __name__ == "__main__":
#     unittest.main(verbosity=2)
#     # cli cmd
    # python -m unittest tests/test_query_responder/test_llm_edsgecase_handling.py

