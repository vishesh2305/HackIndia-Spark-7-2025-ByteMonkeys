// Example: frontend/src/components/PaymentComponent.jsx
import React, { useState } from 'react';
import { PayPalButtons, usePayPalScriptReducer } from "@paypal/react-paypal-js";
import { contributeToCampaign } from '../utils/web3'; // Your existing wallet function
import { recordBackendPayment, createPaypalOrderApi, capturePaypalOrderApi } from '../utils/api'; // API functions

// Assume this component receives props like:
// campaignId, campaignTitle, onPaymentSuccess (callback)
function PaymentComponent({ campaignId, campaignTitle, onPaymentSuccess }) {
    const [paymentMethod, setPaymentMethod] = useState(''); // 'wallet' or 'paypal'
    const [amount, setAmount] = useState('');
    const [currency, setCurrency] = useState('USD'); // Or make dynamic
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState(null);

    // PayPal SDK state and dispatcher
    const [{ options, isPending, isRejected }, dispatch] = usePayPalScriptReducer();

    // --- Wallet Contribution Handler (Keep existing logic) ---
    const handleWalletContribute = async () => {
        if (!amount || parseFloat(amount) <= 0) { setError("Please enter a valid amount."); return; }
        setIsProcessing(true); setError(null);
        try {
            const paymentResult = await contributeToCampaign(campaignId, amount); // web3.jsx
            if (paymentResult) {
                await recordBackendPayment(campaignId, paymentResult); // api.jsx
                alert(`Wallet Contribution Successful! Tx: ${paymentResult.transactionHash.substring(0, 10)}...`);
                if (onPaymentSuccess) onPaymentSuccess();
            } else { setError("Wallet contribution failed."); }
        } catch (err) { setError(`Wallet error: ${err.message}`); console.error(err); }
        finally { setIsProcessing(false); }
    };

    // --- PayPal Button Handlers ---
    const paypalCreateOrder = async (data, actions) => {
        if (!amount || parseFloat(amount) <= 0) {
            setError("Please enter a valid amount for PayPal.");
            throw new Error("Invalid amount"); // Stop PayPal flow
        }
        setError(null);
        setIsProcessing(true); // Indicate processing
        console.log("Requesting PayPal order creation from backend...");
        try {
            // Call backend to create the order
            const orderDetails = await createPaypalOrderApi({
                campaignId: campaignId,
                amount: amount,
                currency: currency
            });
            console.log("Backend created orderID:", orderDetails.orderID);
            setIsProcessing(false); // Backend done, PayPal UI takes over
            return orderDetails.orderID; // Return orderID to PayPal SDK
        } catch (err) {
            console.error("Backend order creation failed:", err);
            setError(`Failed to initiate PayPal payment: ${err.message}`);
            setIsProcessing(false);
            throw err; // Signal error to PayPal Buttons
        }
    };

    const paypalOnApprove = async (data, actions) => {
        console.log("PayPal onApprove data:", data); // Contains orderID, payerID etc.
        setIsProcessing(true);
        setError(null);
        try {
            console.log("Requesting PayPal order capture from backend...");
            // Call backend to capture the payment
            const captureResult = await capturePaypalOrderApi({
                orderID: data.orderID,
                campaignId: campaignId // Pass campaignId for DB updates
            });
            console.log("Backend capture result:", captureResult);
            // Check backend response status
            if (captureResult && captureResult.status === 'success') {
                 alert(`PayPal Payment Successful! PayPal Tx ID: ${captureResult.paypalPaymentId}`);
                 if (onPaymentSuccess) onPaymentSuccess(); // Trigger success callback
            } else {
                throw new Error(captureResult?.message || "Backend failed to confirm payment capture.");
            }
        } catch (err) {
            console.error("Backend capture/DB record failed:", err);
            setError(`Payment capture failed: ${err.message}. If debited, contact support.`);
            // Do NOT call onPaymentSuccess on capture failure
        } finally {
            setIsProcessing(false);
        }
    };

    const paypalOnError = (err) => {
        console.error("PayPal Button Error:", err);
        setError(`PayPal Error: ${err.message}. Please retry or choose another method.`);
        setIsProcessing(false);
    };

    return (
        <div style={styles.paymentBox}>
            <h4>Contribute to: {campaignTitle}</h4>
            {error && <p style={styles.errorText}>Error: {error}</p>}

            <div style={styles.inputGroup}>
                <label htmlFor="amount">Amount: </label>
                <input
                    id="amount"
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="e.g., 10.00"
                    min="0.01" step="0.01"
                    disabled={isProcessing}
                    style={styles.inputField}
                />
                {/* Simple Currency Selector - Make more robust if needed */}
                {paymentMethod === 'paypal' && (
                     <select value={currency} onChange={e => setCurrency(e.target.value)} disabled={isProcessing}>
                         <option value="USD">USD</option>
                         <option value="EUR">EUR</option>
                         <option value="INR">INR</option> {/* Add relevant currencies */}
                     </select>
                )}
                {paymentMethod === 'wallet' && <span>ETH</span>}
            </div>

            <div style={styles.buttonGroup}>
                <button onClick={() => setPaymentMethod('wallet')} disabled={isProcessing} style={paymentMethod === 'wallet' ? styles.selectedButton : styles.button}>Use Wallet</button>
                <button onClick={() => setPaymentMethod('paypal')} disabled={isProcessing} style={paymentMethod === 'paypal' ? styles.selectedButton : styles.button}>Use PayPal</button>
            </div>

            {/* Wallet Button */}
            {paymentMethod === 'wallet' && (
                <button onClick={handleWalletContribute} disabled={!amount || isProcessing} style={styles.submitButton}>
                    {isProcessing ? 'Processing...' : 'Submit Wallet Contribution'}
                </button>
            )}

            {/* PayPal Buttons */}
            {paymentMethod === 'paypal' && (
                <div style={styles.paypalContainer}>
                    {(isPending || isProcessing) && <div>Loading PayPal...</div>}
                    {isRejected && <div style={styles.errorText}>Error loading PayPal script. Check Client ID.</div>}
                    {/* Render PayPal Buttons only when SDK is ready, not processing, and amount is valid */}
                    {!isPending && !isRejected && !isProcessing && amount && parseFloat(amount) > 0 && (
                        <PayPalButtons
                            style={{ layout: "vertical", label: 'pay' }}
                            createOrder={paypalCreateOrder}
                            onApprove={paypalOnApprove}
                            onError={paypalOnError}
                            forceReRender={[amount, currency, campaignId]} // Re-render if these change
                            disabled={!amount || parseFloat(amount) <= 0 || isProcessing}
                        />
                    )}
                    {(!amount || parseFloat(amount) <= 0) && !isProcessing && <p>Enter amount to pay with PayPal.</p>}
                </div>
            )}
        </div>
    );
}

// Add some basic styles
const styles = {
    paymentBox: { border: '1px solid #ddd', padding: '15px', marginTop: '10px', borderRadius: '4px' },
    inputGroup: { marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '5px' },
    inputField: { padding: '5px', width: '100px'},
    buttonGroup: { display: 'flex', gap: '10px', marginBottom: '15px' },
    button: { padding: '8px', cursor: 'pointer', border: '1px solid #ccc' },
    selectedButton: { padding: '8px', cursor: 'pointer', border: '2px solid #007bff' },
    submitButton: { padding: '10px', width: '100%', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'},
    paypalContainer: { marginTop: '15px', position: 'relative', zIndex: 0 }, // zIndex helps if elements overlap
    errorText: { color: 'red', fontSize: '0.9em' },
};

export default PaymentComponent;