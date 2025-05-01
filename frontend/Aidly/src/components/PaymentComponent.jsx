// HACKINDIA_PROJECT/frontend/src/components/PaymentComponent.jsx
import React, { useState } from 'react';
import { contributeToCampaign } from '../utils/web3.jsx'; // Ethers.js function
import { recordBackendPayment } from '../utils/api.jsx'; // Function to notify backend

function PaymentComponent({ campaignId, campaignTitle, onPaymentSuccess }) {
    const [amountEth, setAmountEth] = useState(''); // Amount input in Ether
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);

    const handlePayment = async () => {
        setError(null); // Clear previous errors
        setSuccessMessage(null);

        // Validate amount
        if (!amountEth || isNaN(parseFloat(amountEth)) || parseFloat(amountEth) <= 0) {
            setError('Please enter a valid positive amount in ETH.');
            return;
        }

        setIsProcessing(true);

        try {
            // Step 1: Send transaction via Wallet using ethers.js util
            console.log(`Initiating contribution of ${amountEth} ETH to campaign ${campaignId}`);
            const paymentResult = await contributeToCampaign(campaignId, amountEth);

            // Check if blockchain transaction was successful
            if (paymentResult && paymentResult.transactionHash) {
                console.log("Blockchain transaction successful:", paymentResult);
                setSuccessMessage(`Contribution sent! Tx: ${paymentResult.transactionHash.substring(0, 10)}... Recording payment...`);

                // Step 2: Send transaction details to backend for recording
                try {
                    console.log("Recording payment details in backend...");
                    const backendRecord = await recordBackendPayment(campaignId, paymentResult);
                    console.log("Backend payment record:", backendRecord);
                     setSuccessMessage(`Payment of ${amountEth} ETH for "${campaignTitle}" recorded successfully!`);
                     setAmountEth(''); // Clear amount field
                     // Notify parent component (e.g., CampaignCard) about success
                     if (onPaymentSuccess) onPaymentSuccess();

                } catch (backendError) {
                     console.error("Error recording payment on backend:", backendError);
                     // Transaction succeeded on chain, but failed to record in our DB - CRITICAL state
                     setError(`Blockchain transaction OK, but backend recording failed: ${backendError.message}. Please contact support with TxHash: ${paymentResult.transactionHash}`);
                     // Don't clear success message in this specific error case
                     setSuccessMessage(`Blockchain OK, Backend Error! Tx: ${paymentResult.transactionHash.substring(0,10)}...`);
                }

            } else {
                // contributeToCampaign handled the user alert for blockchain failure/rejection
                setError('Contribution failed or was cancelled in wallet.');
                setSuccessMessage(null); // Clear any partial success message
            }

        } catch (err) {
            // Catch unexpected errors in the process
            console.error("Payment process error:", err);
            setError(`Payment failed: ${err.message || 'An unexpected error occurred.'}`);
            setSuccessMessage(null);
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div style={styles.paymentContainer}>
            <h4 style={styles.paymentTitle}>Fund "{campaignTitle}"</h4>
            <div style={styles.inputGroup}>
                <label htmlFor={`amount-${campaignId}`} style={styles.label}>
                    Amount (ETH):
                </label>
                <input
                    id={`amount-${campaignId}`}
                    type="number"
                    value={amountEth}
                    onChange={(e) => setAmountEth(e.target.value)}
                    placeholder="e.g., 0.1"
                    step="0.001"
                    min="0.001" // Example minimum contribution
                    disabled={isProcessing}
                    style={styles.input}
                />
            </div>
            <button
                 onClick={handlePayment}
                 disabled={isProcessing || !amountEth}
                 style={styles.button}
                 // Add dynamic style for disabled state
                 // style={isProcessing || !amountEth ? {...styles.button, ...styles.buttonDisabled} : styles.button}
             >
                {isProcessing ? 'Processing...' : 'Contribute via Wallet'}
            </button>
            {/* Display Error OR Success Message */}
            {!isProcessing && error && <p style={styles.errorMessage}>Error: {error}</p>}
            {!isProcessing && successMessage && <p style={styles.successMessage}>{successMessage}</p>}
            {isProcessing && <p style={styles.infoMessage}>Processing transaction, please check your wallet...</p>}
        </div>
    );
}

// Styles
const styles = {
    paymentContainer: {
        border: '1px dashed #007bff', // Blue dashed border
        padding: '15px',
        marginTop: '15px',
        borderRadius: '5px',
        backgroundColor: '#f0f7ff', // Light blue background
    },
    paymentTitle: {
        margin: '0 0 10px 0',
        fontSize: '1.1em',
        color: '#0056b3',
    },
    inputGroup: {
        marginBottom: '10px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
    },
    label: {
        fontWeight: 'bold',
        fontSize: '0.9em',
        flexShrink: 0, // Prevent label from shrinking
    },
    input: {
        flexGrow: 1, // Allow input to take available space
        padding: '8px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        boxSizing: 'border-box',
    },
    button: {
        width: '100%',
        padding: '10px 15px',
        backgroundColor: '#17a2b8', // Teal color
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em',
        marginTop: '5px',
        opacity: 1,
        transition: 'opacity 0.2s, background-color 0.2s',
    },
    // buttonDisabled: {
    //     opacity: 0.6,
    //     cursor: 'not-allowed',
    //     backgroundColor: '#6c757d',
    // },
    errorMessage: {
        color: '#dc3545', // Red
        fontSize: '0.9em',
        marginTop: '10px',
        fontWeight: 'bold',
    },
    successMessage: {
        color: '#28a745', // Green
        fontSize: '0.9em',
        marginTop: '10px',
        fontWeight: 'bold',
    },
     infoMessage: {
        color: '#17a2b8', // Teal
        fontSize: '0.9em',
        marginTop: '10px',
     }
};


export default PaymentComponent;