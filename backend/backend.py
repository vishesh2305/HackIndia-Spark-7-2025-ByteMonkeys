# HACKINDIA_PROJECT/backend/backend.py
# --- Corrected Google Search function call ---

import os
import sys
import io
import re
import secrets
import logging
import json
import uuid
from datetime import datetime
import time # Import time for potential delays between API calls
import paypalrestsdk

# --- Add project root to sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End Path Addition ---

from flask import Flask, request, jsonify
from flask_cors import CORS
from web3 import Web3
from pymongo import MongoClient
from bson import ObjectId
from PIL import Image
import pytesseract
import ipfshttpclient
import requests
from thefuzz import fuzz
from bs4 import BeautifulSoup
import requests

from dotenv import load_dotenv
load_dotenv()


GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")
BLACKLISTED_KEYWORDS = [
    "fraud", "fake", "illegal", "scam", "deceptive", "misleading", 
    "ponzi", "pyramid scheme", "personal gain", "self benefit",
    "help me", "support me", "my journey", "i need", "fund my", 
    "pay my", "cover my bills", "rent assistance", "tuition help",
    "emergency funds", "back on my feet", "lost my job", 
    "travel fund", "study abroad", "retreat", "dream project",
    "healing journey", "emotional support", "financial hardship",
    "creative journey", "lifestyle", "vacation", "mental break",
    "any amount helps", "donate to me", "start over", "fresh start",
    "support my cause", "personal expenses",
    "crowdfunding", "quick cash", "need your help", "short on rent",
    "medical bills", "help my family", "single mom", "in debt",
    "cash app", "venmo", "paypal", "zelle", "wire me",
     "unexpected expense", "cover costs",
    "loan repayment", "jobless", "financial recovery", "bail me out",
    "life-changing opportunity", "down payment", "fundraising goal",
    "my dream", "rent due", "utility bills", "eviction notice"
]

PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET")
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox") 


# --- Import Google API Client Library ---
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("\n" + "*"*50)
    print("ERROR: google-api-python-client library not found.")
    print("Please install it using: pip install google-api-python-client")
    print("And add 'google-api-python-client' to your requirements.txt")
    print("*"*50 + "\n")
    # Define as None so the code can load but API calls will fail gracefully
    build = None
    HttpError = None

# Now import from config and utils directly
try:
    from config import settings # Import from config folder using modified path
    # Use direct import from utils.py
    from utils import prepare_ai_verification, process_search_results,hash_data
except ModuleNotFoundError as e:
     print(f"ERROR: Could not import modules. Is the script run from the project root? Or is {e.name} missing?")
     print(f"Project root added to path: {project_root}")
     print(f"Current sys.path: {sys.path}")
     sys.exit(1) # Exit if essential modules can't be loaded


# --- Basic Flask App Setup ---
app = Flask(__name__)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app.logger.setLevel(settings.LOG_LEVEL)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.logger.info(f"Upload folder configured at: {app.config['UPLOAD_FOLDER']}")


# --- Service Connections (IPFS, Web3, MongoDB) ---
# (These remain the same)
ipfs_client = "http://127.0.0.1:5001/webui"
try:
    ipfs_client = ipfshttpclient.connect(settings.IPFS_API_URL)
    ipfs_id = ipfs_client.id()
    app.logger.info(f"Connected to IPFS node: {ipfs_id['ID']} at {settings.IPFS_API_URL}")
except Exception as e:
    app.logger.error(f"ERROR: Could not connect to IPFS at {settings.IPFS_API_URL}: {e}. IPFS features disabled.")
    ipfs_client = None

w3 = None; contract = None; contract_abi = None
try:
    w3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URI))
    if not w3.is_connected(show_traceback=True): app.logger.error(f"ERROR: Failed to connect to Web3 provider at {settings.WEB3_PROVIDER_URI}. Blockchain features disabled."); w3 = None
    else:
        app.logger.info(f"Connected to Web3 provider at {settings.WEB3_PROVIDER_URI}. Chain ID: {w3.eth.chain_id}")
        abi_path = os.path.join(project_root, 'blockchain', 'artifacts', 'contracts', 'CampaignFunding.sol', 'CampaignFunding.json')
        app.logger.info(f"Attempting to load contract ABI from: {abi_path}")
        if os.path.exists(abi_path) and settings.CAMPAIGN_CONTRACT_ADDRESS:
            with open(abi_path, 'r') as f: contract_json = json.load(f); contract_abi = contract_json['abi']
            contract = w3.eth.contract(address=settings.CAMPAIGN_CONTRACT_ADDRESS, abi=contract_abi)
            app.logger.info(f"CampaignFunding contract loaded at address: {settings.CAMPAIGN_CONTRACT_ADDRESS}")
        elif not settings.CAMPAIGN_CONTRACT_ADDRESS: app.logger.error("CAMPAIGN_CONTRACT_ADDRESS not set. Cannot load contract.")
        else: app.logger.error(f"Contract ABI file not found at {abi_path}. Cannot load contract.")
except Exception as e: app.logger.error(f"ERROR: Exception during Web3/Contract setup: {e}", exc_info=True); w3 = None; contract = None

mongo_client = None; db = None; user_collection = None; campaign_collection = None; payment_collection = None
try:
    mongo_client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping'); db = mongo_client[settings.DB_NAME]
    user_collection = db['users']; campaign_collection = db['campaigns']; payment_collection = db['payments']
    app.logger.info(f"Connected to MongoDB at {settings.MONGO_URI}, database: {settings.DB_NAME}")
except Exception as e: app.logger.error(f"ERROR: MongoDB connection failed to {settings.MONGO_URI}: {e}. Database features disabled."); mongo_client = None; db = None; user_collection = None; campaign_collection = None; payment_collection = None

# --- PayPal Configuration ---

if PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET:
    try:
        paypalrestsdk.configure({
            "mode": PAYPAL_MODE, # 'sandbox' or 'live'
            "client_id": PAYPAL_CLIENT_ID,
            "client_secret": PAYPAL_CLIENT_SECRET
        })
        app.logger.info(f"PayPal SDK configured in '{PAYPAL_MODE}' mode.")
    except Exception as pp_err:
        app.logger.error(f"Failed to configure PayPal SDK: {pp_err}", exc_info=True)
        # Consider disabling PayPal features if configuration fails
else:
    app.logger.warning("PayPal Client ID or Secret not found in environment. PayPal features disabled.")
# --- End PayPal Configuration ---


# --- Tesseract Configuration ---
# (Remains the same)
if settings.TESSERACT_PATH and os.path.exists(settings.TESSERACT_PATH): pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH; app.logger.info(f"Using Tesseract from settings: {settings.TESSERACT_PATH}")
else:
    try: version = pytesseract.get_tesseract_version(); app.logger.info(f"Using Tesseract from system PATH. Version: {version}")
    except pytesseract.TesseractNotFoundError: app.logger.error("CRITICAL: Tesseract executable not found. OCR endpoints will fail.")
    except Exception as e: app.logger.error(f"Error checking Tesseract version from PATH: {e}")

# --- Constants for OCR / Validation ---
# (Remain the same)
DATE_FORMATS = [ "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%d-%B-%Y", "%b %d, %Y", "%B %d, %Y", "%Y%m%d" ]
NAME_FUZZINESS_THRESHOLD = 85

# --- Helper Functions (OCR, Normalization, Comparison, IPFS) ---
# (These remain the same - ensure they are defined correctly as in previous responses)
def perform_ocr(image_path):
    # ... (Implementation from previous response) ...
    app.logger.debug(f"Performing OCR on: '{image_path}'")
    try: img = Image.open(image_path); text = pytesseract.image_to_string(img); app.logger.debug(f"RAW OCR Text length: {len(text)}"); return text
    except FileNotFoundError: app.logger.error(f"OCR Error: Image file not found at {image_path}"); return None
    except pytesseract.TesseractNotFoundError: app.logger.error("OCR Error: Tesseract executable not found."); return None
    except Exception as e: app.logger.error(f"OCR Error: An unexpected error occurred: {e}", exc_info=True); return None

def find_name_before_anchor(text, anchor_match):
    # ... (Implementation from previous response) ...
    found_name = None
    try:
        anchor_line_start_index = text.rfind('\n', 0, anchor_match.start()) + 1
        if anchor_line_start_index == 0 and anchor_match.start() > 0: anchor_line_start_index = 0
        elif anchor_line_start_index < 0: anchor_line_start_index = anchor_match.start()
        search_area_before_anchor = text[:anchor_line_start_index].strip()
        potential_name_lines = search_area_before_anchor.split('\n')
        for line in reversed(potential_name_lines):
            potential_name = line.strip()
            if potential_name and re.fullmatch(r"[A-Za-z]{2,}(?:[\s.-]+[A-Za-z.]+)+", potential_name):
                 found_name = potential_name; app.logger.debug(f"Found potential name ('{found_name}') before anchor '{anchor_match.group(0)}'"); break
            elif potential_name: app.logger.debug(f"Stopping name search at non-name line: '{potential_name}'"); break
    except Exception as e: app.logger.debug(f"Error finding name before anchor '{anchor_match.group(0)}': {e}", exc_info=True)
    return found_name

def extract_details_regex(text):
    # ... (Implementation from previous response) ...
    if not text: return None
    extracted_data = {'name': None, 'dob': None}; dob_match_1, dob_match_2 = None, None
    try: dob_pattern_1 = re.compile(r"(?:DOB|D\.O\.B|Birth\s?date|Date\s?of\s?Birth)[\s:./-]*(\d{1,2}[-/.\s]+\d{1,2}[-/.\s]+\d{2,4}|\d{4}[-/.\s]+\d{1,2}[-/.\s]+\d{1,2})", re.IGNORECASE); dob_match_1 = dob_pattern_1.search(text);
    except Exception as e: app.logger.debug(f"Error during DOB Pattern Set 1 search: {e}")
    if dob_match_1: extracted_data['dob'] = dob_match_1.group(1).strip(); app.logger.debug(f"Found DOB using Pattern Set 1: {extracted_data['dob']}")
    if not extracted_data['dob']:
        try: dob_pattern_2 = re.compile(r"(?:^|\n)\s*(\d{4}-\d{2}-\d{2})\s*(?:$|\n)", re.MULTILINE); dob_match_2 = dob_pattern_2.search(text);
        except Exception as e: app.logger.debug(f"Error during DOB Pattern Set 2 search: {e}")
        if dob_match_2: extracted_data['dob'] = dob_match_2.group(1).strip(); app.logger.debug(f"Found DOB using Pattern Set 2: {extracted_data['dob']}")
    name_anchor_match = dob_match_1 or dob_match_2
    if name_anchor_match: extracted_data['name'] = find_name_before_anchor(text, name_anchor_match)
    if not extracted_data['name']:
        app.logger.debug("DOB/Anchor method failed for name, trying fallback heuristics.")
        try:
            potential_name_lines = []
            lines = text.split('\n')
            for i, line in enumerate(lines):
                clean_line = line.strip()
                if re.fullmatch(r"([A-Z][A-Za-z'-.]+)(?:\s+[A-Za-z'-.]+)*\.?", clean_line) and len(clean_line.split()) <= 5:
                     if not re.search(r'\d', clean_line) and clean_line.count('.') <= 1 and clean_line.count('-') <= 1:
                        if not any(kw in clean_line.lower() for kw in ['address', 'male', 'female', 'gender', 'father', 'mother', 'signature', 'issued', 'valid', 'government', 'republic', 'india', 'date', 'birth', 'card', 'income', 'tax', 'account']):
                            potential_name_lines.append(clean_line)
            if potential_name_lines: extracted_data['name'] = potential_name_lines[0]; app.logger.debug(f"Selected potential name (Fallback Heuristic): '{extracted_data['name']}'")
        except Exception as e: app.logger.debug(f"Error during Fallback Name extraction: {e}", exc_info=True)
    app.logger.debug(f"Final Extracted Data: {json.dumps(extracted_data, indent=2)}")
    return extracted_data

def normalize_date(date_str):
    if not date_str:
        return None
    cleaned_date_str = date_str.strip()  # Initialize with a safe default
    cleaned_date_str = re.sub(r'\s*[-/.]\s*', '-', cleaned_date_str)
    cleaned_date_str = re.sub(r'[^\d-]', '', cleaned_date_str)
    for fmt in ["%d-%m-%Y", "%m-%d-%Y", "%Y-%m-%d", "%d-%m-%y", "%m-%d-%y"]:
        try:
            dt = datetime.strptime(cleaned_date_str, fmt)
        except ValueError:
            continue
        if dt.year < 100:
            dt = dt.replace(year=dt.year + 2000 if dt.year < 50 else dt.year + 1900)
        return dt.strftime('%Y-%m-%d')
    app.logger.warning(f"Could not parse date '{date_str}' (cleaned: '{cleaned_date_str}') into YYYY-MM-DD.")
    return None
def normalize_string(s):
    # ... (Implementation from previous response) ...
    if s is None: return None; s = s.strip().lower(); s = re.sub(r'\s+', ' ', s); s = re.sub(r'[^\w\s.-]', '', s); return s

def compare_details(user_input, extracted_data):
    name_match = False
    dob_match = False
    match_details = []
    norm_user = {'name': normalize_string(user_input.get('name')), 'dob': normalize_date(user_input.get('dob'))}
    norm_extracted = {'name': normalize_string(extracted_data.get('name')), 'dob': normalize_date(extracted_data.get('dob'))}
    app.logger.debug(f"Comparing User: {norm_user} vs Extracted: {norm_extracted}")

    # Name Comparison
    if norm_user['name'] and norm_extracted['name']:
        name_similarity = fuzz.token_sort_ratio(norm_user['name'], norm_extracted['name'])
        if name_similarity >= NAME_FUZZINESS_THRESHOLD:
            name_match = True
            match_details.append(f"Name match ({name_similarity}%)")
        else:
            match_details.append(f"Name mismatch (Sim: {name_similarity}%) User:'{norm_user['name']}', Extracted:'{norm_extracted['name']}'")
    elif not norm_user['name'] and norm_extracted['name']:
        match_details.append("Name missing in user input.")
    elif norm_user['name'] and not norm_extracted['name']:
        match_details.append("Name could not be extracted from document.")
    else:
        match_details.append("Name missing in both user input and extracted data.")

    # DOB Comparison
    if norm_user['dob'] and norm_extracted['dob']:
        if norm_user['dob'] == norm_extracted['dob']:
            dob_match = True
            match_details.append(f"DOB match: {norm_user['dob']}")
        else:
            match_details.append(f"DOB mismatch - User:'{norm_user['dob']}', Extracted:'{norm_extracted['dob']}'")
    elif not norm_user['dob'] and norm_extracted['dob']:
        match_details.append("DOB missing in user input.")
    elif norm_user['dob'] and not norm_extracted['dob']:
        match_details.append("DOB could not be extracted from document.")
    else:
        match_details.append("DOB missing in both user input and extracted data.")

    # Validation logic: Pass if DOB matches, regardless of name
    validation_passed = dob_match  # Changed logic
    message = "OCR Data Validation Passed." if validation_passed else "OCR Data Validation Failed."
    details_message = " | ".join(match_details)
    app.logger.info(f"Comparison Result: {message} Details: {details_message}")
    return validation_passed, message, details_message
def store_data_ipfs(data_to_store):
    # ... (Implementation from previous response) ...
    if ipfs_client is None: app.logger.warning("IPFS client not connected. Skipping IPFS data storage."); return None
    try: json_bytes = json.dumps(data_to_store, default=str, sort_keys=True).encode('utf-8'); res = ipfs_client.add_bytes(json_bytes, pin=True); cid = res; app.logger.info(f"Data stored on IPFS. CID: {cid}"); return cid
    except Exception as e: app.logger.error(f"Error storing data on IPFS: {e}", exc_info=True); return None

def store_file_ipfs(file_path):
    # ... (Implementation from previous response) ...
    if ipfs_client is None: app.logger.warning(f"IPFS client not connected. Skipping IPFS file storage for {file_path}."); return None
    if not os.path.exists(file_path): app.logger.error(f"Cannot store file on IPFS: File not found at {file_path}"); return None
    try: res = ipfs_client.add(file_path, pin=True); cid = res['Hash'] if isinstance(res, dict) else res[0]['Hash']; app.logger.info(f"Stored file '{os.path.basename(file_path)}' on IPFS. CID: {cid}"); return cid
    except Exception as e: app.logger.error(f"Error storing file {file_path} on IPFS: {e}", exc_info=True); return None

# --- Google Search Helper Function ---
def perform_Google_Search(queries):
    """
    Performs searches using the Google Custom Search API and returns results
    in a format compatible with process_search_results.
    """
    if not build or not HttpError: # Check if library was imported
        app.logger.error("Google API client library not imported correctly. Cannot perform search.")
        return None
    if not settings.GOOGLE_API_KEY or not settings.GOOGLE_CSE_ID:
        app.logger.error("Google API Key or CSE ID not configured in settings. Cannot perform search.")
        return None

    all_results_structured = []
    try:
        # Build the Custom Search service object
        service = build("customsearch", "v1", developerKey=settings.GOOGLE_API_KEY)
        app.logger.info(f"Google Search service built successfully.")

        for query in queries:
            app.logger.info(f"Performing Google Search for query: '{query}'")
            query_result_structured = {'query': query, 'results': []}
            try:
                res = service.cse().list(
                    q=query,
                    cx=settings.GOOGLE_CSE_ID,
                    num=5 # Request top 5 results per query
                ).execute()

                items = res.get('items', [])
                app.logger.debug(f"Found {len(items)} results for query '{query}'")
                for item in items:
                    # Adapt Google API response
                    result_item = {
                        'snippet': item.get('snippet'),
                        'source_title': item.get('title'),
                        'url': item.get('link'),
                        'publication_time': None, # Placeholder - Add logic if needed
                        'index': None # Placeholder
                    }
                    # Attempt to extract publication time from pagemap if available
                    try:
                         pub_time = item.get('pagemap', {}).get('metatags', [{}])[0].get('article:published_time')
                         if pub_time: result_item['publication_time'] = pub_time
                    except Exception: pass # Ignore errors extracting optional time
                    query_result_structured['results'].append(result_item)

                all_results_structured.append(query_result_structured)
                time.sleep(0.5) # Small delay between queries

            except HttpError as search_err:
                 app.logger.error(f"Google Search API HTTP Error for query '{query}': {search_err}", exc_info=False)
                 if hasattr(search_err, 'resp') and hasattr(search_err.resp, 'status'):
                     app.logger.error(f"API Error Details: Status={search_err.resp.status}, Reason={search_err.resp.reason}, Content={search_err.content}")
                 all_results_structured.append(query_result_structured) # Add with empty results on error
            except Exception as query_err:
                 app.logger.error(f"Unexpected Error during Google Search for query '{query}': {query_err}", exc_info=True)
                 all_results_structured.append(query_result_structured) # Add with empty results

        return all_results_structured

    except Exception as service_err:
        app.logger.error(f"Failed to build Google Search service or general error: {service_err}", exc_info=True)
        return None # Return None if the service itself fails

# --- API Endpoints ---

def scrape_website_data(url, campaign_id):
    """
    Performs basic web scraping of a website and logs the data.
    This function does not affect the campaign creation process.

    Args:
        url (str): The URL to scrape.
        campaign_id (str): The ID of the campaign being processed.
    """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        soup = BeautifulSoup(response.content, "html.parser")

        # --- Example Scraping (Adapt to your needs!) ---
        title = soup.title.text if soup.title else "No Title"
        paragraphs = [p.text for p in soup.find_all("p")]

        log_data = {
            "campaign_id": campaign_id,
            "scraped_url": url,
            "page_title": title,
            "paragraphs": paragraphs[:5]  # Limit to first 5 paragraphs
        }
        app.logger.info(f"Scraped data from {url}: {json.dumps(log_data, indent=2)}")

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Web scraping failed for {url}: {e}")
    except Exception as e:
        app.logger.error(f"Unexpected error during web scraping: {e}", exc_info=True)


@app.route('/api/health', methods=['GET'])
def health_check():
    # ... (Implementation from previous response) ...
    services = { "face_api_reachable": False, "ipfs_connected": False, "web3_connected": False, "mongodb_connected": False, "tesseract_found": False, "google_api_configured": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID)}
    try:
        if settings.FACE_API_URL: response = requests.get(settings.FACE_API_URL.replace("/compare_faces", "/"), timeout=2); services["face_api_reachable"] = response.ok
    except Exception: pass
    try:
         if ipfs_client: ipfs_client.id(); services["ipfs_connected"] = True
    except Exception: pass
    try:
         if w3 and w3.is_connected(): w3.eth.block_number; services["web3_connected"] = True
    except Exception: pass
    try:
         if mongo_client: mongo_client.admin.command('ping'); services["mongodb_connected"] = True
    except Exception: pass
    try:
         pytesseract.get_tesseract_version(); services["tesseract_found"] = True
    except Exception: pass
    return jsonify({ "service": "HACKINDIA Backend", "status": "running", "version": "1.1.0", "dependencies": services }), 200

@app.route('/api/face_recognize', methods=['POST'])
def face_recognize():
    # ... (Implementation remains the same) ...
    app.logger.info("Received request at /api/face_recognize")
    if 'id_photo' not in request.files or 'selfie' not in request.form: return jsonify({'error': 'Missing id_photo or selfie file/data'}), 400
    id_photo_file = request.files['id_photo']; selfie_data = request.form['selfie']
    if id_photo_file.filename == '': return jsonify({'error': 'ID Photo filename is empty'}), 400
    face_api_url = settings.FACE_API_URL
    if not face_api_url: app.logger.error("Face Recognition API URL not configured in settings."); return jsonify({'error': 'Face Recognition API URL not configured'}), 500
    id_photo_file.seek(0); face_data = {'selfie': selfie_data}; face_files = {'id_photo': (id_photo_file.filename, id_photo_file, id_photo_file.mimetype)}
    app.logger.info(f"Calling face recognition service at {face_api_url}...")
    try:
        face_response = requests.post(face_api_url, data=face_data, files=face_files, timeout=20)
        face_response.raise_for_status(); face_result = face_response.json(); app.logger.debug(f"Face service JSON response: {face_result}")
        if face_result.get('match'):
            app.logger.info("Face match successful."); id_photo_file.seek(0); file_ext = os.path.splitext(id_photo_file.filename)[1].lower(); allowed_extensions = ['.png', '.jpg', '.jpeg'];
            if file_ext not in allowed_extensions: return jsonify({'error': f'Invalid file type: {file_ext}. Allowed: {allowed_extensions}'}), 400
            secure_filename = f"id_{secrets.token_hex(8)}{file_ext}"; temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename)
            try: id_photo_file.save(temp_image_path); app.logger.info(f"ID photo saved temporarily: {temp_image_path}"); return jsonify({'match': True, 'message': face_result.get('message', 'Face match successful!'), 'imageId': secure_filename}), 200
            except Exception as save_err: app.logger.error(f"Error saving temporary ID photo: {save_err}", exc_info=True); return jsonify({'error': 'Failed to save ID photo after successful match'}), 500
        else: app.logger.info("Faces do not match according to face service."); return jsonify({'match': False, 'message': face_result.get('message', 'Faces do not match.')}), 200
    except requests.exceptions.ConnectionError: app.logger.error(f"ConnectionError: Could not connect to Face Recognition service at {face_api_url}."); return jsonify({'error': 'Could not connect to face recognition service.'}), 503
    except requests.exceptions.Timeout: app.logger.error(f"Timeout: Request to face recognition service timed out."); return jsonify({'error': 'Face recognition service timed out.'}), 504
    except requests.exceptions.RequestException as req_err: error_detail = f"Error communicating with face service: {req_err}"

    try: error_detail = req_err.response.json().get('error', req_err.response.text)
    except Exception as e:
        pass; app.logger.error(f"RequestException calling face service: {error_detail}", exc_info=True); return jsonify({'error': error_detail}), 502
        app.logger.error(f"Unexpected error in /api/face_recognize: {e}", exc_info=True); return jsonify({'error': 'An internal server error occurred.'}), 500

@app.route('/api/validate_ocr', methods=['POST'])
def validate_ocr():
    # ... (Implementation remains the same) ...
    app.logger.info("Received request at /api/validate_ocr"); temp_image_path = None
    if db is None or user_collection is None: app.logger.error("MongoDB not available for OCR validation."); return jsonify({'error': 'Database service unavailable'}), 503
    try:
        if not request.is_json: return jsonify({"error": "Request must be JSON"}), 415
        data = request.get_json(); user_name = data.get('name'); user_dob = data.get('dob'); image_id = data.get('imageId')
        if not all([user_name, user_dob, image_id]): missing = [k for k, v in {'Name': user_name, 'DOB': user_dob, 'Image ID': image_id}.items() if not v]; return jsonify({'is_valid': False, 'message': f'Missing required fields: {", ".join(missing)}'}), 400
        if '..' in image_id or '/' in image_id or '\\' in image_id: return jsonify({'is_valid': False, 'message': 'Invalid image ID format.'}), 400
        temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_id)
        if not os.path.exists(temp_image_path): app.logger.error(f"Image file not found for ID: {image_id} at path: {temp_image_path}"); return jsonify({'is_valid': False, 'message': 'Error: Image file not found (session expired?).'}), 404
        raw_text = perform_ocr(temp_image_path)
        if raw_text is None: return jsonify({'is_valid': False, 'message': 'OCR processing failed.'}), 500
        extracted_details = extract_details_regex(raw_text) or {}
        if not extracted_details.get('name') or not extracted_details.get('dob'): app.logger.warning(f"Could not extract Name or DOB from OCR for image {image_id}. Comparison will likely fail.")
        user_input_data = {"name": user_name, "dob": user_dob}
        validation_passed, message, details_message = compare_details(user_input_data, extracted_details)
        if not validation_passed: return jsonify({'is_valid': False, 'message': message, 'details': details_message}), 200
        app.logger.info(f"OCR validation passed for image {image_id}.")
        validated_name = extracted_details.get('name', user_name); validated_dob = normalize_date(extracted_details.get('dob', user_dob))
        if not validated_name: app.logger.error(f"Cannot proceed: Validated name is empty for image {image_id}."); return jsonify({'is_valid': True, 'message': 'Validation passed, but error preparing data (Name empty).'}), 500
        id_photo_cid = store_file_ipfs(temp_image_path) or 'N/A - IPFS file storage failed'
        user_details_for_hash = {'name': validated_name, 'dob_normalized': validated_dob, 'id_photo_cid': id_photo_cid}
        data_hash = hash_data(user_details_for_hash)
        if not data_hash: app.logger.error("Failed to hash user details."); return jsonify({'is_valid': True, 'message': 'Validation passed, but failed to hash data.'}), 500
        tx_hash = 'N/A - Blockchain interaction skipped'
        if contract and w3 and contract_abi:
            app.logger.info(f"Attempting to store validation hash {data_hash} on blockchain...")
            try:
                if not any(f['name'] == 'storeValidationHash' for f in contract_abi if f['type'] == 'function'): app.logger.error("Function 'storeValidationHash' not found in loaded contract ABI."); tx_hash = 'N/A - Contract function mismatch'
                else:
                    accounts = w3.eth.accounts
                    if not accounts: tx_hash = 'N/A - No accounts available'; app.logger.error("No Ethereum accounts available via Web3 provider.")
                    else:
                        sender_account = accounts[0]; hex_hash = data_hash if data_hash.startswith('0x') else '0x' + data_hash
                        try: gas_estimate = contract.functions.storeValidationHash(hex_hash).estimate_gas({'from': sender_account}); app.logger.info(f"Estimated gas for storeValidationHash: {gas_estimate}"); gas_limit = gas_estimate + 50000
                        except Exception as est_err: app.logger.warning(f"Gas estimation failed for storeValidationHash (may revert): {est_err}. Using fixed limit."); gas_limit = 300000
                        tx = contract.functions.storeValidationHash(hex_hash).transact({'from': sender_account, 'gas': gas_limit})
                        receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=120)
                        if receipt.status == 1: tx_hash = receipt.transactionHash.hex(); app.logger.info(f"Validation Hash stored on blockchain. Tx: {tx_hash}")
                        else: tx_hash = f'N/A - Tx {receipt.transactionHash.hex()} Failed (Status 0)'; app.logger.error(f"Blockchain transaction failed for storeValidationHash. Tx: {receipt.transactionHash.hex()}")
            except Exception as blockchain_e: app.logger.error(f"Error storing hash on blockchain: {blockchain_e}", exc_info=True); tx_hash = f'N/A - Blockchain error: {str(blockchain_e)[:100]}'
        else: app.logger.warning("Web3/Contract not available. Skipping blockchain storage for validation hash.")
        app.logger.info(f"Saving validated user data to MongoDB for: {validated_name}")
        try:
             mongo_document = {'user_name': validated_name, 'dob_normalized': validated_dob, 'validation_data_hash': data_hash, 'validation_tx_hash': tx_hash, 'validated_at_utc': datetime.utcnow().isoformat() + "Z", 'id_photo_cid': id_photo_cid, 'original_image_id': image_id }
             result = user_collection.update_one({'user_name': validated_name}, {'$set': mongo_document}, upsert=True)
             app.logger.info(f"User validation data saved/updated in MongoDB. Matched: {result.matched_count}, Modified: {result.modified_count}, UpsertedID: {result.upserted_id}")
             return jsonify({'is_valid': True, 'message': 'User validated successfully. Data stored.', 'details': details_message, 'data_hash': data_hash, 'tx_hash': tx_hash, 'user_name': validated_name, 'id_photo_cid': id_photo_cid }), 200
        except Exception as mongo_e: app.logger.error(f"Error saving user validation data to MongoDB: {mongo_e}", exc_info=True); return jsonify({'is_valid': True, 'message': 'Validation passed, but failed to save data to database.'}), 500
    except Exception as e: app.logger.error(f"Unexpected error in /api/validate_ocr: {e}", exc_info=True); return jsonify({'error': 'An internal server error occurred.'}), 500
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            try: os.remove(temp_image_path); app.logger.info(f"Temporary file {temp_image_path} deleted.")
            except Exception as e: app.logger.error(f"Error deleting temporary file {temp_image_path}: {e}")

@app.route('/api/auth/status/<user_identifier>', methods=['GET'])
def get_auth_status(user_identifier):
    # ... (Implementation remains the same) ...
    if user_collection is None: return jsonify({'error': 'Database service not available'}), 503
    try: user_data = user_collection.find_one({'user_name': user_identifier})
    except Exception as e: app.logger.error(f"Error checking auth status for '{user_identifier}': {e}", exc_info=True); return jsonify({'error': 'Error checking authentication status'}), 500
    if user_data and user_data.get('validation_data_hash'): app.logger.debug(f"Auth status check for '{user_identifier}': Found and Validated."); return jsonify({'isValidated': True}), 200
    else: app.logger.debug(f"Auth status check for '{user_identifier}': Not found or not validated."); return jsonify({'isValidated': False}), 200


# --- Campaign Endpoints ---

@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    """Creates a new campaign, stores details on IPFS, and performs AI verification (if necessary)."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415
    if campaign_collection is None:
        return jsonify({'error': 'DB unavailable'}), 503

    data = request.get_json()
    required_fields = ['title', 'description', 'goalAmount', 'creatorName']
    if not all(field in data for field in required_fields):
        missing = [f for f in required_fields if f not in data]
        return jsonify({'error': f'Missing required campaign fields: {", ".join(missing)}'}), 400

    app.logger.info(
        f"Received campaign creation request from '{data['creatorName']}' for title: '{data['title']}'")

    campaign_details = {
        'title': data['title'],
        'description': data['description'],
        'goalAmount': data.get('goalAmount', '0'),
        'creatorName': data['creatorName'],
        'amountRaised': '0',
        'status': 'pending_verification',
        'details_ipfs_cid': None,
        'campaign_creation_tx_hash': None,
        'verification_result': None,
        'created_at_utc': datetime.utcnow().isoformat() + "Z",
        'updated_at_utc': datetime.utcnow().isoformat() + "Z",
    }

    campaign_details_cid = store_data_ipfs(campaign_details) or 'N/A - IPFS Error'
    campaign_details['details_ipfs_cid'] = campaign_details_cid # Added to store the IPFS CID

    try:
        insert_result = campaign_collection.insert_one(campaign_details.copy())
        campaign_id = insert_result.inserted_id
        campaign_details['_id'] = str(campaign_id)  # Convert ObjectId to string for JSON serialization
    except Exception as mongo_e:
        app.logger.error(f"Error saving campaign to MongoDB: {mongo_e}", exc_info=True)
        return jsonify({'error': 'Failed to save campaign to database'}), 500

    is_blacklisted = False
    combined_campaign_text = f"{campaign_details['title'].lower()} {campaign_details['description'].lower()}"
    for keyword in BLACKLISTED_KEYWORDS:
        if keyword in combined_campaign_text:
            is_blacklisted = True
            campaign_details['status'] = 'rejected'
            campaign_details['verification_result'] = f"Campaign rejected: Blacklisted keyword '{keyword}' found."
            campaign_collection.update_one({'_id': campaign_id},
                                            {'$set': {'status': 'rejected',
                                                      'verification_result': campaign_details['verification_result'],
                                                      'updated_at_utc': datetime.utcnow().isoformat() + "Z"}})
            return jsonify(campaign_details), 201
            break  # Exit loop as soon as a keyword is found

    # If no blacklisted keywords are found, proceed without Google Search
    if not is_blacklisted:
        campaign_details['status'] = 'verified'  # Or any status you deem appropriate for direct approval
        campaign_details['verification_result'] = "No blacklisted keywords found. Skipping AI verification."
        campaign_collection.update_one({'_id': campaign_id},
                                        {'$set': {'status': 'verified',
                                                  'verification_result': campaign_details['verification_result'],
                                                  'updated_at_utc': datetime.utcnow().isoformat() + "Z"}})
        return jsonify(campaign_details), 201



@app.route('/api/campaigns', methods=['GET'])
def get_campaigns():
    # ... (Implementation remains the same) ...
    if campaign_collection is None: return jsonify({'error': 'Database service not available'}), 503
    try: status_filter = request.args.get('status'); query = {};
    except Exception as e: app.logger.error(f"Error getting status filter: {e}"); status_filter=None; query={}
    if status_filter and status_filter != 'all': query['status'] = status_filter
    elif not status_filter: query['status'] = 'verified'
    app.logger.debug(f"Fetching campaigns with query: {query}")
    try: campaigns = list(campaign_collection.find(query).sort("created_at_utc", -1))
    except Exception as e: app.logger.error(f"Error fetching campaigns from DB: {e}", exc_info=True); return jsonify({'error': 'Failed to fetch campaigns from database'}), 500
    for campaign in campaigns: campaign['_id'] = str(campaign['_id'])
    return jsonify(campaigns), 200

@app.route('/api/campaigns/<campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    # ... (Implementation remains the same) ...
    if campaign_collection is None: return jsonify({'error': 'Database service not available'}), 503
    try: oid = ObjectId(campaign_id)
    except Exception: return jsonify({'error': 'Invalid campaign ID format'}), 400
    try:
        campaign = campaign_collection.find_one({'_id': oid})
        if campaign: campaign['_id'] = str(campaign['_id']); return jsonify(campaign), 200
        else: return jsonify({'error': 'Campaign not found'}), 404
    except Exception as e: app.logger.error(f"Error fetching campaign {campaign_id}: {e}", exc_info=True); return jsonify({'error': 'Failed to fetch campaign'}), 500


@app.route('/api/campaigns/<campaign_id>/fund', methods=['POST'])
def record_funding(campaign_id):
    # ... (Implementation remains the same) ...
    if not request.is_json: return jsonify({"error": "Request must be JSON"}), 415
    if campaign_collection is None or payment_collection is None: return jsonify({'error': 'Database service not available'}), 503
    try: campaign_oid = ObjectId(campaign_id)
    except Exception: return jsonify({'error': 'Invalid campaign ID format'}), 400
    data = request.get_json()
    required_fields = ['transactionHash', 'amount', 'funderAddress']
    if not all(field in data for field in required_fields): missing = [f for f in required_fields if f not in data]; return jsonify({'error': f'Missing required payment fields: {", ".join(missing)}'}), 400
    app.logger.info(f"Received funding record for campaign {campaign_id}. Tx: {data['transactionHash']}")
    try: campaign = campaign_collection.find_one({'_id': campaign_oid, 'status': 'verified'})
    except Exception as e: app.logger.error(f"DB error finding campaign {campaign_id}: {e}"); return jsonify({'error': 'Database error finding campaign'}), 500
    if not campaign: return jsonify({'error': 'Campaign not found or not active for funding'}), 404
    if w3 and w3.is_connected():
        try:
             tx_receipt = w3.eth.get_transaction_receipt(data['transactionHash'])
             if not tx_receipt: app.logger.warning(f"Tx {data['transactionHash']} not found on chain."); return jsonify({'error': 'Blockchain transaction hash not found or not yet mined.'}), 400
             if tx_receipt['status'] == 0: app.logger.warning(f"Tx {data['transactionHash']} failed on chain (Status 0)."); return jsonify({'error': 'Blockchain transaction failed.'}), 400
             app.logger.info(f"Tx {data['transactionHash']} verified on chain. Status: {tx_receipt['status']}")
        except Exception as web3_e: app.logger.error(f"Error verifying transaction {data['transactionHash']} on chain: {web3_e}")
    else: app.logger.warning("Web3 not connected, skipping blockchain transaction verification.")
    payment_details = {'campaignId': campaign_oid, 'campaignMongoId': str(campaign_oid), 'transactionHash': data['transactionHash'], 'amount_ether': data['amount'], 'funderAddress': data['funderAddress'], 'timestamp_utc': datetime.utcnow().isoformat() + "Z", 'payment_details_ipfs_cid': None }
    payment_cid = store_data_ipfs(payment_details)
    payment_details['payment_details_ipfs_cid'] = payment_cid or 'N/A - IPFS Error'
    try:
        payment_result = payment_collection.insert_one(payment_details.copy())
        app.logger.info(f"Payment record saved to MongoDB. ID: {payment_result.inserted_id}, Tx: {data['transactionHash']}")
    except Exception as mongo_e: app.logger.error(f"Error saving payment record to MongoDB: {mongo_e}", exc_info=True); return jsonify({'error': 'Failed to save payment record to database.'}), 500
    try: # Update amount raised
        current_raised_str = campaign.get('amountRaised', '0'); new_fund_ether_str = data['amount']
        try:
            current_raised_wei = int(current_raised_str); new_fund_wei = w3.to_wei(new_fund_ether_str, 'ether') if w3 else int(float(new_fund_ether_str) * 1e18)
            total_raised_wei = current_raised_wei + new_fund_wei; total_raised_wei_str = str(total_raised_wei)
        except ValueError as convert_err: app.logger.error(f"Invalid number format for amount conversion. Campaign: {campaign_id}, Error: {convert_err}"); total_raised_wei_str = current_raised_str
        except Exception as e: app.logger.error(f"Unexpected error during amount conversion: {e}"); total_raised_wei_str = current_raised_str
        update_campaign = campaign_collection.update_one({'_id': campaign_oid}, {'$set': {'amountRaised': total_raised_wei_str, 'updated_at_utc': datetime.utcnow().isoformat() + "Z"}})
        if update_campaign.modified_count == 1: app.logger.info(f"Campaign {campaign_id} amountRaised updated.")
        else: app.logger.warning(f"Campaign {campaign_id} amountRaised update did not modify document.")
    except Exception as update_e: app.logger.error(f"Error updating campaign amountRaised for {campaign_id}: {update_e}", exc_info=True)
    payment_details['_id'] = str(payment_result.inserted_id); payment_details.pop('campaignId', None)
    return jsonify(payment_details), 201


@app.route('/api/paypal/create-order', methods=['POST'])
def create_paypal_order():
    # Check if MongoDB collection is available - CORRECTED CHECK
    if campaign_collection is None:
         app.logger.error("MongoDB campaign_collection is not initialized.")
         return jsonify({'error': 'Database service not available'}), 503

    # Check if PayPal SDK was configured
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
         app.logger.error("PayPal Client ID or Secret not configured.")
         return jsonify({"error": "PayPal is not configured on the server."}), 503

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    data = request.get_json()
    campaign_id = data.get('campaignId')
    # Expect amount as string like "10.50"
    amount_str = data.get('amount')
    # PayPal requires standard currency codes (e.g., USD, EUR, INR)
    currency_code = data.get('currency', 'USD') # Default or get from request

    if not campaign_id or not amount_str:
        return jsonify({"error": "Missing campaignId or amount"}), 400

    # Basic amount validation
    try:
        amount_val = float(amount_str)
        if amount_val <= 0: raise ValueError("Amount must be positive")
    except ValueError:
         return jsonify({"error": "Invalid amount format (must be positive number)"}), 400

    # Fetch campaign title for description (optional but good)
    campaign_title = f"Campaign {campaign_id}" # Default
    # Use the corrected check for campaign_collection before using it
    if campaign_collection is not None:
        try:
            # Ensure campaign_id is a valid ObjectId before querying
            campaign_oid = ObjectId(campaign_id)
            campaign = campaign_collection.find_one({'_id': campaign_oid})
            if campaign:
                campaign_title = campaign.get('title', campaign_title)
            else:
                app.logger.warning(f"Campaign {campaign_id} not found for PayPal order description.")
        except Exception as e:
             app.logger.warning(f"Could not fetch campaign title for PayPal order ({campaign_id}): {e}")
    else:
        app.logger.warning("MongoDB not initialized, cannot fetch campaign title for PayPal order.")


    app.logger.info(f"Creating PayPal order for Campaign {campaign_id}, Amount: {amount_str} {currency_code}")

    try:
        # Create PayPal Payment object
        payment = paypalrestsdk.Payment({
            "intent": "sale", # 'sale' for immediate capture
            "payer": { "payment_method": "paypal" },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Fund: {campaign_title[:120]}", # Limit name length
                        "sku": f"CAMP-{campaign_id}",
                        "price": amount_str,
                        "currency": currency_code,
                        "quantity": 1 }]
                },
                "amount": {
                    "total": amount_str,
                    "currency": currency_code },
                "description": f"Contribution to campaign ID: {campaign_id}" # Limit desc length
            }],
            # Redirect URLs often not needed for client-side JS capture,
            # but set placeholders or frontend URLs if required.
            "redirect_urls": {
                "return_url": request.host_url + "payment/success", # Example
                "cancel_url": request.host_url + "payment/cancel"   # Example
            }})

        # Create payment on PayPal
        if payment.create():
            app.logger.info(f"PayPal Order created successfully. Order ID: {payment.id}")
            # Return the 'id' which is the Order ID the frontend needs
            return jsonify({'orderID': payment.id}), 201
        else:
            app.logger.error(f"PayPal Order creation failed: {payment.error}")
            # Provide specific error details if possible
            error_details = payment.error if isinstance(payment.error, dict) else {'message': str(payment.error)}
            return jsonify({"error": "Failed to create PayPal order", "details": error_details}), 500

    except Exception as e:
        app.logger.error(f"Error creating PayPal order: {e}", exc_info=True)
        return jsonify({"error": "Internal server error during PayPal order creation"}), 500



@app.route('/api/paypal/capture-order', methods=['POST'])
def capture_paypal_order():
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
         return jsonify({"error": "PayPal is not configured on the server."}), 503
    if campaign_collection is None or payment_collection is None:
         return jsonify({'error': 'Database service not available'}), 503

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 415

    data = request.get_json()
    order_id = data.get('orderID') # PayPal Order ID from frontend onApprove
    campaign_id_str = data.get('campaignId') # Pass campaign ID from frontend

    if not order_id or not campaign_id_str:
        return jsonify({"error": "Missing PayPal orderID or campaignId"}), 400

    app.logger.info(f"Attempting to capture PayPal Order ID: {order_id} for Campaign: {campaign_id_str}")

    try:
        # Find the payment (order) by ID
        payment = paypalrestsdk.Payment.find(order_id)

        # Execute (capture) the payment
        # payer_id is required. Get it from the payment object found.
        if payment.execute({"payer_id": payment.payer.payer_info.payer_id}):
            app.logger.info(f"PayPal Payment {order_id} captured successfully. State: {payment.state}")

            # --- Payment Successful - Record in DB ---
            transaction = payment.transactions[0]
            amount_details = transaction.amount
            captured_amount = amount_details.total
            captured_currency = amount_details.currency
            paypal_payment_id = payment.id # This is PayPal's transaction ID
            payer_email = payment.payer.payer_info.email

            # 1. Save to Payment Collection
            try:
                campaign_oid = ObjectId(campaign_id_str)
                payment_record = {
                    'campaignId': campaign_oid,
                    'campaignMongoId': campaign_id_str,
                    'paymentGateway': 'PayPal',
                    'gatewayTransactionId': paypal_payment_id,
                    'orderId': order_id, # Store original OrderID too
                    'amount': captured_amount, # Store the actual captured amount
                    'currency': captured_currency,
                    'payerInfo': {'email': payer_email},
                    'status': payment.state, # Should be 'approved' or similar
                    'timestamp_utc': datetime.utcnow().isoformat() + "Z",
                    'payment_details_ipfs_cid': None # Optional: Store on IPFS
                }
                # payment_cid = store_data_ipfs(payment_record) # Optional IPFS store
                # payment_record['payment_details_ipfs_cid'] = payment_cid or 'N/A'

                payment_insert_result = payment_collection.insert_one(payment_record.copy())
                payment_record_id = str(payment_insert_result.inserted_id)
                app.logger.info(f"PayPal payment record saved. DB ID: {payment_record_id}, PayPal ID: {paypal_payment_id}")

            except Exception as db_err:
                app.logger.error(f"Error saving PayPal payment {order_id} to DB: {db_err}", exc_info=True)
                # CRITICAL: Payment captured but failed to save! Manual intervention needed.
                # Consider refund logic or alerting system.
                return jsonify({"error": "Payment captured but failed to record in database. Please contact support."}), 500

            # 2. Update Campaign Amount Raised
            try:
                campaign = campaign_collection.find_one({'_id': campaign_oid})
                if campaign:
                    # **Decision Point:** How to store mixed funds?
                    # Option: Add a separate field like 'amountRaisedPayPalUSD'
                    current_raised_paypal_str = campaign.get(f'amountRaisedPayPal{captured_currency}', '0')
                    new_total_paypal = float(current_raised_paypal_str) + float(captured_amount)

                    update_result = campaign_collection.update_one(
                        {'_id': campaign_oid},
                        {'$set': {
                            f'amountRaisedPayPal{captured_currency}': str(new_total_paypal),
                            'updated_at_utc': datetime.utcnow().isoformat() + "Z"
                        }}
                    )
                    if update_result.modified_count:
                        app.logger.info(f"Campaign {campaign_id_str} PayPal amount ({captured_currency}) updated.")
                    else:
                        app.logger.warning(f"Campaign {campaign_id_str} PayPal amount update failed (no modification).")
                else:
                    app.logger.error(f"Campaign {campaign_id_str} not found for updating amount after PayPal payment {order_id}.")

            except Exception as update_err:
                 app.logger.error(f"Failed to update campaign amount for PayPal payment {order_id}: {update_err}")
                 # Non-critical error, payment is recorded, but amount might be off.

            # Return success details to frontend
            return jsonify({
                 "status": "success",
                 "message": "PayPal payment captured and recorded.",
                 "paypalPaymentId": paypal_payment_id,
                 "orderId": order_id,
                 "amount": captured_amount,
                 "currency": captured_currency,
             }), 200
            # --- End DB Recording ---

        else:
            # Payment execution failed
            app.logger.error(f"PayPal Payment execution failed for Order ID {order_id}: {payment.error}")
            error_details = payment.error if isinstance(payment.error, dict) else {'message': str(payment.error)}
            return jsonify({"error": "Failed to capture PayPal payment", "details": error_details}), 500

    except paypalrestsdk.ResourceNotFound:
         app.logger.error(f"PayPal Order ID {order_id} not found by SDK.")
         return jsonify({"error": "PayPal order not found."}), 404
    except Exception as e:
        app.logger.error(f"Error capturing PayPal order {order_id}: {e}", exc_info=True)
        return jsonify({"error": "Internal server error during PayPal payment capture"}), 500


# --- Main Execution ---
if __name__ == '__main__':
    app.logger.info(f"Starting Flask Backend Server in {'Debug' if settings.FLASK_DEBUG else 'Production'} mode..."),
    # Use settings for host, port, debug
    app.run(host=settings.FLASK_HOST, port=settings.FLASK_PORT, debug=settings.FLASK_DEBUG)