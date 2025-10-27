""" Unittest TestSuite -> MovieLens Query Responder - Preprocessing & Context Builder """
import unittest
import logging
from movie_reccommender_system.query_responder import llm_preprocessing
from movie_reccommender_system.query_responder import llm_context_builder
# set up logging for this test file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# logger- query responder
logger = logging.getLogger("TestLLMPreprocessingAndContext")


# test - llm preprocessing
class TestLLMPreprocessing(unittest.TestCase):
    """Tests for llm_preprocessing helpers and pipeline normalisation."""
    # test - to int/float
    def test_to_int_and_to_float(self):
        """fTest basic converters return expected values and defaults."""
        logger.info(f"Running test_to_int_and_to_float")
        self.assertEqual(llm_preprocessing.to_int("42"), 42)
        # test integer conversion default
        self.assertIsNone(llm_preprocessing.to_int("x"))
        # test float conversion success
        self.assertEqual(llm_preprocessing.to_float("3.5"), 3.5)
        # test float conversion default
        self.assertIsNone(llm_preprocessing.to_float(None))

    # test - input shape validation
    def test_validate_input_shapes(self):
        """Test input validation returns normalized shapes."""
        logger.info(f"Running test_validate_input_shapes")
        # input datz
        data = {
            "intent": "GET_DETAILS", 
            "slots": {"year": "1995"}, 
            "results": [{"movieId": "1", "title": "Toy Story"}]}
        # call validate function
        intent, slots, results = llm_preprocessing.validate_input(data)
        # assert shapes
        self.assertEqual(intent, "GET_DETAILS")
        self.assertIsInstance(slots, dict)
        self.assertIsInstance(results, list)

    # test - nrmalise results and depudes
    def test_normalize_result_row_and_dedupe(self):
        """Test row normalization and deduplication works."""
        logger.info(f"Running test_normalize_result_row_and_dedupe")
        # build two rows with same id
        rows = [
            {"movieId": "1", "title": "Toy Story", "year": "1995", "avg_rating": "4.1", "num_ratings": "900", "genres": "Comedy|Family"},
            {"movieId": "1", "title": "Toy Story", "year": "1995", "avg_rating": 4.1, "num_ratings": 900, "genres": ["Comedy", "Family"]},]
        # normalize each row
        clean = [llm_preprocessing.normalize_result_row(r) for r in rows]
        # drop None rows
        clean = [r for r in clean if r is not None]
        # run dedupe
        deduped = llm_preprocessing.dedupe_and_collect(clean)
        # assert only one remains
        self.assertEqual(len(deduped), 1)
        # assert keys present
        self.assertTrue({"movieId", "title", "year", "avg_rating", "num_ratings", "genres"} <= set(deduped[0].keys()))

    # test - sort/limiting the results
    def test_sort_and_limit_result_size(self):
        """Test sort and limit behavior for TOP_N and GET_DETAILS."""
        logger.info(f"Running test_sort_and_limit_result_size")
        # create unordered results
        rows = [
            {"movieId": "2", "title": "B", "year": 2010, "avg_rating": 4.0, "num_ratings": 100, "genres": []},
            {"movieId": "1", "title": "A", "year": 2012, "avg_rating": 4.5, "num_ratings": 50, "genres": []},
            {"movieId": "3", "title": "C", "year": 2000, "avg_rating": 3.9, "num_ratings": 500, "genres": []},]
        # sort as TOP_N
        top_sorted = llm_preprocessing.sort_and_limit_result_size("TOP_N", rows[:], max_results=2)
        # assert highest rating first and capped to two
        self.assertEqual(len(top_sorted), 2)
        self.assertEqual(top_sorted[0]["movieId"], "1")
        # sort as GET_DETAILS
        details_sorted = llm_preprocessing.sort_and_limit_result_size("GET_DETAILS", rows[:], max_results=5)
        # assert title order for GET_DETAILS
        self.assertEqual([r["title"] for r in details_sorted], ["A", "B", "C"])


    # test - query output
    def test_normalise_query_output_pipeline(self):
        """Test full normalise_query_output pipeline shape and capping."""
        logger.info(f"Running test_normalise_query_output_pipeline")
        # build input payload
        data = {
            "intent": "TOP_N",
            "slots": {"min_rating": "4", "start_year": "2000"},
            "results": [
                {"movieId": "1", "title": "X", "year": "2010", "avg_rating": "4.5", "num_ratings": "100", "genres": "Drama"},
                {"movieId": "2", "title": "Y", "year": "2008", "avg_rating": "4.2", "num_ratings": "90", "genres": "Drama"},
                {"movieId": "3", "title": "Z", "year": "2005", "avg_rating": "4.1", "num_ratings": "80", "genres": "Drama"},],}
        # run pipeline
        out = llm_preprocessing.normalise_query_output(data, max_results=2)
        # assert keys
        self.assertTrue({"intent", "slots", "results"} <= set(out.keys()))
        # assert capping to two
        self.assertEqual(len(out["results"]), 2)


# test - llm context builder
class TestLLMContextBuilder(unittest.TestCase):
    """Tests for llm_context_builder utilities and compact context."""
    # test build time window
    def test_build_time_window(self):
        """Test time window phrases for different year inputs."""
        logger.info(f"Running test_build_time_window")
        # test between phrase
        self.assertEqual(llm_context_builder.build_time_window({"start_year": 2000, "end_year": 2010}), "between 2000 and 2010")
        # test since phrase
        self.assertEqual(llm_context_builder.build_time_window({"start_year": 2000}), "since 2000")
        # test until phrase
        self.assertEqual(llm_context_builder.build_time_window({"end_year": 2010}), "until 2010")
        # test in phrase
        self.assertEqual(llm_context_builder.build_time_window({"year": 2005}), "in 2005")
        # test none
        self.assertIsNone(llm_context_builder.build_time_window({}))

    # test - build ratings bound
    def test_build_rating_bounds(self):
        """Test rating bounds phrasing for min, max, exact."""
        logger.info(f"Running test_build_rating_bounds")
        # test exact
        self.assertEqual(llm_context_builder.build_rating_bounds({"rating": 5.0}), "= 5.0")
        # test between
        self.assertEqual(llm_context_builder.build_rating_bounds({"min_rating": 3.5, "max_rating": 4.5}), "between 3.5 and 4.5")
        # test greater than equal to
        self.assertEqual(llm_context_builder.build_rating_bounds({"min_rating": 4.0}), "≥ 4.0")
        # test lower than equal to
        self.assertEqual(llm_context_builder.build_rating_bounds({"max_rating": 3.0}), "≤ 3.0")
        # test none
        self.assertIsNone(llm_context_builder.build_rating_bounds({}))


    # test - slot genres normalization and filter texts
    def test_normalize_slot_genres_and_filters_text(self):
        """Test genres normalization and combined filters text."""
        logger.info(f"Running test_normalize_slot_genres_and_filters_text")
        # normalize genres from string
        genres = llm_context_builder.normalize_slot_genres({"genres": "Drama|Sci-Fi, Comedy"})
        # assert cleaned list
        self.assertEqual(genres, ["Drama", "Sci-Fi", "Comedy"])
        # build filters
        text = llm_context_builder.build_filters_text(
            "RECOMMEND_BY_FILTER",
            {"genres": ["Drama", "Comedy"], "title": "Toy Story"},
            "since 2000",
            "≥ 4.0",
            max_length=140,)
        # assert parts included
        self.assertIn("recommendations by filters", text)
        self.assertIn("genres=Drama, Comedy", text)
        self.assertIn("since 2000", text)
        self.assertIn("≥ 4.0", text)
        self.assertIn('title="Toy Story"', text)

    # test - compact context
    def test_extract_compact_context(self):
        """Test compact context extraction end to end."""
        logger.info(f"Running test_extract_compact_context")
        # define normalised data
        data = {
            "intent": "TOP_N",
            "slots": {"genres": ["Drama"], "title": "Toy Story", "start_year": 2000, "min_rating": 4.0},
            "results": [
                {"movieId": "1", "title": "A", "year": 2010, "avg_rating": 4.5, "num_ratings": 100, "genres": ["Drama"]},
                {"movieId": "2", "title": "B", "year": 2012, "avg_rating": 4.2, "num_ratings": 90, "genres": ["Drama"]},],}
        # call extract
        ctx = llm_context_builder.extract_compact_context(data, max_filters_length=160)
        # assert key fields
        self.assertEqual(ctx["result_count"], 2)
        self.assertIn("filters_text", ctx)
        self.assertIn("titles", ctx)
        self.assertIn("rating_bounds", ctx)
        self.assertIn("time_window", ctx)




# if __name__ == "__main__":
#     unittest.main(verbosity=2)
    # cli cmd
    # python -m unittest tests/test_query_responder/test_llm_preprocessing_and_context.py

