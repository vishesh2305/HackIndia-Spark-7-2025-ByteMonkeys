// HACKINDIA_PROJECT/frontend/src/components/CampaignCard.jsx
import React, { useState } from 'react';
import PaymentComponent from './PaymentComponent.jsx'; // Use .jsx
import { ethers } from 'ethers'; // To format Ether amounts and parse units

// --- Helper Functions ---

// Formats ETH/Wei amounts
const formatEthAmount = (amountWeiStr) => {
    if (amountWeiStr === null || amountWeiStr === undefined || amountWeiStr === '') return "0.0";
    try {
        // Ensure input is treated as Wei string
        const amountWei = ethers.parseUnits(String(amountWeiStr), 'wei');
        return ethers.formatUnits(amountWei, 'ether'); // Format back to Ether
    } catch (e) {
        console.error(`Error formatting ETH amount (Wei): "${amountWeiStr}"`, e);
        return "N/A";
    }
}

// Formats Fiat amounts with currency symbol (simple version)
const formatFiatAmount = (amountStr, currencyCode) => {
     if (amountStr === null || amountStr === undefined || amountStr === '' || parseFloat(amountStr) === 0) {
        return null; // Don't display if zero or invalid
     }
    try {
        const amount = parseFloat(amountStr);
        // Basic currency symbols - extend as needed
        const symbols = {
            'USD': '$',
            'EUR': '€',
            'INR': '₹',
        };
        const symbol = symbols[currencyCode] || currencyCode; // Default to code if symbol unknown
        // Use Intl.NumberFormat for better locale-aware formatting
        return new Intl.NumberFormat(undefined, { style: 'currency', currency: currencyCode }).format(amount);
        // Fallback formatting:
        // return `${symbol}${amount.toFixed(2)}`;
    } catch (e) {
        console.error(`Error formatting fiat amount: "${amountStr}" with currency "${currencyCode}"`, e);
        return `${currencyCode} N/A`;
    }
}

function CampaignCard({ campaign }) {
    const [showPayment, setShowPayment] = useState(false);
    const [showDetails, setShowDetails] = useState(false);

    // --- Progress Calculation (ETH Only - Simplification) ---
    // NOTE: This progress only reflects ETH goal achievement due to mixed currency complexity.
    let ethProgress = 0;
    let ethGoalFormatted = "0.0";
    let ethRaisedFormatted = "0.0";

    try {
        // Goal is assumed to be in ETH (Wei)
        const goalWei = ethers.parseUnits(String(campaign.goalAmount || '0'), 'wei');
        ethGoalFormatted = formatEthAmount(campaign.goalAmount || '0');

        // amountRaised is assumed to be ETH only (in Wei)
        const raisedWei = ethers.parseUnits(String(campaign.amountRaised || '0'), 'wei');
        ethRaisedFormatted = formatEthAmount(campaign.amountRaised || '0');

        if (goalWei > 0n) {
            const percentageBasisPoints = (raisedWei * 10000n) / goalWei;
            ethProgress = Math.min(Number(percentageBasisPoints) / 100, 100);
        }
    } catch (e) {
        console.error("Error calculating ETH progress for campaign:", campaign._id, e);
        ethProgress = 0;
        ethGoalFormatted = formatEthAmount(campaign.goalAmount || '0'); // Still try to format goal
        ethRaisedFormatted = formatEthAmount(campaign.amountRaised || '0'); // Still try to format raised
    }
    // --- End Progress Calculation ---

    // --- Generate Text for Raised Amounts ---
    const raisedAmountsText = () => {
        const parts = [];
        // ETH part
        parts.push(`${ethRaisedFormatted} ETH`);

        // Add PayPal amounts dynamically (check for fields added by backend)
        for (const key in campaign) {
            if (key.startsWith('amountRaisedPayPal')) {
                const currencyCode = key.substring('amountRaisedPayPal'.length); // e.g., USD, INR
                 const formattedAmount = formatFiatAmount(campaign[key], currencyCode);
                 if (formattedAmount) { // Only add if amount > 0 and formatted correctly
                      parts.push(formattedAmount);
                 }
            }
        }
        // Join with ' + ' if multiple parts exist
        return parts.join(' + ');
    };
    // --- End Raised Amounts Text ---


    const getStatusColor = (status) => {
        switch (status) {
            case 'verified': return 'green';
            case 'rejected': return 'red';
            case 'pending_verification': return 'orange';
            case 'verification_error': return 'purple';
            case 'completed': return 'blue';
            case 'expired': return 'grey';
            default: return 'black';
        }
    }

    const ipfsGateway = "https://ipfs.io/ipfs/";

    return (
        <div style={styles.card}>
            <h3 style={styles.title}>{campaign.title || 'Untitled Campaign'}</h3>
            <p style={styles.creator}><i>by {campaign.creatorName || 'Unknown Creator'}</i></p>

            <p style={{ ...styles.status, color: getStatusColor(campaign.status) }}>
                Status: {campaign.status?.replace(/_/g, ' ') || 'Unknown'}
            </p>

            <p style={styles.description}>
                {showDetails ? campaign.description : `${(campaign.description || '').substring(0, 80)}...`}
                {campaign.description && campaign.description.length > 80 && (
                    <button onClick={() => setShowDetails(!showDetails)} style={styles.detailsToggle}>
                        {showDetails ? 'Show Less' : 'Show More'}
                    </button>
                )}
            </p>

            {/* Progress Bar (Still based on ETH goal/raised) */}
            <div style={styles.progressContainer}>
                <div style={styles.progressBarBackground}>
                    {/* Use ethProgress for the visual bar */}
                    <div style={{ ...styles.progressBarFill, width: `${ethProgress}%` }}></div>
                </div>
                {/* Updated Progress Text */}
                <p style={styles.progressText}>
                    Raised: {raisedAmountsText()} / Goal: {ethGoalFormatted} ETH ({ethProgress.toFixed(1)}% ETH Goal)
                </p>
                <p style={styles.progressNote}>
                    (Progress bar shows ETH goal achievement)
                </p>
            </div>

            {/* Links and Actions */}
            <div style={styles.linksAndActions}>
                {campaign.details_ipfs_cid && !campaign.details_ipfs_cid.startsWith('N/A') && (
                    <a href={`${ipfsGateway}${campaign.details_ipfs_cid}`} target="_blank" rel="noopener noreferrer" style={styles.ipfsLink}>
                        View Details (IPFS)
                    </a>
                )}
                {campaign.status === 'verified' && (
                    <button onClick={() => setShowPayment(!showPayment)} style={styles.fundButton}>
                        {showPayment ? 'Cancel Funding' : 'Fund Campaign'}
                    </button>
                )}
            </div>

            {/* Show PaymentComponent */}
            {showPayment && campaign.status === 'verified' && (
                <PaymentComponent
                    campaignId={campaign._id}
                    campaignTitle={campaign.title}
                    // Pass goal/raised amounts if PaymentComponent needs them
                    // goalAmountEth={ethGoalFormatted}
                    // raisedAmountEth={ethRaisedFormatted}
                    // campaignData={campaign} // Pass full data if needed
                    onPaymentSuccess={() => {
                        console.log("Payment successful callback received in Card.");
                        setShowPayment(false);
                        // TODO: Trigger a refresh of the CampaignList data
                        // This usually involves calling a function passed down from HomePage/CampaignList
                        // For example: props.onSuccessfullPaymentRefreshNeeded();
                    }}
                />
            )}
        </div>
    );
}

// Styles need slight adjustments maybe for the note
const styles = {
    card: {
        border: '1px solid #eee',
        padding: '15px 20px',
        borderRadius: '8px',
        width: '320px',
        boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        backgroundColor: 'white',
    },
    title: { margin: '0 0 5px 0', fontSize: '1.2em' },
    creator: { margin: '0 0 10px 0', fontSize: '0.9em', color: '#555' },
    status: { fontWeight: 'bold', fontSize: '0.9em', textTransform: 'capitalize' },
    description: { fontSize: '0.95em', color: '#333', lineHeight: '1.4', marginBottom: '10px' },
    detailsToggle: { background: 'none', border: 'none', color: '#007bff', cursor: 'pointer', fontSize: '0.9em', padding: '0 0 0 5px' },
    progressContainer: { marginBottom: '10px' },
    progressBarBackground: { background: '#e9ecef', borderRadius: '5px', height: '10px', overflow: 'hidden', width: '100%' },
    progressBarFill: { background: '#28a745', height: '100%', transition: 'width 0.5s ease-in-out', borderRadius: '5px' },
    progressText: { fontSize: '0.85em', marginTop: '5px', color: '#495057', wordWrap: 'break-word' }, // Allow text wrap
    progressNote: { fontSize: '0.75em', color: '#6c757d', fontStyle: 'italic', marginTop: '2px' }, // Style for the note
    linksAndActions: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid #f0f0f0' },
    ipfsLink: { fontSize: '0.9em', color: '#007bff', textDecoration: 'none' },
    fundButton: { padding: '6px 12px', fontSize: '0.9em', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
};

export default CampaignCard;