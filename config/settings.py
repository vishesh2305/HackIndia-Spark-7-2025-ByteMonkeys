# HACKINDIA_PROJECT/config/settings.py

import os
from dotenv import load_dotenv
import logging # Added logging



GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')


if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    logging.warning("GOOGLE_API_KEY or GOOGLE_CSE_ID not found in environment variables. AI campaign validation will likely fail.")

# Load .env file from the project root (one level up from config)
# Create a .env file in HACKINDIA_PROJECT/ with your actual values
# Example .env content:
# MONGO_URI=mongodb://localhost:27017/
# DB_NAME=hackindia_db
# CAMPAIGN_CONTRACT_ADDRESS=0x... # Fill after deployment
# WEB3_PROVIDER_URI=http://127.0.0.1:8545
# IPFS_API_URL=/ip4/127.0.0.1/tcp/5001 # Use API multiaddr for ipfshttpclient
# TESSERACT_PATH="C:\Program Files\Tesseract-OCR\tesseract.exe" # Use your path
# FACE_API_URL=http://localhost:5003/compare_faces
# FLASK_HOST=127.0.0.1
# FLASK_PORT=5000
# FLASK_DEBUG=True
# ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(f".env file loaded from {dotenv_path}")
else:
    logging.warning(f"Warning: .env file not found at {dotenv_path}. Using defaults or system environment variables.")


# Database Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
# Use a specific DB name, default 'hackindia_db'
DB_NAME = os.getenv('DB_NAME', 'hackindia_db')

# --- IMPORTANT: Blockchain Configuration ---
# Get this address AFTER deploying the contract using blockchain/scripts/deploy.js
# Ensure this is set in your .env file after deployment!
CAMPAIGN_CONTRACT_ADDRESS = os.getenv('CAMPAIGN_CONTRACT_ADDRESS')
if not CAMPAIGN_CONTRACT_ADDRESS:
    logging.error("CAMPAIGN_CONTRACT_ADDRESS not set in environment variables. Blockchain features related to campaigns will fail.")
# Ganache default, change if using another network
WEB3_PROVIDER_URI = os.getenv('WEB3_PROVIDER_URI', 'http://127.0.0.1:8545')

# IPFS Configuration
# Default local node API multiaddress (ensure your node's API server is running)
# Example: '/dns/localhost/tcp/5001/http' or '/ip4/127.0.0.1/tcp/5001'
IPFS_API_URL = os.getenv('IPFS_API_URL', '/ip4/127.0.0.1/tcp/5001')

# Tesseract Configuration (Needed for OCR in backend.py)
# Adjust path for your system, or ensure tesseract is in system PATH
TESSERACT_PATH = os.getenv('TESSERACT_PATH') # Example: r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Face Recognition Service URL (If backend/app.py runs separately)
FACE_API_URL = os.getenv('FACE_API_URL', 'http://localhost:5003/compare_faces')

# Backend Server Configuration
FLASK_HOST = os.getenv('FLASK_HOST', '127.0.0.1')
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']

# CORS Origins (adjust for your frontend URL, especially in production)
# Use comma-separated values in .env: ALLOWED_ORIGINS="http://localhost:3000,http://yourdomain.com"
_allowed_origins_str = os.getenv('ALLOWED_ORIGINS', "http://localhost:3000,http://127.0.0.1:3000") # Default might be wrong
ALLOWED_ORIGINS = [origin.strip() for origin in _allowed_origins_str.split(',')]

# Logging Configuration (Optional basic setup)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')