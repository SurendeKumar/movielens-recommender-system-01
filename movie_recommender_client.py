""" Main Client script """
import json
import time
import requests
import logging
# basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",)

# Movielens responder
API_URL = "http://127.0.0.1:8000/api/movielens/answer"


# send a query to the FastAPI server and print the response
def send_movie_query(
        user_query: str, 
        http_session: requests.Session) -> None:
    """Function to send a query to the FastAPI server and display the reponse.

    Args:
        user_query (str): Incoming user query from payload.
        http_session (requests.Session): Persistent HTTP session for sending requests.
    """
    # build the payload to send in the POST request
    payload = {"text": user_query}

    try:
        # send POST request to API with payload
        response = http_session.post(
            API_URL, 
            json=payload, 
            timeout=20)
        # raise an exception if the request returned an error status code
        response.raise_for_status()
        # parse the response JSON into a dictionary
        response_data = response.json()
        # extract only the "answer" field from the nested response
        answer = response_data.get("movielens_prompt_answer_dict", {}).get("answer")

        # check if answer exists then display
        if answer:
            print(f"\nAnswer: {answer}\n")
        else:
            # if no "answer" field, log a warning and print the full response
            logging.warning(f"No 'answer' found in response.")
            logging.info(f"{json.dumps(response_data, indent=2)}")
    except requests.exceptions.RequestException as error:
        logging.error(f"Request failed: {error}")


# Main client
def movielens_sys_client(max_attempts: int = 5):
    """Movielens Client to send movie queries repeatedly until user exits.
        - Displays a welcome message.
        - Prompts the user for input in a loop.
        - Sends each query to the FastAPI server using send_movie_query.
        - Exits when the user types - exit, quit, :q or presses Ctrl+C.

    Args:
        max_attempts (int): Maximum number of input attempts allowed.

    """
    logging.info(f"MovieLens client ready.")
    logging.info(f"Type your movie query, or 'exit'/'quit' to leave. Press Ctrl+C anytime to quit.\n")
    try:
        # create  HTTP session
        with requests.Session() as http_session:
            # infinite loop to keep asking user for input
            for attempt_number in range(1, max_attempts + 1):
                # Show attempt count prompt and read user input
                user_input = input(f"query [{attempt_number}/{max_attempts}]> ").strip()

                # if input is empty then skip this loop and ask again
                if not user_input:
                    print("Empty input. Please type a movie query or 'exit'.")
                    continue

                # if user typed exit or quit, stop the loop
                if user_input.lower() in {"exit", "quit", ":q"}:
                    print("Bye!")
                    break
                # call the function to send the query to FastAPI server
                send_movie_query(user_input, http_session)
                # small pause to avoid overwhelming the server
                time.sleep(0.05)
    
    except KeyboardInterrupt:
        print(f"\nInterrupted. Bye!")
    except Exception as unexpected_error:
        logging.error(f"Unexpected error: {unexpected_error}")







# # movielens recommender system client file
# def movielens_sys_client():
#     try:
#         # ask user for input
#         query = input("Enter the movie query: ").strip()
#         if not query:
#             logging.error(f"No query provided.")
#             return

#         # build JSON payload
#         payload = {"text": query}
#         logging.info(f"Sending request to {API_URL} with payload={payload}")

#         # call FastAPI endpoint
#         resp = requests.post(API_URL, json=payload)
#         resp.raise_for_status()
#         # response JSON
#         data = resp.json()

#         # extract only the answer field
#         answer = data.get("movielens_prompt_answer_dict", {}).get("answer")
#         if answer:
#             print(f"Answer: {answer}")
#         else:
#             logging.warning(f"No 'answer' found in response.")
#             logging.info(f"No answer: {data}")
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Request failed: {e}")
#     except Exception as e:
#         logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    movielens_sys_client()
