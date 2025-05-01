// HACKINDIA_PROJECT/frontend/src/components/CampaignForm.jsx
import React, { useState } from 'react';
import { createCampaign } from '../utils/api.jsx'; // Use .jsx
import { ethers } from 'ethers'; // For converting goal to Wei

function CampaignForm({ userName, onCampaignCreated }) { // Receive userName and callback
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [goalAmountEth, setGoalAmountEth] = useState(''); // Goal amount input in Ether
    // Add deadline field if needed: const [deadline, setDeadline] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [resultMessage, setResultMessage] = useState(null); // For success/failure messages

    const handleSubmit = async (e) => {
        e.preventDefault(); // Prevent default form submission behavior
        setIsLoading(true);
        setError(null);
        setResultMessage(null);

        // Validate inputs
        if (!userName) {
             setError("Cannot create campaign: User information missing.");
             setIsLoading(false);
             return;
        }
        if (!title.trim()) {
             setError("Campaign title cannot be empty.");
             setIsLoading(false);
             return;
        }
        if (!description.trim()) {
             setError("Campaign description cannot be empty.");
             setIsLoading(false);
             return;
        }
        if (isNaN(parseFloat(goalAmountEth)) || parseFloat(goalAmountEth) <= 0) {
             setError("Please enter a valid positive funding goal in ETH.");
             setIsLoading(false);
             return;
        }
         // Add deadline validation if used

        try {
            // Convert goal from Ether string to Wei string for backend/contract consistency
            const goalAmountWei = ethers.parseEther(goalAmountEth).toString();

            const campaignData = {
                title: title.trim(),
                description: description.trim(),
                goalAmount: goalAmountWei, // Send goal in Wei string format
                creatorName: userName, // Include creator's name (validated user)
                // deadline: deadline ? new Date(deadline).getTime() / 1000 : 0 // Example: Convert date to Unix timestamp
            };

            console.log("Submitting campaign data:", campaignData);
            const result = await createCampaign(campaignData);
            console.log("Campaign creation result:", result);

            // Handle result based on AI verification status from backend
            let message = `Campaign "${result.title}" created.`;
            let isError = false;

             if (result.status === 'verified') {
                 message += " Status: Verified Successfully! It's ready for funding.";
             } else if (result.status === 'rejected') {
                 message += ` Status: Rejected by automated verification. Reason: ${result.verification_result || 'Not provided'}`;
                 isError = true; // Treat rejection as an error message type
             } else if (result.status === 'pending_verification') {
                message += " Status: Pending Verification. It will be checked shortly.";
             } else { // verification_error or unexpected status
                 message += ` Status: ${result.status || 'Unknown'}. Verification issue occurred.`;
                 isError = true;
             }

            setResultMessage(message);
            if (isError) setError("Verification issue occurred."); // Set generic error state if not verified

            // Clear form only if creation API call itself didn't throw error (even if rejected)
            setTitle('');
            setDescription('');
            setGoalAmountEth('');
            // setDeadline('');

            // Call the callback to notify HomePage (e.g., hide form, refresh list)
            if (onCampaignCreated) onCampaignCreated();

        } catch (err) {
            // Catch errors from the createCampaign API call itself
            console.error("Error creating campaign:", err);
            setError(`Failed to create campaign: ${err.message}`);
            setResultMessage(null); // Clear any previous result message on API error
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={styles.formContainer}>
            <h2>Create New Campaign</h2>
            <form onSubmit={handleSubmit}>
                <div style={styles.inputGroup}>
                    <label htmlFor="title" style={styles.label}>Campaign Title:</label>
                    <input
                        type="text"
                        id="title"
                        style={styles.input}
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        required
                        maxLength={100}
                        disabled={isLoading}
                    />
                </div>
                <div style={styles.inputGroup}>
                    <label htmlFor="description" style={styles.label}>Description:</label>
                    <textarea
                        id="description"
                        style={styles.textarea}
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        required
                        rows={5}
                        maxLength={1000}
                        disabled={isLoading}
                    />
                </div>
                <div style={styles.inputGroup}>
                    <label htmlFor="goal" style={styles.label}>Funding Goal (in ETH):</label>
                    <input
                        type="number"
                        id="goal"
                        style={styles.input}
                        value={goalAmountEth}
                        onChange={(e) => setGoalAmountEth(e.target.value)}
                        required
                        step="0.001" // Allow smaller steps for ETH
                        min="0.001" // Set a reasonable minimum goal
                        placeholder="e.g., 0.5"
                        disabled={isLoading}
                    />
                </div>
                {/* Add Deadline Input if needed */}
                {/* <div style={styles.inputGroup}>
                    <label htmlFor="deadline" style={styles.label}>Deadline (Optional):</label>
                    <input
                        type="date"
                        id="deadline"
                        style={styles.input}
                        value={deadline}
                        onChange={(e) => setDeadline(e.target.value)}
                        min={new Date().toISOString().split("T")[0]} // Minimum today
                        disabled={isLoading}
                    />
                </div> */}
                <button type="submit" disabled={isLoading} style={styles.button}>
                    {isLoading ? 'Creating...' : 'Submit Campaign for Verification'}
                </button>
            </form>
             {/* Display Error or Result Message */}
             {error && <p style={styles.errorMessage}>Error: {error}</p>}
             {resultMessage && !error && <p style={styles.successMessage}>{resultMessage}</p>}
             {resultMessage && error && <p style={styles.errorMessage}>{resultMessage}</p>}
        </div>
    );
}

// Styles
const styles = {
    formContainer: {
        maxWidth: '600px',
        margin: '0 auto',
        padding: '20px',
        border: '1px solid #ddd',
        borderRadius: '8px',
        backgroundColor: '#f9f9f9',
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
        width: '100%',
        padding: '10px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        boxSizing: 'border-box', // Include padding in width
    },
     textarea: {
        width: '100%',
        padding: '10px',
        border: '1px solid #ccc',
        borderRadius: '4px',
        boxSizing: 'border-box',
        minHeight: '100px',
        resize: 'vertical',
        fontFamily: 'inherit', // Use same font as other inputs
    },
     button: {
        width: '100%',
        padding: '12px 15px',
        backgroundColor: '#28a745', // Green color
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1.1em',
        fontWeight: 'bold',
        opacity: 1,
        transition: 'opacity 0.2s, background-color 0.2s',
    },
    // buttonDisabled: { opacity: 0.6, cursor: 'not-allowed' },
    errorMessage: {
        marginTop: '15px',
        color: 'red',
        fontWeight: 'bold',
        textAlign: 'center',
    },
    successMessage: {
        marginTop: '15px',
        color: 'green',
        fontWeight: 'bold',
        textAlign: 'center',
    },

};

export default CampaignForm;