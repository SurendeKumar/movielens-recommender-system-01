""" Main Client script """
import requests
import logging
# basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",)

API_URL = "http://127.0.0.1:8000/api/movielens/recommender"

# movielens recommender system client file
def movielens_sys_client():
    try:
        # ask user for input
        query = input("Enter the movie query: ").strip()
        if not query:
            logging.error(f"No query provided.")
            return

        # build JSON payload
        payload = {"text": query}
        logging.info(f"Sending request to {API_URL} with payload={payload}")

        # call FastAPI endpoint
        resp = requests.post(API_URL, json=payload)
        resp.raise_for_status()
        # response JSON
        data = resp.json()

        # extract only the answer field
        answer = data.get("movielens_prompt_answer_dict", {}).get("answer")
        if answer:
            logging.info(f"Answer: {answer}")
        else:
            logging.warning(f"No 'answer' found in response.")
            logging.info(f"No answer: {data}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    movielens_sys_client()
