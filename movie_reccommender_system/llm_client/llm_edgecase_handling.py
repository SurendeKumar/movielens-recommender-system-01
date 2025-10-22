# llm_edge_handling.py
# ----------------------------------------
# Point 5: Edge-case handling for movie results before LLM
# Implements detection, suggestions, diversification, quality floor, and context annotations
# ----------------------------------------

# Detect edge cases present in the canonical data
def detect_edge_cases(canonical_data, max_results, min_count_threshold=50):
    """
    Inspect canonical_data and report edge case flags.

    Args:
        canonical_data (dict): Output from canonicalize_query_output().
        max_results (int): Hard cap on items to display.
        min_count_threshold (int): Minimum ratings count considered reliable.

    Returns:
        dict: Flags like {
          "no_results": bool,
          "overflow": bool,
          "sparse_quality": bool,
          "seed_missing": bool,
          "thin_metadata": bool,
          "ties_possible": bool
        }
    """
    # Read intent safely
    intent = canonical_data.get("intent")
    # Read slots safely
    slots = canonical_data.get("slots", {})
    # Read results safely
    results = canonical_data.get("results", [])

    # Compute no results flag
    no_results = len(results) == 0
    # Compute overflow flag
    overflow = len(results) > max_results
    # Compute sparse quality flag (many items with low counts or missing rating)
    low_quality_count = sum(
        1 for r in results
        if r.get("avg_rating") is None or (isinstance(r.get("num_ratings"), int) and r.get("num_ratings") < min_count_threshold)
    )
    # Decide if sparse quality exists (half or more items are low quality)
    sparse_quality = (len(results) > 0) and (low_quality_count >= max(1, len(results) // 2))
    # Compute seed missing flag for SIMILAR_MOVIES
    seed_missing = (intent == "SIMILAR_MOVIES") and (not slots.get("title"))
    # Compute thin metadata flag (many items missing year or genres)
    thin_meta_count = sum(1 for r in results if (r.get("year") is None or not r.get("genres")))
    # Decide if thin metadata exists (half or more items are thin)
    thin_metadata = (len(results) > 0) and (thin_meta_count >= max(1, len(results) // 2))
    # Compute ties possible flag (many items with identical rating/count)
    ties_possible = False
    # Build tuples (rating, count) to check duplicates
    seen_pairs = set()
    # Track duplicates count
    dup_pairs = 0
    # Iterate over results to detect duplicate sort keys
    for r in results:
        pair = (r.get("avg_rating"), r.get("num_ratings"))
        if pair in seen_pairs:
            dup_pairs += 1
        else:
            seen_pairs.add(pair)
    # If we have any duplicates, ties are possible
    if dup_pairs > 0:
        ties_possible = True

    # Return all flags
    return {
        "no_results": no_results,
        "overflow": overflow,
        "sparse_quality": sparse_quality,
        "seed_missing": seed_missing,
        "thin_metadata": thin_metadata,
        "ties_possible": ties_possible,
    }


# Make simple relaxation suggestions from slots
def make_relaxation_suggestions(slots):
    """
    Build at most three short suggestions for broadening the search.

    Args:
        slots (dict): The slots dict from canonical data.

    Returns:
        list[str]: Human-readable suggestions.
    """
    # Create a list to store suggestions
    tips = []
    # Suggest lowering min rating if present
    if slots.get("min_rating") is not None:
        tips.append("Lower the minimum rating by 0.5")
    # Suggest widening the year range if start/end present
    if slots.get("start_year") is not None or slots.get("end_year") is not None:
        tips.append("Expand the year range by ±5 years")
    # Suggest removing a genre if multiple genres present
    genres_raw = slots.get("genres") or slots.get("genre")
    if genres_raw:
        # Normalize to list
        if isinstance(genres_raw, str):
            genres_list = [g.strip() for g in genres_raw.replace("|", ",").split(",") if g.strip()]
        elif isinstance(genres_raw, list):
            genres_list = [str(g).strip() for g in genres_raw if str(g).strip()]
        else:
            genres_list = []
        # If more than one genre, propose dropping one
        if len(genres_list) > 1:
            tips.append(f"Try fewer genres (e.g., remove '{genres_list[-1]}')")
    # Suggest trying alternate title format if title present
    if slots.get("title"):
        tips.append("Try alternate title phrasing (e.g., 'Godfather, The')")
    # Limit to at most three suggestions
    return tips[:3]


# Diversify results by primary genre using round-robin and cap to max_results
def diversify_and_cap(results, max_results):
    """
    Select a diverse subset by primary genre, then cap to max_results.

    Args:
        results (list[dict]): Cleaned and sorted movie rows.
        max_results (int): Hard cap for number of items.

    Returns:
        list[dict]: Diversified and capped list.
    """
    # Group results by their primary genre (first genre in list)
    by_genre = {}
    # Iterate over results to build groups
    for row in results:
        # Read list of genres
        genres_list = row.get("genres") or []
        # Pick first genre as primary, or "Unknown" if none
        primary = genres_list[0] if genres_list else "Unknown"
        # Append row to that genre bucket
        by_genre.setdefault(primary, []).append(row)

    # Create an ordered list of genre keys to iterate round-robin
    genre_keys = list(by_genre.keys())
    # Create output list
    picked = []
    # Use an index to walk within each genre list
    index = 0
    # Continue until we hit the cap or run out of items
    while len(picked) < max_results:
        # Track whether we added something in this round
        added_in_round = False
        # Loop through each genre key
        for g in genre_keys:
            # Get the list for this genre
            bucket = by_genre.get(g, [])
            # If the index is within this bucket, pick that item
            if index < len(bucket):
                picked.append(bucket[index])
                added_in_round = True
                # Stop if we reached the cap
                if len(picked) >= max_results:
                    break
        # If no items were added in this round, we are done
        if not added_in_round:
            break
        # Move to next index for the next round
        index += 1

    # If we still have fewer than max_results and there are leftovers, fill from the original list
    if len(picked) < max_results:
        # Build a set of already picked ids to avoid duplicates
        picked_ids = {p.get("movieId") for p in picked}
        # Iterate original results to fill remaining spots
        for row in results:
            if len(picked) >= max_results:
                break
            if row.get("movieId") not in picked_ids:
                picked.append(row)
                picked_ids.add(row.get("movieId"))

    # Return the diversified and capped list
    return picked


# Apply a simple quality floor preference by ratings count
def apply_quality_floor(results, min_count_threshold=50):
    """
    Split results into preferred (enough ratings) and fallback (the rest).

    Args:
        results (list[dict]): Cleaned and sorted movie rows.
        min_count_threshold (int): Minimum ratings count to be considered preferred.

    Returns:
        tuple(list[dict], list[dict]): (preferred, fallback) lists.
    """
    # Container for preferred items
    preferred = []
    # Container for fallback items
    fallback = []
    # Iterate over all results
    for row in results:
        # Read num_ratings safely
        num = row.get("num_ratings")
        # Decide bucket by threshold
        if isinstance(num, int) and num >= min_count_threshold:
            preferred.append(row)
        else:
            fallback.append(row)
    # Return both lists
    return preferred, fallback


# Annotate the context object with edge-case info
def annotate_context(context, flags, suggestions=None, sampled_from=None):
    """
    Attach edge-case notes and optional suggestion info to the context.

    Args:
        context (dict): Output from extract_compact_context().
        flags (dict): Edge flags from detect_edge_cases().
        suggestions (list[str] | None): Optional user tips.
        sampled_from (dict | None): Optional info like {"total": N, "used": M, "method": "..."}

    Returns:
        dict: New context with 'edge_notes', 'suggestions', and 'sampled_from' as appropriate.
    """
    # Make a shallow copy to avoid mutating input
    new_context = dict(context)
    # Build a list of simple edge notes
    notes = []
    # Add note for no results
    if flags.get("no_results"):
        notes.append("no_results")
    # Add note for overflow
    if flags.get("overflow"):
        notes.append("overflow")
    # Add note for sparse quality
    if flags.get("sparse_quality"):
        notes.append("quality_floor_advised")
    # Add note for seed missing
    if flags.get("seed_missing"):
        notes.append("seed_missing")
    # Add note for thin metadata
    if flags.get("thin_metadata"):
        notes.append("thin_metadata")
    # Add note for ties possible
    if flags.get("ties_possible"):
        notes.append("ties_possible")
    # Attach notes if any
    if notes:
        new_context["edge_notes"] = notes
    # Attach suggestions if provided
    if suggestions:
        new_context["suggestions"] = suggestions[:3]
    # Attach sampled_from info if provided
    if sampled_from:
        new_context["sampled_from"] = sampled_from
    # Return augmented context
    return new_context


# High-level helper to apply edge-case handling end-to-end
def apply_edge_handling(canonical_data, context, max_results=5, min_count_threshold=50, diversify=True):
    """
    Apply edge-case policies to results and update context accordingly.

    Args:
        canonical_data (dict): Output from canonicalize_query_output().
        context (dict): Output from extract_compact_context().
        max_results (int): Hard cap for number of items to keep.
        min_count_threshold (int): Threshold for preferred items by ratings count.
        diversify (bool): Whether to diversify by primary genre on overflow.

    Returns:
        tuple(dict, dict): (updated_canonical_data, updated_context)
    """
    # Read current results
    results = canonical_data.get("results", [])
    # Detect all edge cases
    flags = detect_edge_cases(canonical_data, max_results, min_count_threshold)
    # Prepare suggestions (only useful when no results)
    suggestions = make_relaxation_suggestions(canonical_data.get("slots", {})) if flags.get("no_results") else []
    # Initialize sampled_from info
    sampled_from = None

    # If overflow, optionally diversify then cap
    if flags.get("overflow"):
        # If diversify is requested, use round-robin by primary genre
        if diversify:
            diversified = diversify_and_cap(results, max_results)
            # Add sampled_from info to show original vs used
            sampled_from = {"total": len(results), "used": len(diversified), "method": "genre_round_robin"}
            # Replace results with diversified
            results = diversified
        else:
            # If not diversifying, simply cap
            results = results[:max_results]
            # Record method used
            sampled_from = {"total": len(canonical_data.get("results", [])), "used": len(results), "method": "cap_only"}

    # If sparse quality, prefer items with enough counts while keeping order
    if flags.get("sparse_quality"):
        preferred, fallback = apply_quality_floor(results, min_count_threshold)
        # Merge preferred first, then fallback, and cap to max_results
        merged = preferred + fallback
        results = merged[:max_results]

    # Build updated canonical data with new results
    updated_canonical = dict(canonical_data)
    updated_canonical["results"] = results

    # Annotate the context with flags, suggestions, and sampling info
    updated_context = annotate_context(context, flags, suggestions=suggestions, sampled_from=sampled_from)

    # Return both updated objects
    return updated_canonical, updated_context




if __name__ == "__main__":

    # test_edge_handling.py
    # -------------------------------------------------
    # Test script for llm_edge_handling / Point 5 logic
    # -------------------------------------------------

    # Import json for pretty printing
    import json

    # Import functions from your modules
    from llm_preprocessing import canonicalize_query_output
    from llm_context_builder import extract_compact_context
    # from llm_edge_handling import apply_edge_handling

    # -------- Scenario 1: Overflow results → diversify and cap --------

    # Build raw data with many results to trigger overflow handling
    raw_data_overflow = {
        "intent": "TOP_N",
        "slots": {
            "min_rating": "3.5",
            "start_year": "2000",
            "end_year": "2010",
            "genres": "Action, Drama, Sci-Fi"
        },
        "results": [
            # Action-heavy group
            {"movieId": 1, "title": "The Dark Knight", "year": "2008", "avg_rating": "4.7", "num_ratings": "5000", "genres": "Action|Crime|Drama"},
            {"movieId": 2, "title": "Inception", "year": "2010", "avg_rating": "4.6", "num_ratings": "4500", "genres": ["Action", "Sci-Fi", "Thriller"]},
            {"movieId": 3, "title": "Mad Max: Fury Road", "year": "2015", "avg_rating": "4.5", "num_ratings": "3000", "genres": "Action|Adventure|Sci-Fi"},
            # Drama group
            {"movieId": 4, "title": "The Social Network", "year": "2010", "avg_rating": "4.2", "num_ratings": "2500", "genres": ["Drama"]},
            {"movieId": 5, "title": "There Will Be Blood", "year": "2007", "avg_rating": "4.3", "num_ratings": "2200", "genres": "Drama"},
            # Sci-Fi group
            {"movieId": 6, "title": "District 9", "year": "2009", "avg_rating": "4.1", "num_ratings": "2000", "genres": "Sci-Fi|Thriller"},
            {"movieId": 7, "title": "Moon", "year": "2009", "avg_rating": "4.0", "num_ratings": "1200", "genres": ["Sci-Fi", "Drama"]},
            # Unknown genre fallback
            {"movieId": 8, "title": "Unknown Indie", "year": "2008", "avg_rating": "3.9", "num_ratings": "90", "genres": []}
        ]
    }

    # Canonicalize the overflow data
    canonical_overflow = canonicalize_query_output(raw_data_overflow)

    # Build compact context
    context_overflow = extract_compact_context(canonical_overflow, max_filters_length=140)

    # Apply edge handling with a cap of 5 and diversification ON
    updated_canonical_overflow, updated_context_overflow = apply_edge_handling(
        canonical_overflow,
        context_overflow,
        max_results=5,
        min_count_threshold=50,
        diversify=True
    )

    # Print results for scenario 1
    print("\n=== Scenario 1: Overflow → diversify and cap ===")
    print("\nOriginal count:", len(canonical_overflow["results"]))
    print("Updated count:", len(updated_canonical_overflow["results"]))
    print("\nUpdated Context:")
    print(json.dumps(updated_context_overflow, indent=4))
    print("\nUpdated Results (titles only):")
    print([r["title"] for r in updated_canonical_overflow["results"]])
    


    # -------- Scenario 2: No results → suggestions --------

    # Build raw data with empty results to trigger suggestions
    raw_data_no_results = {
        "intent": "RECOMMEND_BY_FILTER",
        "slots": {
            "min_rating": "4.8",
            "start_year": "2020",
            "end_year": "2021",
            "genres": "Historical, Documentary"
        },
        "results": []
    }

    # Canonicalize the no-results data
    canonical_no_results = canonicalize_query_output(raw_data_no_results)

    # Build compact context
    context_no_results = extract_compact_context(canonical_no_results, max_filters_length=140)

    # Apply edge handling (suggestions should appear)
    updated_canonical_no_results, updated_context_no_results = apply_edge_handling(
        canonical_no_results,
        context_no_results,
        max_results=5,
        min_count_threshold=50,
        diversify=True
    )

    # Print results for scenario 2
    print("\n=== Scenario 2: No results → suggestions ===")
    print("\nUpdated Context:")
    print(json.dumps(updated_context_no_results, indent=4))
    print("\nUpdated Results:")
    print(json.dumps(updated_canonical_no_results["results"], indent=4))

    # -------- Scenario 3: Sparse quality (low num_ratings) --------

    # Build raw data where many items have very low ratings count
    raw_data_sparse_quality = {
        "intent": "RECOMMEND",
        "slots": {
            "min_rating": "3.5"
        },
        "results": [
            {"movieId": 11, "title": "Indie Gem A", "year": "2012", "avg_rating": "4.2", "num_ratings": "12", "genres": "Drama"},
            {"movieId": 12, "title": "Indie Gem B", "year": "2011", "avg_rating": "4.1", "num_ratings": "8", "genres": "Drama"},
            {"movieId": 13, "title": "Widely Rated Hit", "year": "2010", "avg_rating": "4.0", "num_ratings": "1200", "genres": "Drama"},
            {"movieId": 14, "title": "Indie Gem C", "year": "2013", "avg_rating": "4.0", "num_ratings": "25", "genres": "Drama"},
            {"movieId": 15, "title": "Popular Pick", "year": "2014", "avg_rating": "3.9", "num_ratings": "800", "genres": "Drama"}
        ]
    }

    # Canonicalize the sparse-quality data
    canonical_sparse = canonicalize_query_output(raw_data_sparse_quality)

    # Build compact context
    context_sparse = extract_compact_context(canonical_sparse, max_filters_length=140)

    # Apply edge handling with min_count_threshold=50 to prefer widely-rated titles
    updated_canonical_sparse, updated_context_sparse = apply_edge_handling(
        canonical_sparse,
        context_sparse,
        max_results=5,
        min_count_threshold=50,
        diversify=False  # diversification not needed here
    )

    # Print results for scenario 3
    print("\n=== Scenario 3: Sparse quality → prefer widely-rated ===")
    print("\nUpdated Context:")
    print(json.dumps(updated_context_sparse, indent=4))
    print("\nUpdated Results (title → num_ratings):")
    print([f'{r["title"]} → {r.get("num_ratings")}' for r in updated_canonical_sparse["results"]])
