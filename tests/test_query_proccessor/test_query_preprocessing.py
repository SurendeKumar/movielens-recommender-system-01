""" Unittest TestSuite -> MovieLens Query preprocessing steps """
import unittest
import logging
from movie_reccommender_system.query_processor import query_preprocessing
# set up logging for this test file
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
# logger- query preprocessing 
logger = logging.getLogger("TestQueryPreprocessing")


# TestSuite - Query Preprocessing
class TestQueryPreprocessing(unittest.TestCase):
    """Test suite for query_preprocessing helpers."""

    # test lower case conversion
    def test_convert_text_to_lower_case(self):
        """Test lower-casing and strip behavior."""
        logger.info(f"Running test_convert_text_to_lower_case")
        # define input text
        text_in = "  Hello World  "
        # call function
        out = query_preprocessing.covnert_text_to_lower_case(text_in)
        # assert expected
        self.assertEqual(out, "hello world")

    # test - split into words corpus
    def test_split_text_into_words_corpus(self):
        """Test splitting into words by spaces."""
        logger.info(f"Running test_split_text_into_words_corpus")
        # define input text
        text_in = "one two  three"
        # call function
        out = query_preprocessing.split_text_into_words_corpus(text_in)
        # assert expected
        self.assertEqual(out, ["one", "two", "three"])

    # test to validate the year value - True
    def test_is_four_digit_year_true(self):
        """Test year detection returns true for valid year."""
        logger.info(f"Running test_is_four_digit_year_true")
        # call function
        out = query_preprocessing.is_four_digit_year("1999")
        # assert expected
        self.assertTrue(out)

    # test to validate the year value - False
    def test_is_four_digit_year_false(self):
        """Test year detection returns false for invalid year."""
        logger.info(f"Running test_is_four_digit_year_false")
        # call function for short value
        out_short = query_preprocessing.is_four_digit_year("99")
        # call function for out of range
        out_range = query_preprocessing.is_four_digit_year("2200")
        # assert expected
        self.assertFalse(out_short)
        self.assertFalse(out_range)

    # test - float parser for ratings
    def test_parse_float_safe_ok(self):
        """Test float parsing returns a number on success."""
        logger.info(f"Running test_parse_float_safe_ok")
        # call function
        out = query_preprocessing.parse_float_safe("3.5")
        # assert expected
        self.assertEqual(out, 3.5)

    #  test - float parser for ratings - none
    def test_parse_float_safe_none(self):
        """Test float parsing returns None on failure."""
        logger.info(f"Running test_parse_float_safe_none")
        # call function
        out = query_preprocessing.parse_float_safe("abc")
        # assert expected
        self.assertIsNone(out)

    # test t0 extract the year value from texts
    def test_extract_year_from_text_last_four(self):
        """Test year extraction from last four characters."""
        logger.info(f"Running test_extract_year_from_text_last_four")
        # call function
        out = query_preprocessing.extract_year_from_text("Jan 01, 1995")
        # assert expected
        self.assertEqual(out, 1995)

    # test - to extract year values from ebedded texts
    def test_extract_year_from_text_embedded(self):
        """Test year extraction finds first four-digit segment."""
        logger.info(f"Running test_extract_year_from_text_embedded")
        # call function
        out = query_preprocessing.extract_year_from_text("released in 2001 summer")
        # assert expected
        self.assertEqual(out, 2001)


    # test - to extract year values from missing texts
    def test_extract_year_from_text_missing(self):
        """Test year extraction returns 0 when not found."""
        logger.info(f"Running test_extract_year_from_text_missing")
        # call function
        out = query_preprocessing.extract_year_from_text("no year here")
        # assert expected
        self.assertEqual(out, 0)



# if __name__ == "__main__":
#     # run the tests with verbosity 2
#     unittest.main(verbosity=2)

    # cli cmd
    # python -m unittest tests/test_query_proccessor/test_query_preprocessing.py
