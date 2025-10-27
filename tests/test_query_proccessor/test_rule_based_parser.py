""" Unittest TestSuite -> MovieLens Query Rule Based Parser """
import unittest
import logging
from movie_reccommender_system.query_processor import rules_based_parser
# set up logging for this test file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# logger- query rule based parser
logger = logging.getLogger("TestRuleBasedParser")

# TestSuite - Rules Based Parser
class TestRuleBasedParser(unittest.TestCase):
    """Test suite for rule-based parsing of user text."""
    # test - top N intents from digit
    def test_get_top_number_from_text_digit(self):
        """Test top N extraction with digit form."""
        logger.info(f"Running test_get_top_number_from_text_digit")
        # define text
        text = "show top 7 drama"
        # call function
        out = rules_based_parser.get_top_number_from_text(text)
        # assert expected
        self.assertEqual(out, 7)

    # test - top N intents from text word
    def test_get_top_number_from_text_word(self):
        """Test top N extraction with word form."""
        logger.info(f"Running test_get_top_number_from_text_word")
        # define text
        text = "top five movies"
        # call function
        out = rules_based_parser.get_top_number_from_text(text)
        # assert expected
        self.assertEqual(out, 5)

    # test - top N intents when not present
    def test_get_top_number_from_text_default(self):
        """Test default top N when not present."""
        logger.info(f"Running test_get_top_number_from_text_default")
        # define text
        text = "show best movies"
        # call function
        out = rules_based_parser.get_top_number_from_text(text)
        # assert expected
        self.assertEqual(out, 10)

    # test - years_from for since pattern
    def test_get_years_from_text_since(self):
        """Test year_from extracted with since pattern."""
        logger.info(f"Running test_get_years_from_text_since")
        # define text
        text = "recommend drama since 2012"
        # call function
        y, y_from, y_to = rules_based_parser.get_years_from_text(text)
        # assert expected
        self.assertIsNone(y)
        self.assertEqual(y_from, 2012)
        self.assertIsNone(y_to)

    # test - year patterns with hyphens patterns
    def test_get_years_from_text_range_hyphen(self):
        """Test year range with hyphen pattern."""
        logger.info("Running test_get_years_from_text_range_hyphen")
        # define text
        text = "action 2005-2010"
        # call function
        y, y_from, y_to = rules_based_parser.get_years_from_text(text)
        # assert expected
        self.assertIsNone(y)
        self.assertEqual(y_from, 2005)
        self.assertEqual(y_to, 2010)

    # test - year with between, and patterns
    def test_get_years_from_text_between(self):
        """Test year range with between and pattern."""
        # log test start
        logger.info(f"Running test_get_years_from_text_between")
        # define text
        text = "between 1999 and 2001 comedy"
        # call function
        y, y_from, y_to = rules_based_parser.get_years_from_text(text)
        # assert expected
        self.assertIsNone(y)
        self.assertEqual(y_from, 1999)
        self.assertEqual(y_to, 2001)

    # test - min_raring from text variants
    def test_get_min_rating_from_text_variants(self):
        """Test min rating parser across patterns."""
        logger.info(f"Running test_get_min_rating_from_text_variants")
        # define text list
        texts = [
            "rating 4",
            "rating at least 3",
            "rating greater than 4",
            "min 3.5",
            "minimum 4.5",
            "rating less than 2.5",]
        # call and check first
        r1, c1 = rules_based_parser.get_min_rating_from_text(texts[0])
        # call and check second
        r2, c2 = rules_based_parser.get_min_rating_from_text(texts[1])
        # call and check third
        r3, c3 = rules_based_parser.get_min_rating_from_text(texts[2])
        # call and check fourth
        r4, c4 = rules_based_parser.get_min_rating_from_text(texts[3])
        # call and check fifth
        r5, c5 = rules_based_parser.get_min_rating_from_text(texts[4])
        # call and check sixth
        r6, c6 = rules_based_parser.get_min_rating_from_text(texts[5])
        # assert gte variants
        self.assertEqual((r1, c1), (4.0, "greater_than_or_equal"))
        self.assertEqual((r2, c2), (3.0, "greater_than_or_equal"))
        self.assertEqual((r3, c3), (4.0, "greater_than_or_equal"))
        self.assertEqual((r4, c4), (3.5, "greater_than_or_equal"))
        self.assertEqual((r5, c5), (4.5, "greater_than_or_equal"))
        self.assertEqual((r6, c6), (2.5, "less_than_or_equal"))

    # test - genres from text
    def test_get_genres_from_text(self):
        """Test genre detection including multi-word mapping."""
        logger.info(f"Running test_get_genres_from_text")
        # define text
        text = "I love science fiction and drama"
        # call function
        out = rules_based_parser.get_genres_from_text(text)
        # assert expected
        self.assertIn("Sci-Fi", out)
        self.assertIn("Drama", out)

    # test - title from quotes
    def test_get_title_from_text_quotes(self):
        """Test title extraction from quoted text."""
        logger.info(f"Running test_get_title_from_text_quotes")
        # define text
        text = 'tell me about "Toy Story"'
        # call function
        out = rules_based_parser.get_title_from_text(text)
        # assert expected
        self.assertEqual(out, "Toy Story")

    # test - query parser intents
    def test_user_query_parser_intents(self):
        """Test top-level intent resolution for common patterns."""
        logger.info(f"Running test_user_query_parser_intents")
        # define detail query
        q1 = "tell me about Titanic"
        # parse detail query
        p1 = rules_based_parser.user_query_parser(q1)
        # assert detail intent
        self.assertEqual(p1.intent, "GET_DETAILS")
        # define similar query
        q2 = "movies like Toy Story"
        # parse similar query
        p2 = rules_based_parser.user_query_parser(q2)
        # assert similar intent
        self.assertEqual(p2.intent, "SIMILAR_MOVIES")
        # define top n query
        q3 = "top 5 comedy"
        # parse top n
        p3 = rules_based_parser.user_query_parser(q3)
        # assert top n intent
        self.assertEqual(p3.intent, "TOP_N")
        # define recommend query
        q4 = "recommend drama since 2010 rating at least 4"
        # parse recommend
        p4 = rules_based_parser.user_query_parser(q4)
        # assert recommend intent
        self.assertEqual(p4.intent, "RECOMMEND_BY_FILTER")


# if __name__ == "__main__":
#     # run the tests with verbosity 2
#     unittest.main(verbosity=2)

    # cli cmd
    # python -m unittest tests/test_query_proccessor/test_query_preprocessing.py
