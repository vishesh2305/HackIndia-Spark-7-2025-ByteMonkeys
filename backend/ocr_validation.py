import pytesseract

import re
import json
import os
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv
from thefuzz import fuzz
from flask import Flask, request, jsonify, render_template, flash
import secrets  # For generating secure temporary filenames
import logging  # Optional: for better logging

app = Flask(__name__)
# Secret key needed for flashing messages (optional but good practice)
app.secret_key = secrets.token_hex(16)
# Configure a folder for temporary uploads
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Optional: Configure logging
logging.basicConfig(level=logging.DEBUG)

# --- OCR & Validation Logic (Adapted from your script) ---
load_dotenv()

TESSERACT_PATH = '/opt/homebrew/bin/tesseract'
if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    app.logger.warning(f"Tesseract path '{TESSERACT_PATH}' configured but not found! Relying on system PATH.")

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y",
    "%Y/%m/%d", "%Y-%m-%d", "%d %b %Y", "%d-%b-%Y",
    "%d %B %Y", "%d-%B-%Y", "%b %d, %Y", "%B %d, %Y"
]

def perform_ocr(image_path):
    app.logger.debug(f"Trying to open image at path: '{image_path}'")
    try:
        img = Image.open(image_path)
        # Enhance OCR for potentially noisy images (optional preprocessing)
        # Consider adding OpenCV preprocessing here if needed
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

# --- Refined Name Extraction Helper ---
def find_name_before_anchor(text, anchor_match):
    """Helper to find name on lines before a regex match object."""
    found_name = None
    try:
        # Find the start index of the line containing the anchor match
        anchor_line_start_index = text.rfind('\n', 0, anchor_match.start()) + 1
        if anchor_line_start_index == 0 and anchor_match.start() > 0: # Handle case where anchor is on the very first line
            anchor_line_start_index = 0
        elif anchor_line_start_index < 0: # Defensive fallback
             anchor_line_start_index = anchor_match.start()

        # Define the area of text *before* the anchor line to search for the name
        search_area_before_anchor = text[:anchor_line_start_index].strip()

        # Split the preceding text into lines and reverse to check from bottom up
        potential_name_lines = search_area_before_anchor.split('\n')

        # Iterate backwards through the lines before the anchor line
        for line in reversed(potential_name_lines):
            potential_name = line.strip()
            # Check if the line looks like a valid name (allows multiple words, letters, spaces, optional dot)
            if potential_name and re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)*\.?", potential_name):
                 found_name = potential_name # Take the last valid name line found
                 app.logger.debug(f"Found potential name ('{found_name}') before anchor '{anchor_match.group(0)}'")
                 break # Stop searching backwards once a likely name is found
            elif potential_name: # Stop if we hit a non-empty line that isn't a name
                app.logger.debug(f"Stopping name search at non-name line: '{potential_name}'")
                break
    except Exception as e:
        app.logger.debug(f"Error finding name before anchor '{anchor_match.group(0)}': {e}")
    return found_name
# --- End Helper ---


def extract_details_regex(text):
    if not text:
        return None
    # Initialize with aadhar key
    extracted_data = {'name': None, 'dob': None, 'aadhar': None}
    dob_match_1 = None
    dob_match_2 = None

    # --- Aadhar Pattern ---
    # Looks for 12 digits, potentially separated by spaces (captures digits only)
    aadhar_pattern = re.compile(r"(\d{4})\s?(\d{4})\s?(\d{4})")
    aadhar_match = aadhar_pattern.search(text)
    if aadhar_match:
        extracted_data['aadhar'] = "".join(aadhar_match.groups())
        app.logger.debug(f"Found Aadhar: {extracted_data['aadhar']}")
    else:
        app.logger.debug("Aadhar number (12 digits) not found.")


    # --- Attempt to find DOB first using either pattern ---
    try:
        # DOB Pattern 1: Look for common labels and DD/MM/YYYY format
        dob_pattern_1 = re.compile(r"(?:DOB[:/]|Birth ?date[:\s/]|Date of Birth[:\s/])\s*(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE)
        dob_match_1 = dob_pattern_1.search(text)
        if dob_match_1:
            extracted_data['dob'] = dob_match_1.group(1).strip()
            app.logger.debug(f"Found DOB using Pattern Set 1: {extracted_data['dob']}")
    except Exception as e:
         app.logger.debug(f"Error during DOB Pattern Set 1 search: {e}")

    if not extracted_data['dob']: # Only try pattern 2 if pattern 1 failed
        try:
            # DOB Pattern 2: Look forYYYY-MM-DD on its own line
            dob_pattern_2 = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)
            dob_match_2 = dob_pattern_2.search(text)
            if dob_match_2:
                extracted_data['dob'] = dob_match_2.group(1).strip()
                app.logger.debug(f"Found DOB using Pattern Set 2: {extracted_data['dob']}")
        except Exception as e:
             app.logger.debug(f"Error during DOB Pattern Set 2 search: {e}")


    # --- Attempt to find Name based on which DOB pattern matched (or other patterns) ---
    if dob_match_1:
        # If DOB Pattern 1 matched, find name before that match
        extracted_data['name'] = find_name_before_anchor(text, dob_match_1)
    elif dob_match_2:
        # If DOB Pattern 2 matched, find name before that match
        extracted_data['name'] = find_name_before_anchor(text, dob_match_2)
    else:
        # Fallback if DOB wasn't found by either specific pattern
        # Try the 'AADHAAR' keyword pattern as a last resort for name
        app.logger.debug("DOB not found by main patterns, trying fallback name extraction.")
        if not extracted_data['name']:
             try:
                # Using original Pattern Set 2 logic, but make keyword more flexible
                name_pattern_fallback = re.compile(r"(?:AADHAAR|.?ADHAAR)\s*\n+([A-Za-z\s]+?)(?=\n\s*(\d{4}-\d{2}-\d{2}|\S+:|Address:|Male|Female|THIRD GENDER|$))", re.IGNORECASE | re.DOTALL)
                name_match_fallback = name_pattern_fallback.search(text)
                if name_match_fallback:
                    extracted_name = re.sub(r'\s+', ' ', name_match_fallback.group(1)).strip()
                    if re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)*\.?", extracted_name):
                         extracted_data['name'] = extracted_name
                         app.logger.debug(f"Found potential name (Fallback Pattern): '{extracted_name}'")
             except Exception as e:
                 app.logger.debug(f"Error during Fallback Name extraction: {e}")

    app.logger.debug(f"---- Final Extracted Data -----")
    app.logger.debug(json.dumps(extracted_data, indent=2))
    app.logger.debug("-----------------------------")
    return extracted_data


def normalize_date(date_str):
    # (Keep this function as is)
    if not date_str:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    app.logger.warning(f"Could not parse date '{date_str}' into standard format.")
    return None

def normalize_data(data):
    # (Keep this function as is)
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
    # (Keep this function as is)
    if not extracted_data or not user_input_data:
        if not extracted_data: extracted_data = {}
        if not user_input_data: user_input_data = {}

    name_match = False
    dob_match = False
    aadhar_match = False
    match_details = []

    norm_extracted = normalize_data(extracted_data)
    norm_user_input = normalize_data(user_input_data)

    app.logger.debug(f"\nNormalized Extracted: {json.dumps(norm_extracted, indent=2)}")
    app.logger.debug(f"Normalized User Input: {json.dumps(norm_user_input, indent=2)}\n")

    # Name Comparison
    if norm_extracted.get('name') and norm_user_input.get('name'):
        name_similarity = fuzz.ratio(norm_extracted['name'], norm_user_input['name'])
        if name_similarity >= name_fuzziness_threshold:
            name_match = True
            match_details.append(f"Name match (Similarity: {name_similarity}%)")
        else:
            match_details.append(f"Name mismatch (Similarity: {name_similarity}%) - Extracted: '{norm_extracted['name']}', Input: '{norm_user_input['name']}'")
    elif norm_extracted.get('name') is None and norm_user_input.get('name') is not None:
         match_details.append(f"Name mismatch - Extracted: Name not found, Input: '{norm_user_input['name']}'")
    elif norm_user_input.get('name') is None and norm_extracted.get('name') is not None:
         match_details.append(f"Name mismatch - Input: Name not provided, Extracted: '{norm_extracted['name']}'")
    else:
        match_details.append("Name missing in both extracted data and user input.")

    # DOB Comparison
    if norm_extracted.get('dob') and norm_user_input.get('dob'):
        if norm_extracted['dob'] == norm_user_input['dob']:
            dob_match = True
            match_details.append(f"DOB match: {norm_extracted['dob']}")
        else:
            match_details.append(f"DOB mismatch - Extracted: '{norm_extracted['dob']}', Input: '{norm_user_input['dob']}'")
    elif norm_extracted.get('dob') is None and norm_user_input.get('dob') is not None:
         match_details.append(f"DOB mismatch - Extracted: DOB not found, Input: '{norm_user_input['dob']}'")
    elif norm_user_input.get('dob') is None and norm_extracted.get('dob') is not None:
         match_details.append(f"DOB mismatch - Input: DOB not provided, Extracted: '{norm_extracted['dob']}'")
    else:
        match_details.append("DOB missing in both extracted data and user input.")

    # Aadhar Comparison
    if norm_extracted.get('aadhar') and norm_user_input.get('aadhar'):
        if norm_extracted['aadhar'] == norm_user_input['aadhar']:
            aadhar_match = True
            match_details.append(f"Aadhar match")
        else:
            app.logger.warning(f"Aadhar mismatch - Extracted: {norm_extracted['aadhar'][:4]}... Input: {norm_user_input['aadhar'][:4]}...")
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

@app.route('/', methods=['GET'])
def index():
    """Serves the initial HTML form."""
    return render_template('index.html', result=None)

@app.route('/validate', methods=['POST'])
def validate():
    """Handles form submission, performs OCR and validation."""
    result = { 'status': 'error', 'message': 'An unexpected error occurred.', 'details': '' }
    temp_image_path = None

    try:
        # --- 1. Get User Input ---
        user_name = request.form.get('name')
        user_dob = request.form.get('dob')
        user_aadhar = request.form.get('aadhar')
        image_file = request.files.get('document_image')

        if not user_name or not user_dob or not user_aadhar:
             result['message'] = 'Please enter Name, Date of Birth, and Aadhar Number.'
             flash(result['message'], 'error')
             return render_template('index.html', result=result)

        user_aadhar_cleaned = re.sub(r'\s', '', user_aadhar)
        if not re.fullmatch(r"\d{12}", user_aadhar_cleaned):
            result['message'] = 'Please enter a valid 12-digit Aadhar number.'
            flash(result['message'], 'error')
            return render_template('index.html', result=result)

        if not image_file or image_file.filename == '':
            result['message'] = 'Please upload an image file.'
            flash(result['message'], 'error')
            return render_template('index.html', result=result)

        # --- 2. Save Uploaded Image Temporarily ---
        filename = secrets.token_hex(8) + os.path.splitext(image_file.filename)[1]
        temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(temp_image_path)
        app.logger.info(f"Image saved temporarily to {temp_image_path}")

        # --- 3. Perform OCR ---
        raw_text = perform_ocr(temp_image_path)

        if not raw_text:
            result['message'] = 'OCR processing failed. Could not read text from image.'
            flash(result['message'], 'error')
            # Go directly to finally block for cleanup
        else:
            # --- 4. Extract Details ---
            extracted_details = extract_details_regex(raw_text)
            extraction_failed = not extracted_details or (
                extracted_details.get('name') is None and
                extracted_details.get('dob') is None and
                extracted_details.get('aadhar') is None
            )
            if extraction_failed:
                 app.logger.warning("Could not extract any details, comparison will likely fail.")

            # --- 5. Compare Data ---
            user_input_data = {"name": user_name, "dob": user_dob, "aadhar": user_aadhar_cleaned}

            validation_passed, message, details_msg = compare_data(
                extracted_details if extracted_details else {},
                user_input_data
            )

            result['status'] = 'success' if validation_passed else 'failure'
            result['message'] = message
            result['details'] = details_msg
            flash(f"{message} {details_msg}", 'success' if validation_passed else 'error')

    except Exception as e:
        app.logger.error(f"Error during validation process: {e}", exc_info=True)
        result['message'] = f'An server error occurred during validation: {e}'
        flash(result['message'], 'error')

    finally:
        # --- 6. Cleanup Temporary File ---
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
                app.logger.info(f"Temporary file {temp_image_path} deleted.")
            except Exception as e:
                app.logger.error(f"Error deleting temporary file {temp_image_path}: {e}")

    return render_template('index.html', result=result)
@app.route('/extract_aadhar', methods=['POST'])
def extract_aadhar():
    try:
        if 'document_image' not in request.files:
            return jsonify({'error': 'Missing document_image'}), 400

        image_file = request.files['document_image']
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400

        # Save image temporarily
        filename = secrets.token_hex(8) + os.path.splitext(image_file.filename)[1]
        temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(temp_image_path)
        app.logger.info(f"Image saved temporarily to {temp_image_path}")

        # Perform OCR
        raw_text = perform_ocr(temp_image_path)
        if not raw_text:
            return jsonify({'error': 'OCR failed. Could not read text from image'}), 400

        # Extract details
        extracted_details = extract_details_regex(raw_text)
        if not extracted_details or not extracted_details.get('name') or not extracted_details.get('aadhar'):
            return jsonify({'error': 'Could not extract name or Aadhar number'}), 400

        # Clean up
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            app.logger.info(f"Temporary file {temp_image_path} deleted.")

        return jsonify({
            'is_valid': True,
            'name': extracted_details['name'],
            'id_number': extracted_details['aadhar']
        }), 200

    except Exception as e:
        app.logger.error(f"Error in extract_aadhar: {e}")
        if 'temp_image_path' in locals() and os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, port=5002)
