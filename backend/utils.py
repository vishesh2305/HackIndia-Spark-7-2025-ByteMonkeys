# HACKINDIA_PROJECT/backend/utils.py
import logging
import re
import json
import hashlib

# --- AI Verification Logic ---

def process_search_results(search_results, campaign_title, campaign_creator):
    """
    Analyzes search results to determine campaign legitimacy.

    Args:
        search_results (list): List of SearchResults objects from the Google Search tool.
                               Expected format: list[SearchResults(query=str, results=list[PerQueryResult(snippet=str, source_title=str, url=str)])]
        campaign_title (str): The title of the campaign being verified.
        campaign_creator (str): The creator/organizer of the campaign.

    Returns:
        tuple: (bool, str) - (is_legitimate, details_string)
    """
    found_legitimate_links = 0
    found_official_creator_mention = 0
    found_campaign_mention = 0 # Less weighted usually
    found_scam_warnings = 0
    details_list = ["AI Verification Analysis:"]
    processed_urls = set() # Avoid analyzing the same URL multiple times

    # Check if the input structure is as expected
    if not isinstance(search_results, list):
        logging.error(f"process_search_results expected a list, got {type(search_results)}")
        return False, "Internal Error: Invalid search results format received."

    # Keywords for analysis (customize as needed)
    LEGIT_INDICATORS = ["official website", "registered charity", "nonprofit", "foundation", "news", "report", "donation page", "verified", "501(c)(3)", "tax id", "guidestar", "charity navigator"]
    SCAM_INDICATORS = ["scam", "fraud", "warning", "fake", "review scam", "complaint", "beware", "suspicious"]
    # Normalize campaign details for comparison
    norm_title = campaign_title.lower()
    norm_creator = campaign_creator.lower() if campaign_creator else ""


    for result_set in search_results:
         # Validate result_set structure (basic)
        if not hasattr(result_set, 'query') or not hasattr(result_set, 'results'):
            logging.warning(f"Skipping invalid result_set item: {result_set}")
            continue

        query = result_set.query
        details_list.append(f"\n>> Results for query: '{query}'")

        if result_set.results and isinstance(result_set.results, list):
            for item in result_set.results:
                # Validate item structure (basic)
                if not hasattr(item, 'url') or not hasattr(item, 'snippet') or not hasattr(item, 'source_title'):
                     logging.warning(f"Skipping invalid PerQueryResult item: {item}")
                     continue

                if item.url in processed_urls:
                    continue # Skip already processed URL
                processed_urls.add(item.url)

                snippet = (item.snippet or "").lower()
                source_title = (item.source_title or "").lower()
                combined_text = f"{source_title} {snippet}"
                details_list.append(f"  - Source: {item.source_title or 'N/A'}")
                details_list.append(f"    Snippet: {item.snippet[:150] if item.snippet else 'N/A'}...")
                details_list.append(f"    URL: {item.url}")


                # Check for scam indicators
                if any(kw in combined_text for kw in SCAM_INDICATORS):
                    found_scam_warnings += 1
                    details_list.append("    [!] Found potential scam indicator.")

                # Check for legitimacy indicators
                if any(kw in combined_text for kw in LEGIT_INDICATORS):
                    found_legitimate_links += 1
                    details_list.append("    [*] Found potential legitimacy indicator.")

                # Check if creator name appears (especially on non-generic domains)
                if norm_creator and norm_creator in combined_text:
                     found_official_creator_mention += 1
                     details_list.append(f"    [*] Found mention of creator: '{campaign_creator}'.")

                # Check if campaign title appears
                if norm_title in combined_text:
                     found_campaign_mention += 1

        else:
            details_list.append("  - No results found for this specific query.")

    # --- Decision Logic (Example - requires tuning) ---
    details_list.append("\n--- Verification Summary ---")
    is_legit = False

    # Prioritize scam warnings heavily
    if found_scam_warnings > 0:
        is_legit = False
        details_list.append(f"Result: Rejected (Found {found_scam_warnings} potential scam indicators).")
    # Require some evidence of legitimacy if no scam warnings
    elif found_official_creator_mention >= 1 and found_legitimate_links >= 1:
         is_legit = True
         details_list.append(f"Result: Verified (Found mentions of creator ({found_official_creator_mention}) and legitimacy indicators ({found_legitimate_links})).")
    elif found_legitimate_links >= 2: # Allow verification without direct creator mention if other signals are strong
         is_legit = True
         details_list.append(f"Result: Verified (Found {found_legitimate_links} legitimacy indicators, creator mention weak/absent).")
    # Default to reject if insufficient evidence
    else:
        is_legit = False
        details_list.append(f"Result: Rejected (Insufficient positive indicators. Legitimacy indicators: {found_legitimate_links}, Creator mentions: {found_official_creator_mention}, Scam warnings: {found_scam_warnings}).")

    logging.info(f"AI Verification Decision: is_legit={is_legit}")
    return is_legit, "\n".join(details_list)


def prepare_ai_verification(campaign_details):
    """
    Prepares the queries needed for AI verification using the Google Search tool.

    Args:
        campaign_details (dict): Dictionary containing 'title', 'description', 'creatorName', etc.

    Returns:
        tuple: (list | None, str | None) - (queries, error_message)
               Returns a list of queries if successful, or (None, error_message) if input is invalid.
    """
    logging.info(f"Preparing AI verification queries for campaign: {campaign_details.get('title')}")
    title = campaign_details.get('title', '')
    creator = campaign_details.get('creatorName', '')

    if not title:
        return None, "Campaign title is missing, cannot prepare verification queries."

    # Construct search queries
    queries = []
    # Query 1: Exact title + context words
    queries.append(f'"{title}" campaign fundraising donation')
    if creator:
        # Query 2: Title + Creator
        queries.append(f'"{title}" campaign "{creator}"')
        # Query 3: Creator legitimacy check
        queries.append(f'"{creator}" charity OR foundation OR nonprofit registration OR scam') # Add scam keyword here too
    else:
         # Query 2 (No Creator): Broader title check
         queries.append(f'"{title}" charity OR cause OR donation OR scam')

    logging.info(f"Generated AI verification queries: {queries}")
    # Return the queries needed for the tool call
    return queries, None


# --- Hashing Utility ---
def hash_data(data):
    """Hashes a dictionary of data after converting to a sorted JSON string."""
    if not isinstance(data, dict):
        logging.error(f"Attempted to hash non-dictionary data: {type(data)}")
        return None

    try:
        # Ensure consistent order and format for hashing
        sorted_data_string = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(sorted_data_string.encode('utf-8')).hexdigest()
    except TypeError as e:
        logging.error(f"Error JSON serializing data for hashing: {e} - Data: {data}")
        return None