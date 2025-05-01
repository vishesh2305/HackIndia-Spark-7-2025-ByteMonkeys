import logging
import re
import json
import hashlib

# --- NLTK Sentiment Setup ---
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

analyzer = SentimentIntensityAnalyzer()


def process_search_results():
    return (f"Search Results....")

# --- AI Verification Logic ---

# def process_search_results(search_results):
#     """
#     Analyzes search results to determine campaign legitimacy using sentiment analysis.

#     Args:
#         search_results (list): List of SearchResults objects.

#     Returns:
#         tuple: (is_legitimate: bool, details_string: str)
#     """
#     found_legitimate_links = 0
#     found_official_creator_mention = 0
#     found_scam_warnings = 0
#     cumulative_sentiment_score = 0.0
#     sentiment_analyzed_count = 0

#     details_list = ["AI Verification Analysis (with Sentiment):"]
#     processed_urls = set()

#     if not isinstance(search_results, list):
#         logging.error(f"Expected list of search results, got {type(search_results)}")
#         return False, "Internal Error: Invalid search results format."

#     LEGIT_INDICATORS = [
#         "official website", "registered charity", "nonprofit", "foundation", "news",
#         "report", "donation page", "verified", "501(c)(3)", "tax id", "guidestar", "charity navigator"
#     ]
#     SCAM_INDICATORS = [
#         "scam", "fraud", "warning", "fake", "review scam", "complaint", "beware", "suspicious"
#     ]

#     for result_set in search_results:
#         if not hasattr(result_set, 'query') or not hasattr(result_set, 'results'):
#             logging.warning(f"Skipping invalid result_set item: {result_set}")
#             continue

#         details_list.append(f"\n>> Results for query: '{result_set.query}'")

#         if result_set.results and isinstance(result_set.results, list):
#             if len(result_set.results) == 0:
#                 logging.warning(f"No results found for query: {result_set.query}")
#             for item in result_set.results:
#                 if not hasattr(item, 'url') or not hasattr(item, 'snippet') or not hasattr(item, 'source_title'):
#                     logging.warning(f"Skipping invalid result item: {item}")
#                     continue

#                 if item.url in processed_urls:
#                     continue
#                 processed_urls.add(item.url)

#                 snippet = item.snippet or ""
#                 source_title = item.source_title or "N/A"
#                 combined_text = f"{source_title.lower()} {snippet.lower()}"

#                 details_list.append(f"  - Source: {source_title}")
#                 details_list.append(f"    Snippet: {snippet[:150]}...")
#                 details_list.append(f"    URL: {item.url}")

#                 # --- Sentiment Analysis ---
#                 try:
#                     if snippet.strip():
#                         sentiment_score = analyzer.polarity_scores(snippet)['compound']
#                         cumulative_sentiment_score += sentiment_score
#                         sentiment_analyzed_count += 1
#                         sentiment_label = (
#                             "Positive" if sentiment_score >= 0.05 else
#                             "Negative" if sentiment_score <= -0.05 else
#                             "Neutral"
#                         )
#                         details_list.append(f"    Sentiment Score: {sentiment_score:.2f} ({sentiment_label})")
#                 except Exception as e:
#                     logging.error(f"Sentiment analysis failed for snippet: {e}")
#                     continue

#                 if any(kw in combined_text for kw in SCAM_INDICATORS):
#                     found_scam_warnings += 1
#                     details_list.append("    [!] Potential scam indicator found.")

#                 if any(kw in combined_text for kw in LEGIT_INDICATORS):
#                     found_legitimate_links += 1
#                     details_list.append("    [*] Legitimacy indicator found.")

#         else:
#             details_list.append("  - No results found for this query.")

#     details_list.append("\n--- Verification Summary ---")
#     avg_sentiment = cumulative_sentiment_score / sentiment_analyzed_count if sentiment_analyzed_count > 0 else 0.0
#     details_list.append(f"Average Sentiment Score: {avg_sentiment:.2f} from {sentiment_analyzed_count} results")

#     is_legit = False

#     if found_scam_warnings > 0:
#         is_legit = False
#         details_list.append(f"Result: ❌ Rejected (Found {found_scam_warnings} scam indicators).")
#     elif found_legitimate_links >= 1:
#         if avg_sentiment >= -0.1:
#             is_legit = True
#             details_list.append("Result: ✅ Verified (Strong indicators and sentiment OK).")
#         else:
#             is_legit = False
#             details_list.append("Result: ❌ Rejected (Strong negative sentiment despite indicators).")
#     else:
#         is_legit = False
#         details_list.append("Result: ❌ Rejected (Insufficient legitimacy indicators).")

#     logging.info(f"Final AI Verification: is_legit={is_legit}, sentiment={avg_sentiment:.2f}")
#     return is_legit, "\n".join(details_list)
# --- Keyword Filtering ---
BLACKLISTED_KEYWORDS = [ "fraud", "fake", "illegal", "ponzi", "pyramid scheme"]

def process_verification_data(search_results, campaign_title, campaign_description):
    """
    Verifies campaign legitimacy based on keywords in campaign data and search results.

    Args:
        search_results (list): List of SearchResults objects.
        campaign_title (str): The title of the campaign.
        campaign_description (str): The description of the campaign.

    Returns:
        tuple: (is_legitimate: bool, details_string: str)
    """
    is_legit = True
    details_list = ["AI Verification Analysis (Keyword-Based):"]
    combined_campaign_text = f"{campaign_title.lower()} {campaign_description.lower()}"

    # --- Check for Blacklisted Keywords in Campaign Data ---
    for keyword in BLACKLISTED_KEYWORDS:
        if keyword in combined_campaign_text:
            is_legit = False
            details_list.append(f"  [!] Blacklisted keyword '{keyword}' found in campaign data.")
            logging.warning(f"Campaign Rejected: Blacklisted keyword '{keyword}' found.")
            return is_legit, "\n".join(details_list)

    details_list.append("  - No blacklisted keywords found in campaign data.")

    # --- Basic Check for Search Results ---
    if not search_results or not isinstance(search_results, list) or len(search_results) == 0:
        is_legit = False
        details_list.append("  [!] No search results found. Insufficient information.")
        logging.warning("Campaign Rejected: No search results.")
        return is_legit, "\n".join(details_list)

    details_list.append("  - Search results present. Proceeding with basic analysis.")

    # --- Simple Legitimacy Check (Presence of any result) ---
    for result_set in search_results:
        if result_set and result_set.results and len(result_set.results) > 0:
            is_legit = True  # Consider it legit if any results are found
            details_list.append("  - Found some supporting information online.")
            break  # No need to check further results
        else:
            is_legit = False
            details_list.append("  - No supporting information found in search results.")
            logging.warning("Campaign Rejected: No supporting information found in search results.")

    return is_legit, "\n".join(details_list)

def prepare_ai_verification(campaign_details):
    """
    Prepares search queries for verifying a campaign.

    Args:
        campaign_details (dict): Campaign data.

    Returns:
        tuple: (list of queries, error message if any)
    """
    logging.info(f"Preparing queries for campaign: {campaign_details.get('title')}")
    title = campaign_details.get('title', '')

    if not title:
        return None, "Campaign title missing for query preparation."

    queries = [f'"{title}" campaign fundraising donation']
    queries.append(f'"{title}" charity OR cause OR donation OR scam')

    logging.info(f"Generated queries: {queries}")
    return queries, None


def hash_data(data):
    """
    Hashes a dictionary into a consistent SHA-256 hash.

    Args:
        data (dict): Dictionary to hash.

    Returns:
        str | None: Hash string or None on failure.
    """
    if not isinstance(data, dict):
        logging.error("Data to be hashed must be a dictionary.")
        return None

    try:
        sorted_data_string = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(sorted_data_string.encode('utf-8')).hexdigest()
    except Exception as e:
        logging.error(f"Failed to hash data: {e}")
        return None
