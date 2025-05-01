// HACKINDIA_PROJECT/frontend/src/utils/api.jsx

// Use environment variable for API base URL in production builds
// Ensure you set REACT_APP_API_BASE_URL in your frontend's .env file

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';
console.log(`Using API Base URL: ${API_BASE_URL}`);

// Helper function for handling fetch responses
const handleResponse = async (response) => {
    if (!response.ok) {
        let errorData = { error: `HTTP error ${response.status}: ${response.statusText}` }; // Default error
        try {
            // Try parsing JSON error from backend
            const jsonError = await response.json();
            errorData = jsonError || errorData; // Use backend error if available
        } catch (e) {
            // Ignore parsing error if response is not JSON
            console.warn("Response was not JSON, using status text as error.");
        }
        console.error('API Error Response:', errorData);
        // Throw an error with the message from backend if possible
        throw new Error(errorData.error || `HTTP error ${response.status}`);
    }
    // Handle cases where response might be empty (e.g., 204 No Content)
    const contentType = response.headers.get("content-type");
    if (response.status === 204) {
        return null; // Or handle appropriately
    }
    if (contentType && contentType.includes("application/json")) {
        return await response.json();
    } else {
        // Handle non-JSON responses if expected, otherwise return text
        console.warn("Received non-JSON response from API:", response);
        return await response.text();
    }
};

// --- Existing KYC Functions (from your upload) ---

export const fetchFaceRecognition = async (formData) => {
    try {
        console.log("Calling fetchFaceRecognition...");
        const response = await fetch(`${API_BASE_URL}/face_recognize`, {
            method: 'POST',
            body: formData, // FormData handles Content-Type correctly
        });
        return await handleResponse(response);
    } catch (error) {
        console.error('Error during face recognition API call:', error);
        // Rethrow to be caught by the calling component
        throw error;
    }
};

export const fetchOCRValidation = async (userData) => {
    // userData should contain { name, dob, imageId } - Aadhar REMOVED
    if (userData.aadhar) {
        console.warn("Aadhar data found in OCR validation request, but it's ignored by the backend.");
        delete userData.aadhar; // Ensure it's not sent
    }
    try {
        console.log("Calling fetchOCRValidation with:", userData);
        const response = await fetch(`${API_BASE_URL}/validate_ocr`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData),
        });
        // Allow 200 OK even if is_valid is false, handleResponse checks !response.ok for actual fetch/server errors
        return await handleResponse(response);
    } catch (error) {
        console.error('Error during OCR validation API call:', error);
        throw error;
    }
};


// --- NEW/UPDATED Functions for Campaigns ---

// Check if user is validated (using name as identifier - requires improvement for production)
export const checkAuthStatus = async (userIdentifier) => {
     try {
        if (!userIdentifier) {
            console.warn("checkAuthStatus called with no identifier.");
            return false;
        }
        console.log(`Checking auth status for: ${userIdentifier}`);
        // Encode the identifier in case it contains special characters
        const response = await fetch(`${API_BASE_URL}/auth/status/${encodeURIComponent(userIdentifier)}`);
        // Allow 404 (Not Found) as a valid "not validated" state
        if (response.status === 404) {
             console.log(`Auth status check for ${userIdentifier}: Not found.`);
             return false;
        }
        const data = await handleResponse(response); // Handles other non-ok statuses
        console.log("Auth status response:", data);
        return data.isValidated || false; // Return false if isValidated is not present or false
     } catch (error) {
         // Gracefully handle expected "not found" or connection errors without crashing
         console.warn(`Auth status check failed for ${userIdentifier}:`, error.message);
         return false; // Assume not validated on error
     }
};

// Fetch Campaigns (defaults to 'verified')
export const fetchCampaigns = async (status = 'verified') => {
    try {
        console.log(`Workspaceing campaigns with status: ${status}`);
        const response = await fetch(`${API_BASE_URL}/campaigns?status=${status}`);
        return await handleResponse(response);
    } catch (error) {
        console.error('Error fetching campaigns:', error);
        throw error;
    }
};

// Fetch Single Campaign by ID
export const fetchCampaignById = async (campaignId) => {
    try {
        console.log(`Workspaceing campaign by ID: ${campaignId}`);
        const response = await fetch(`${API_BASE_URL}/campaigns/${campaignId}`);
        return await handleResponse(response);
    } catch (error) {
        console.error(`Error fetching campaign ${campaignId}:`, error);
        throw error;
    }
};

// Create Campaign
export const createCampaign = async (campaignData) => {
    // campaignData includes { title, description, goalAmount (in Wei string), creatorName }
    try {
        console.log("Calling createCampaign with:", campaignData);
        const response = await fetch(`${API_BASE_URL}/campaigns`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(campaignData),
        });
        // Expecting 201 Created on success
        if (response.status !== 201) { // Check specifically for 201
             // Let handleResponse deal with non-201/non-ok statuses
             return await handleResponse(response);
        }
        // If status is 201, parse JSON
        return await response.json();
    } catch (error) {
        console.error('Error creating campaign:', error);
        throw error;
    }
};

// Record Payment after successful blockchain transaction
export const recordBackendPayment = async (campaignId, paymentData) => {
     // paymentData includes { transactionHash, amount (in Ether string), funderAddress }
    try {
        console.log(`Recording payment for campaign ${campaignId}:`, paymentData);
        const response = await fetch(`${API_BASE_URL}/campaigns/${campaignId}/fund`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(paymentData),
        });
        // Expecting 201 Created
        if (response.status !== 201) {
            return await handleResponse(response);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error recording payment for campaign ${campaignId}:`, error);
        throw error;
    }
}