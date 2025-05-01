# HACKINDIA_PROJECT/backend/app.py (Face Recognition Service)

import os # Added for environment variables
import logging # Added for logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import face_recognition
from PIL import Image
import io
import base64
import numpy as np

app = Flask(__name__)

# --- Explicit CORS Setup ---
# Define allowed origins. Load from Env Vars if needed, otherwise hardcode.
# Important: Include the origin of your main backend (localhost:5000)
# Also include frontend origin if direct access/testing is needed.
backend_origin = os.getenv('MAIN_BACKEND_ORIGIN', "http://localhost:5000")
frontend_origin = os.getenv('FRONTEND_ORIGIN', "http://localhost:5173")

# Apply CORS with specific origins
CORS(app, origins=[backend_origin, frontend_origin], supports_credentials=True)
# --- End CORS Setup ---

# Configure basic logging (optional but helpful)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - FACE_SVC - %(levelname)s - %(message)s')

@app.route('/') # Optional: Add a health check route
def health_check():
    logging.info("Health check endpoint called.")
    return jsonify({"service": "Face Recognition", "status": "running"}), 200

@app.route('/compare_faces', methods=['POST'])
def compare_faces():
    logging.info("Received request at /compare_faces") # Use logging
    try:
        # Check for missing parts
        if 'id_photo' not in request.files:
            logging.warning("Request missing 'id_photo' file part.")
            return jsonify({'error': 'Missing id_photo file part'}), 400
        if 'selfie' not in request.form:
            logging.warning("Request missing 'selfie' form part.")
            return jsonify({'error': 'Missing selfie form data'}), 400

        id_photo_file = request.files['id_photo']
        selfie_form_data = request.form['selfie'] # Expecting "data:image/jpeg;base64,..."

        # Validate filename (basic)
        if id_photo_file.filename == '':
            logging.warning("Received 'id_photo' but filename is empty.")
            return jsonify({'error': 'ID Photo filename is empty'}), 400

        logging.debug(f"Received id_photo: {id_photo_file.filename}, Content-Type: {id_photo_file.mimetype}")

        # Validate and extract base64 data for selfie
        if not selfie_form_data or ',' not in selfie_form_data:
             logging.warning(f"Invalid selfie data format received (missing comma?): {selfie_form_data[:50]}...")
             return jsonify({'error': 'Invalid selfie data format (expected data URL)'}), 400
        try:
            # Split "data:image/jpeg;base64," part if present
            header, encoded = selfie_form_data.split(',', 1)
            selfie_bytes = base64.b64decode(encoded)
            logging.debug(f"Decoded selfie data length: {len(selfie_bytes)}")
        except (ValueError, TypeError, base64.binascii.Error) as b64_err:
             logging.error(f"Error decoding base64 selfie data: {b64_err}")
             return jsonify({'error': f'Invalid base64 selfie data: {b64_err}'}), 400

        # Process images safely
        try:
             logging.debug("Opening selfie image from bytes...")
             selfie_image = Image.open(io.BytesIO(selfie_bytes)).convert('RGB')
             logging.debug("Opening ID photo image from file...")
             # Reset pointer just in case it was read before
             id_photo_file.seek(0)
             id_image = Image.open(id_photo_file).convert('RGB')
             logging.debug("Images opened successfully.")
        except Exception as img_err:
             logging.error(f"Error opening or converting image data: {img_err}", exc_info=True)
             return jsonify({'error': f'Error processing image data: {img_err}'}), 400

        # Convert images to numpy arrays
        id_image_np = np.array(id_image)
        selfie_image_np = np.array(selfie_image)
        logging.debug("Images converted to numpy arrays.")

        # Find face encodings
        logging.info("Finding face encodings...")
        # It's possible face_encodings returns an empty list if no face is found
        id_encodings = face_recognition.face_encodings(id_image_np)
        selfie_encodings = face_recognition.face_encodings(selfie_image_np)

        # Check if faces were found in both images
        if len(id_encodings) == 0:
            logging.warning("No face detected in ID photo.")
            return jsonify({'match': False, 'error': 'No face detected in ID photo', 'message': 'No face detected in ID photo'}), 400 # Return 400 for client error
        if len(selfie_encodings) == 0:
            logging.warning("No face detected in selfie.")
            return jsonify({'match': False, 'error': 'No face detected in selfie', 'message': 'No face detected in selfie'}), 400 # Return 400 for client error

        logging.info(f"Found {len(id_encodings)} face(s) in ID, {len(selfie_encodings)} face(s) in selfie. Comparing first faces.")
        # Compare the first face found in each image
        # Adjust tolerance if needed (lower value means stricter matching)
        results = face_recognition.compare_faces([id_encodings[0]], selfie_encodings[0], tolerance=0.5)
        match = bool(results[0]) # Convert numpy boolean if necessary
        logging.info(f"Face comparison result: Match = {match}")

        # Return JSON response
        return jsonify({'match': match, 'message': 'Faces match!' if match else 'Faces do not match.'})

    except Exception as e:
        # Log the full error traceback for internal debugging
        logging.error(f"Unexpected error in /compare_faces endpoint: {e}", exc_info=True)
        # Return a generic error message to the client
        return jsonify({'error': f'An internal server error occurred in the face recognition service.'}), 500

if __name__ == '__main__':
    # Use environment variables for configuration, with defaults
    host = os.getenv('FACE_SERVICE_HOST', '127.0.0.1') # Changed default to 127.0.0.1 for clarity
    port = int(os.getenv('FACE_SERVICE_PORT', 5003))
    debug_mode = os.getenv('FACE_SERVICE_DEBUG', 'False').lower() in ['true', '1', 't']

    logging.info(f"Starting Face Recognition Service on {host}:{port} (Debug: {debug_mode})...")
    # Use Waitress or Gunicorn for production instead of app.run
    app.run(debug=debug_mode, port=port, host=host) # Listen on specified host