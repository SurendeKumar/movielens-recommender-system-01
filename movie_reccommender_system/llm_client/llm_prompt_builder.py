"""Script for LLM Prompt Building"""
import logging
# basic log info 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
# deifne single logger for context builder
logger=logging.getLogger("LLM_Context_Builder")


# build prompt
def build_llm_prompt(
        context, 
        results, 
        tone="concise", 
        max_items=10):
    """Function to construct a single prompt string for a text-generation LLM.

    Args:
        context (dict): Output of extract_compact_context(), contains:
                {result_count, seed_title, filters_text, time_window, rating_bounds, (optional) titles}
        results (list[dict]): Cleaned and sorted movie rows from normalise_query_output().
        tone (str): Desired response style hint (e.g., "concise", "friendly", "neutral").
        max_items (int): Maximum number of facts included in the facts block.

    Returns:
        str: Prompt text ready to pass to a HF text-generation pipeline.
    """
    # read the number of results from the context
    result_count = context.get("result_count", 0)
    # read the compact filters text for quick query summary
    filters_text = context.get("filters_text")
    # read the human-readable time window text
    time_window_text = context.get("time_window")
    # read the human-readable rating bounds text
    rating_bounds_text = context.get("rating_bounds")
    # read the optional titles list for quick mention
    titles_list = context.get("titles", [])

    # start building a list of prompt sections
    sections = []

    # add a short system-style instruction to keep the model grounded
    sections.append(
        "You are a helpful movie assistant. "
        "Answer using only the facts provided. Do not invent movies or data.")

    # add a context header line that tells the model what the user asked for
    if filters_text:
        sections.append(f"Context: {filters_text}")
    else:
        # fallback to explicit pieces if filters_text is missing
        hint_parts = []
        if time_window_text:
            hint_parts.append(time_window_text)
        if rating_bounds_text:
            hint_parts.append(rating_bounds_text)
        hint_text = "; ".join(hint_parts) if hint_parts else "no explicit filters"
        sections.append(f"Context: {hint_text}")

    # add a brief summary of how many results were found
    sections.append(f"Found: {result_count} result(s).")

    # if we have a titles list, show a quick one-line summary of titles
    if titles_list:
        sections.append("Titles: " + ", ".join(titles_list))

    # build a facts block from the results so the LLM has structured data to rely on
    logger.info(f"Compiling fact blocks from result for prompt context..")
    fact_lines = make_facts_lines(results, max_items=max_items)
    # add a header for the facts block
    sections.append("Facts:")
    # add each fact line as-is to keep formatting deterministic
    sections.extend(fact_lines if fact_lines else ["• No matching items."])

    # add a direct task instruction that guides tone and length
    sections.append(
        f"Task: Write a short, {tone} response that summarizes these results for the user. "
        "If there are no results, say that politely and suggest broadening the filters.")

    # join all sections with newlines to form one prompt string
    prompt_text = "\n".join(sections)

    # return the final prompt text
    return prompt_text




# build factual data from result 
def make_facts_lines(
        results, 
        max_items=10):
    """Function to build deterministic, compact fact lines from cleaned results.

    Args:
        results (list[dict]): List of movie rows from normalise_query_output().
        max_items (int): Maximum number of lines to include.

    Returns:
        list: Containing the 
            - Bullet-point lines each with 
                - title
                - year
                - rating 
                - ratings count
                - genres.
    """
    # create a list to collect formatted lines
    lines = []
    # keep a simple counter to enforce the limit
    count = 0
    # loop through result rows in order (already sorted upstream)
    for row in results:
        # stop if we already reached the limit
        if count >= max_items:
            break
        # read title safely
        title = row.get("title") or ""
        # read year safely
        year = row.get("year")
        # read average rating safely
        avg_rating = row.get("avg_rating")
        # read ratings count safely
        num_ratings = row.get("num_ratings")
        # read genres safely and join them into a short string
        genres_list = row.get("genres") or []
        # join genres with comma for readability
        genres_text = ", ".join(genres_list) if genres_list else ""
        # format rating text with one decimal when available
        rating_text = f"{avg_rating:.1f}/5" if isinstance(avg_rating, (int, float)) else "rating n/a"
        # format ratings count text when available
        count_text = f"{num_ratings} ratings" if isinstance(num_ratings, int) else "count n/a"
        # build the year text part safely
        year_text = f" ({year})" if isinstance(year, int) else ""
        # build the genres text part safely
        genres_bracket = f" — [{genres_text}]" if genres_text else ""
        # compose one bullet line deterministically
        line = f"• {title}{year_text} — {rating_text} — {count_text}{genres_bracket}"
        # append the line to the list
        lines.append(line)
        # increase the counter
        count += 1
    # return all collected lines
    return lines




# if __name__ == "__main__": 

#     from llm_preprocessing import normalise_query_output
#     from llm_context_builder import extract_compact_context
#     from llm_prompt_builder import build_llm_prompt
#     import json

#     # # Step 1: Sample canonical_data input (raw query executor output)
#     # raw_data = {
#     #     "intent": "TOP_N",
#     #     "slots": {
#     #         "min_rating": "4.0",
#     #         "start_year": "2000",
#     #         "end_year": "2010"
#     #     },
#     #     "results": [
#     #         {
#     #             "movieId": 1,
#     #             "title": "The Dark Knight",
#     #             "year": "2008",
#     #             "avg_rating": "4.7",
#     #             "num_ratings": "5000",
#     #             "genres": "Action|Crime|Drama"
#     #         },
#     #         {
#     #             "movieId": 2,
#     #             "title": "Inception",
#     #             "year": "2010",
#     #             "avg_rating": "4.6",
#     #             "num_ratings": "4500",
#     #             "genres": ["Action", "Sci-Fi", "Thriller"]
#     #         }
#     #     ]
#     # }

#     # # Step 2: Canonicalize the raw data (Point 1)
#     # normalised_data = normalise_query_output(raw_data)

#     normalised_data={
#             "intent": "TOP_N",
#             "slots": {
#                 "start_year": 1998
#             },
#             "results": [
#                 {
#                     "movieId": "1",
#                     "title": "Tokyo Fist (1995)",
#                     "year": 1998,
#                     "avg_rating": 4.0,
#                     "num_ratings": 1,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "2",
#                     "title": "Men With Guns (1997)",
#                     "year": 1998,
#                     "avg_rating": 3.5,
#                     "num_ratings": 2,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "3",
#                     "title": "Mercury Rising (1998)",
#                     "year": 1998,
#                     "avg_rating": 3.429,
#                     "num_ratings": 7,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "4",
#                     "title": "Man in the Iron Mask, The (1998)",
#                     "year": 1998,
#                     "avg_rating": 3.417,
#                     "num_ratings": 12,
#                     "genres": [
#                         "Action"
#                     ]
#                 },
#                 {
#                     "movieId": "5",
#                     "title": "Replacement Killers, The (1998)",
#                     "year": 1998,
#                     "avg_rating": 3.308,
#                     "num_ratings": 39,
#                     "genres": [
#                         "Action"
#                     ]
#                 }
#             ]
#         }

#     # # Step 3: Extract compact context (Point 2)
#     # context = extract_compact_context(normalised_data)

#     context_builder_response={
#         "result_count": 5,
#         "seed_title": None,
#         "filters_text": "top titles; since 1998",
#         "time_window": "since 1998",
#         "rating_bounds": None,
#         "titles": [
#             "Tokyo Fist (1995)",
#             "Men With Guns (1997)",
#             "Mercury Rising (1998)",
#             "Man in the Iron Mask, The (1998)",
#             "Replacement Killers, The (1998)"
#         ]
#     }

#     # Step 4: Build the LLM prompt (Point 3)
#     prompt = build_llm_prompt(
#         context_builder_response, 
#         normalised_data["results"], 
#         tone="concise", 
#         max_items=5)

#     # Print the pieces
#     print("=== Canonical Data ===")
#     print(json.dumps(normalised_data, indent=4))

#     print("\n=== Context ===")
#     print(json.dumps(context_builder_response, indent=4))

#     print("\n=== LLM Prompt ===")
#     print(prompt)

#     prompt_builder_output="""
#         === LLM Prompt ===
#         You are a helpful movie assistant. Answer using only the facts provided. Do not invent movies or data.
#         Context: top titles; since 1998
#         Found: 5 result(s).
#         Titles: Tokyo Fist (1995), Men With Guns (1997), Mercury Rising (1998), Man in the Iron Mask, The (1998), Replacement Killers, The (1998)
#         Facts:
#         • Tokyo Fist (1995) (1998) — 4.0/5 — 1 ratings — [Action]
#         • Men With Guns (1997) (1998) — 3.5/5 — 2 ratings — [Action]
#         • Mercury Rising (1998) (1998) — 3.4/5 — 7 ratings — [Action]
#         • Man in the Iron Mask, The (1998) (1998) — 3.4/5 — 12 ratings — [Action]
#         • Replacement Killers, The (1998) (1998) — 3.3/5 — 39 ratings — [Action]
#         Task: Write a short, concise response that summarizes these results for the user. If there are no results, say that politely and suggest broadening the filters.

#         """
