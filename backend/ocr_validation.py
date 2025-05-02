import pytesseract
import re
import json
import os
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv
from thefuzz import fuzz
from flask import Flask, request, jsonify, render_template, flash
import secrets
import logging

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
logging.basicConfig(level=logging.DEBUG)

load_dotenv()

TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    app.logger.warning(f"Tesseract path '{TESSERACT_PATH}' configured but not found! Relying on system PATH.")

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y",
    "%Y/%m/%d", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y",
    "%d %B %Y", "%d-%B-%Y", "%b %d, %Y", "%B %d, %Y",
    "%Y%m%d", "%d%m%Y", "%m%d%Y", "%Y.%m.%d", "%d.%m.%d", "%m.%d.%Y"  # Added more formats
]


def perform_ocr(image_path):
    app.logger.debug(f"Trying to open image at path: '{image_path}'")
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        app.logger.debug("--- RAW OCR Text ---")
        app.logger.debug(text)
        app.logger.debug("--------------------")
        return text
    except FileNotFoundError:
        app.logger.error(f"Image file not found at {image_path}")
        return None
    except Exception as e:
        app.logger.error(f"An error occurred during OCR processing: {e}")
        app.logger.error("Ensure Tesseract is installed and the path (if needed) is correct.")
        return None


def extract_details_regex(text):
    if not text:
        return None

    extracted_data = {'name': None, 'dob': None, 'aadhar': None}

    # --- Extract Potential Names ---
    name_pattern = re.compile(r"[A-Za-zÀ-ÿ\s.'-]+(?:[A-Za-zÀ-ÿ\s.'-]+)*", re.IGNORECASE)
    potential_names = name_pattern.findall(text)
    app.logger.debug(f"Potential names from OCR: {potential_names}")

    # Heuristic: Select longest name (often the full name)
    if potential_names:
        extracted_data['name'] = max(potential_names, key=len).strip()
        app.logger.debug(f"Selected name: {extracted_data['name']}")

    # --- Extract Potential Dates of Birth ---
    potential_dates = []
    dob_keywords = r"(?:DOB|D\.O\.B|Birth\s*date|Date\s*of\s*Birth|Birthday)"
    date_formats = [
        r"(\d{1,2}[-/.\s]\d{1,2}[-/.\s]\d{2,4})",  # DD/MM/YYYY, etc.
        r"(\d{4}[-/.\s]\d{1,2}[-/.\s]\d{1,2})",  # YYYY/MM/DD
        r"(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{2,4})",  # 01 Jan 2024
        r"(\d{1,2}\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*\d{2,4})"
    ]

    for fmt in date_formats:
        date_pattern = re.compile(dob_keywords + r"\s*[:=]?\s*" + fmt, re.IGNORECASE)
        dates = date_pattern.findall(text)
        if dates:
            potential_dates.extend(dates)
            app.logger.debug(f"Dates found with pattern: {fmt}: {dates}")

    # Heuristic: Select the first date found (often the most prominent DOB)
    if potential_dates:
        extracted_data['dob'] = potential_dates[0].strip()
        app.logger.debug(f"Selected DOB: {extracted_data['dob']}")

    # --- Extract Aadhar (If Present) ---
    aadhar_pattern = re.compile(r"(\d{4})\s?(\d{4})\s?(\d{4})")
    aadhar_match = aadhar_pattern.search(text)
    if aadhar_match:
        extracted_data['aadhar'] = "".join(aadhar_match.groups())
        app.logger.debug(f"Found Aadhar: {extracted_data['aadhar']}")

    app.logger.debug(f"---- Final Extracted Data -----")
    app.logger.debug(json.dumps(extracted_data, indent=2))
    app.logger.debug("-----------------------------")
    return extracted_data


def normalize_date(date_str):
    if not date_str:
        return None
    cleaned_date_str = date_str.strip()
    cleaned_date_str = re.sub(r'\s*[-/.]\s*', '-', cleaned_date_str)
    cleaned_date_str = re.sub(r'[^\d-]', '', cleaned_date_str)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned_date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    app.logger.warning(f"Could not parse date '{date_str}' into standard format.")
    return None


def normalize_data(data):
    normalized = {}
    if not data:
        return {}

    if 'name' in data and data['name']:
        normalized['name'] = data['name'].lower().strip()
    else:
        normalized['name'] = None

    if 'dob' in data and data['dob']:
        normalized['dob'] = normalize_date(data['dob'])
    else:
        normalized['dob'] = None

    if 'aadhar' in data and data['aadhar']:
        normalized['aadhar'] = re.sub(r'\D', '', data['aadhar'])
    else:
        normalized['aadhar'] = None

    return normalized


def compare_data(extracted_data, user_input_data, name_fuzziness_threshold=90):
    if not extracted_data or not user_input_data:
        if not extracted_data:
            extracted_data = {}
        if not user_input_data:
            user_input_data = {}

    name_match = False
    dob_match = False
    aadhar_match = False
    match_details = []

    norm_extracted = normalize_data(extracted_data)
    norm_user_input = normalize_data(user_input_data)

    app.logger.debug(f"\nNormalized Extracted: {json.dumps(norm_extracted, indent=2)}")
    app.logger.debug(f"Normalized User Input: {json.dumps(norm_user_input, indent=2)}\n")

    # Name Comparison
    # if norm_extracted.get('name') and norm_user_input.get('name'):
    #     name_similarity = fuzz.ratio(norm_extracted['name'], norm_user_input['name'])
    #     if name_similarity >= name_fuzziness_threshold:
    #         name_match = True
    #         match_details.append(f"Name match (Similarity: {name_similarity}%)")
    #     else:
    #         match_details.append(
    #             f"Name mismatch (Similarity: {name_similarity}%) - Extracted: '{norm_extracted['name']}', Input: '{norm_user_input['name']}'")
    # elif norm_extracted.get('name') is None and norm_user_input.get('name') is not None:
    #     match_details.append(f"Name mismatch - Extracted: Name not found, Input: '{norm_user_input['name']}'")
    # elif norm_user_input.get('name') is None and norm_extracted.get('name') is not None:
    #     match_details.append(f"Name mismatch - Input: Name not provided, Extracted: '{norm_extracted['name']}'")
    # else:
    #     match_details.append("Name missing in both extracted data and user input.")

    # # DOB Comparison
    # if norm_extracted.get('dob') and norm_user_input.get('dob'):
    #     if norm_extracted['dob'] == norm_user_input['dob']:
    #         dob_match = True
    #         match_details.append(f"DOB match: {norm_extracted['dob']}")
    #     else:
    #         match_details.append(
    #             f"DOB mismatch - Extracted: '{norm_extracted['dob']}', Input: '{norm_user_input['dob']}'")
    # elif norm_extracted.get('dob') is None and norm_user_input.get('dob') is not None:
    #     match_details.append(f"DOB mismatch - Extracted: DOB not found, Input: '{norm_user_input['dob']}'")
    # elif norm_user_input.get('dob') is None and norm_extracted.get('dob') is not None:
    #     match_details.append(f"DOB mismatch - Input: DOB not provided, Extracted: '{norm_extracted['dob']}'")
    # else:
    #     match_details.append("DOB missing in both extracted data and user input.")

    # Aadhar Comparison
    if norm_extracted.get('aadhar') and norm_user_input.get('aadhar'):
        if norm_extracted['aadhar'] == norm_user_input['aadhar']:
            aadhar_match = True
            match_details.append(f"Aadhar match")
        else:
            app.logger.warning(
                f"Aadhar mismatch - Extracted: {norm_extracted['aadhar'][:4]}... Input: {norm_user_input['aadhar'][:4]}...")
            match_details.append(f"Aadhar mismatch")
    elif norm_extracted.get('aadhar') is None and norm_user_input.get('aadhar') is not None:
        match_details.append(f"Aadhar mismatch - Extracted: Aadhar not found")
    elif norm_user_input.get('aadhar') is None and norm_extracted.get('aadhar') is not None:
        match_details.append(f"Aadhar mismatch - Input: Aadhar not provided, Extracted: '{norm_extracted['aadhar']}'")
    else:
        match_details.append("Aadhar missing in both extracted data and user input.")

    validation_passed = name_match and dob_match and aadhar_match
    message = "Validation Passed." if validation_passed else "Validation Failed."
    details_message = " | ".join(match_details) if match_details else "No comparison details generated."

    app.logger.debug("--- Comparison Results ---")
    app.logger.debug(details_message)
    app.logger.debug(f"Overall Result: {message}")
    app.logger.debug("-------------------------")

    return validation_passed, message, details_message

# --- Flask Routes ---
# (Keep your Flask routes as is)