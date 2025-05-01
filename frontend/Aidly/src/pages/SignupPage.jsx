// HACKINDIA_PROJECT/frontend/src/components/SignupPage.jsx
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; // Import for redirection
import { fetchFaceRecognition, fetchOCRValidation } from '../utils/api.jsx'; // Use .jsx extension
import { initWeb3, storeValidationHashOnChain, hashData } from '../utils/web3.jsx'; // Use .jsx extension

function SignupPage() {
    const [idPhoto, setIdPhoto] = useState(null);
    const [selfie, setSelfie] = useState(null);
    const [name, setName] = useState(''); // Keep Name
    const [dob, setDob] = useState('');   // Keep DOB
    // const [aadhar, setAadhar] = useState(''); // Aadhar state REMOVED
    const [faceMatchResult, setFaceMatchResult] = useState(null); // { match: bool, message: string, imageId?: string }
    const [ocrValidationResult, setOcrValidationResult] = useState(null); // { is_valid: bool, message: string, details?: string, data_hash?: string, tx_hash?: string, user_name?: string }
    const [imageId, setImageId] = useState(null); // Store imageId from face recognition
    const [isProcessingFace, setIsProcessingFace] = useState(false);
    const [isProcessingOCR, setIsProcessingOCR] = useState(false);
    const [web3Ready, setWeb3Ready] = useState(false); // Track ethers initialization

    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const navigate = useNavigate(); // Hook for navigation

    // Initialize Ethers on component mount
    useEffect(() => {
        const initialize = async () => {
            console.log("Attempting to initialize Web3...");
            const success = await initWeb3();
            setWeb3Ready(success);
            console.log("Web3 initialization status:", success);
        };
        initialize();

        // --- Webcam Setup ---
        let stream = null;
        const setupWebcam = async () => {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                try {
                    stream = await navigator.mediaDevices.getUserMedia({ video: true });
                    if (videoRef.current) {
                        videoRef.current.srcObject = stream;
                    }
                } catch (err) {
                    console.error('Error accessing webcam:', err);
                    alert('Error accessing webcam. Please ensure permissions are granted.');
                }
            } else {
                alert('getUserMedia not supported in this browser.');
            }
        };
        setupWebcam();

        // --- Cleanup function ---
        return () => {
            console.log("Cleaning up webcam stream.");
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            if (videoRef.current && videoRef.current.srcObject) {
                 // Ensure tracks are stopped even if stream variable is somehow lost
                 videoRef.current.srcObject.getTracks().forEach(track => track.stop());
                 videoRef.current.srcObject = null; // Remove reference
            }
        };
    }, []); // Empty dependency array means this runs once on mount

    const handleIdPhotoChange = (e) => {
        if (e.target.files && e.target.files[0]) {
             setIdPhoto(e.target.files[0]);
        } else {
             setIdPhoto(null);
        }
    };

    const handleCapture = () => {
         if (videoRef.current && canvasRef.current && videoRef.current.readyState === videoRef.current.HAVE_ENOUGH_DATA) {
            const video = videoRef.current;
            const canvas = canvasRef.current;
            // Set canvas dimensions based on video intrinsic dimensions
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            const dataUrl = canvas.toDataURL('image/jpeg'); // Use JPEG for smaller size
            setSelfie(dataUrl);
            console.log("Selfie captured.");
        } else {
             console.error("Cannot capture selfie: Video stream not ready or refs missing.");
             alert("Could not capture selfie. Please ensure webcam is active and try again.");
        }
    };

    const handleFaceRecognition = async () => {
        if (!idPhoto) { alert('Please upload ID photo.'); return; }
        if (!selfie) { alert('Please capture a selfie.'); return; }

        setIsProcessingFace(true);
        setFaceMatchResult(null); // Clear previous result
        setImageId(null); // Clear previous imageId

        const formData = new FormData();
        formData.append('id_photo', idPhoto);
        formData.append('selfie', selfie); // Send base64 data URL

        console.log("Sending data for face recognition...");
        try {
            const result = await fetchFaceRecognition(formData);
            console.log("Face recognition response:", result);
            setFaceMatchResult(result); // Store full result { match, message, imageId? }
            if (result?.match && result?.imageId) {
                setImageId(result.imageId); // Store imageId on success
                alert(`Face Recognition Successful! ${result.message || ''}`);
            } else {
                 // Match false or error from backend handled via handleResponse
                 alert(`Face Recognition Failed: ${result?.message || 'Details mismatch or error occurred.'}`);
            }
        } catch (error) {
            console.error('Face recognition fetch error:', error);
            alert(`Error during face recognition: ${error.message}`);
        } finally {
            setIsProcessingFace(false);
        }
    };

     const handleOCRValidation = async (e) => {
        e.preventDefault(); // Prevent default form submission

        // Validations
        if (!imageId) { alert('Face recognition must be successful first (Image ID missing).'); return; }
        if (!name.trim()) { alert('Please enter your Name (as on ID).'); return; }
        if (!dob) { alert('Please enter your Date of Birth.'); return; }
        // Aadhar input removed

        setIsProcessingOCR(true);
        setOcrValidationResult(null); // Clear previous result

        // Prepare data: ONLY name, dob, imageId
        const userData = { name: name.trim(), dob, imageId };
        console.log("Sending data for OCR validation:", userData);

        try {
            // Call backend OCR validation API
            const ocrResult = await fetchOCRValidation(userData);
            console.log("OCR validation response:", ocrResult);
            setOcrValidationResult(ocrResult); // Store the full result

            if (ocrResult?.is_valid) {
                // --- Validation Successful ---
                alert(`OCR Validation Successful! ${ocrResult.details || ''}`);

                // --- Optional: Store hash on chain ---
                // Check if necessary data is present from backend response
                if (web3Ready && ocrResult.data_hash && ocrResult.user_name) {
                    console.log("Attempting to store validation hash on blockchain:", ocrResult.data_hash);
                     try {
                        // Use the updated web3.jsx function name
                        const txHash = await storeValidationHashOnChain(ocrResult.data_hash);
                        if (txHash) {
                            alert(`User validated successfully. Data Hash stored on blockchain. Tx: ${txHash.substring(0,10)}...`);
                            // --- REDIRECT TO HOME PAGE ---
                            // Store validated user info (e.g., name from response)
                            localStorage.setItem('userName', ocrResult.user_name);
                            localStorage.setItem('isValidated', 'true'); // Set a flag
                            console.log(`User ${ocrResult.user_name} validated. Navigating to /home`);
                            navigate('/home'); // Navigate to the home page route
                        } else {
                             // Blockchain storage failed after successful OCR
                            alert('OCR Validation OK, but failed to store data hash on blockchain. Proceeding without blockchain record.');
                            // Decide if navigation should still happen
                            localStorage.setItem('userName', ocrResult.user_name);
                            localStorage.setItem('isValidated', 'true');
                            navigate('/home');
                        }
                    } catch (web3Error) {
                         // Catch errors specifically from storeValidationHashOnChain
                         console.error("Blockchain storage error:", web3Error);
                         alert(`OCR Validation OK, but Blockchain Error: ${web3Error.message}. Proceeding without blockchain record.`);
                         localStorage.setItem('userName', ocrResult.user_name);
                         localStorage.setItem('isValidated', 'true');
                         navigate('/home');
                    }

                } else {
                     // Handle cases where blockchain step is skipped
                     let skipReason = "";
                     if (!web3Ready) skipReason = "Web3 wallet not ready.";
                     else if (!ocrResult.data_hash) skipReason = "Backend did not provide data hash.";
                     else if (!ocrResult.user_name) skipReason = "Backend did not provide user identifier.";
                     alert(`OCR Validation Successful! Skipping blockchain step: ${skipReason}`);
                     localStorage.setItem('userName', ocrResult.user_name || name); // Fallback to input name if backend name missing
                     localStorage.setItem('isValidated', 'true');
                     navigate('/home'); // Redirect anyway
                }
                 // ----------------------------

            } else {
                // OCR validation failed (is_valid: false from backend)
                alert(`OCR Validation Failed: ${ocrResult?.message || 'Details mismatch.'} ${ocrResult?.details || ''}`);
            }

        } catch (error) {
            // Catch errors from fetchOCRValidation API call itself
            console.error('OCR validation fetch error:', error);
            alert(`Error during OCR validation: ${error.message}`);
        } finally {
            setIsProcessingOCR(false);
        }
    };


    // Render logic
    return (
        <div style={styles.container}>
            <h1>Signup & Verification</h1>
            <p style={styles.statusText}>
                Status:
                {(isProcessingFace || isProcessingOCR) ? ' Processing...' : ''}
                {web3Ready ? ' Wallet Connected' : ' Wallet Not Connected'}
            </p>

            {/* Step 1: Face Recognition */}
            <fieldset style={styles.fieldset} disabled={isProcessingFace || isProcessingOCR}>
                <legend>Step 1: Face Recognition</legend>
                <div style={styles.inputGroup}>
                    <label htmlFor='idPhotoInput'>ID Photo: </label>
                    <input id='idPhotoInput' type="file" accept="image/*" onChange={handleIdPhotoChange} />
                </div>
                <div style={{ margin: '10px 0', textAlign: 'center' }}>
                    <video ref={videoRef} autoPlay playsInline muted style={styles.videoPreview}/>
                    {/* Hidden canvas for capturing frame */}
                    <canvas ref={canvasRef} style={{ display: 'none' }} />
                </div>
                 <div style={styles.capturePreview}>
                     <button onClick={handleCapture} type="button" style={styles.button}>Capture Selfie</button>
                     {selfie && (
                         <img
                             src={selfie}
                             alt="Captured Selfie"
                             style={styles.selfiePreview}
                          />
                      )}
                 </div>
                <button
                    onClick={handleFaceRecognition}
                    disabled={!idPhoto || !selfie || isProcessingFace}
                    type="button"
                    style={{ ...styles.button, marginTop: '10px', width: '100%' }}
                >
                    {isProcessingFace ? 'Verifying Faces...' : 'Verify Faces'}
                </button>
                {faceMatchResult && (
                    <p style={{ ...styles.message, color: faceMatchResult.match ? 'green' : 'red' }}>
                        {faceMatchResult.message}
                    </p>
                )}
            </fieldset>

            {/* Step 2: OCR Validation - Enabled only after successful face match */}
             <fieldset style={styles.fieldset} disabled={!imageId || isProcessingFace || isProcessingOCR}>
                 <legend>Step 2: Document Details</legend>
                 <form onSubmit={handleOCRValidation}>
                     <div style={styles.inputGroup}>
                         <label htmlFor='nameInput'>Name (as on ID): </label>
                         <input
                             id='nameInput'
                             type="text"
                             placeholder="Full Name"
                             value={name}
                             onChange={(e) => setName(e.target.value)}
                             required
                          />
                     </div>
                     <div style={styles.inputGroup}>
                         <label htmlFor='dobInput'>Date of Birth: </label>
                         <input
                             id='dobInput'
                             type="date" // Use date input type
                             placeholder="Date of Birth"
                             value={dob}
                             onChange={(e) => setDob(e.target.value)}
                             required
                         />
                     </div>
                     {/* Aadhar Input Removed */}
                     <button type="submit" disabled={!imageId || isProcessingOCR} style={{...styles.button, width: '100%'}}>
                        {isProcessingOCR ? 'Validating Details...' : 'Validate Details & Finish'}
                     </button>
                 </form>
                 {ocrValidationResult && (
        <p style={{ ...styles.message, color: ocrValidationResult.is_valid ? 'green' : 'red' }}>
        {ocrValidationResult.message}
        {ocrValidationResult.details && ` Details: ${ocrValidationResult.details}`}
        {!ocrValidationResult.is_valid && ocrValidationResult.details.includes("Name mismatch") && (
          <span>  Please verify the extracted name.</span>
        )}
    </p>
)}
            </fieldset>

        </div>
    );
}

// Basic Styles (Consider moving to a CSS file)
const styles = {
    container: {
        maxWidth: '500px',
        margin: '20px auto',
        padding: '20px',
        border: '1px solid #ccc',
        borderRadius: '8px',
        fontFamily: 'Arial, sans-serif',
    },
    fieldset: {
        margin: '20px 0',
        padding: '15px',
        border: '1px solid #ddd',
        borderRadius: '5px',
    },
    statusText: {
        color: 'grey',
        fontSize: '0.9em',
        textAlign: 'right',
    },
    inputGroup: {
        marginBottom: '15px',
    },
    label: {
        display: 'block',
        marginBottom: '5px',
        fontWeight: 'bold',
    },
    input: {
        width: 'calc(100% - 12px)', // Adjust for padding
        padding: '8px',
        border: '1px solid #ccc',
        borderRadius: '4px',
    },
    button: {
        padding: '10px 15px',
        backgroundColor: '#007bff',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em',
        opacity: 1,
        transition: 'opacity 0.2s',
    },
    // buttonDisabled: { // Example: Apply this style when disabled
    //    opacity: 0.6,
    //    cursor: 'not-allowed',
    // },
    videoPreview: {
        width: '100%',
        maxWidth: '320px',
        height: 'auto',
        border: '1px solid black',
        backgroundColor: '#f0f0f0',
    },
    capturePreview: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginTop: '10px',
    },
    selfiePreview: {
        width: '100px',
        height: 'auto',
        border: '1px solid green',
    },
    message: {
        marginTop: '10px',
        fontSize: '0.9em',
        fontWeight: 'bold',
    },
};


export default SignupPage;