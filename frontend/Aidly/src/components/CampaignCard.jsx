// HACKINDIA_PROJECT/frontend/src/components/CampaignCard.jsx
import React, { useState } from 'react';
import PaymentComponent from './PaymentComponent.jsx'; // Use .jsx
import { ethers } from 'ethers'; // To format Ether amounts and parse units

function CampaignCard({ campaign }) {
    const [showPayment, setShowPayment] = useState(false);
    const [showDetails, setShowDetails] = useState(false); // State to toggle details

    // Helper function to safely format amounts (assuming amounts are stored as strings)
    const formatAmount = (amountStr, unit = 'ether') => {
        if (amountStr === null || amountStr === undefined || amountStr === '') return "0.0";
        try {
            // Use parseUnits to handle potential non-string inputs robustly
            const amountWei = ethers.parseUnits(String(amountStr), unit === 'ether' ? 'wei' : unit);
            return ethers.formatUnits(amountWei, unit === 'ether' ? 'ether' : unit); // Format back to Ether (or specified unit)
        } catch (e) {
            console.error(`Error formatting amount: "${amountStr}" with unit "${unit}"`, e);
            return "N/A"; // Return N/A on formatting error
        }
    }

    // Calculate progress percentage safely
    let progress = 0;
    try {
        const goalWei = ethers.parseUnits(String(campaign.goalAmount || '0'), 'wei');
        const raisedWei = ethers.parseUnits(String(campaign.amountRaised || '0'), 'wei');
        // Use BigInt division for precision, convert to number for percentage calculation
        if (goalWei > 0n) { // Use BigInt comparison
             const percentageBasisPoints = (raisedWei * 10000n) / goalWei; // Calculate in basis points (multiplied by 10000)
             progress = Math.min(Number(percentageBasisPoints) / 100, 100); // Convert back to percentage (divide by 100)
        }
    } catch (e) {
         console.error("Error calculating progress for campaign:", campaign._id, e);
         progress = 0; // Default to 0 on error
    }

    // Determine status color
    const getStatusColor = (status) => {
        switch (status) {
            case 'verified': return 'green';
            case 'rejected': return 'red';
            case 'pending_verification': return 'orange';
            case 'verification_error': return 'purple';
            case 'completed': return 'blue'; // Example
            case 'expired': return 'grey';   // Example
            default: return 'black';
        }
    }

    // IPFS Gateway URL (use a public gateway)
    const ipfsGateway = "https://ipfs.io/ipfs/"; // Or use a preferred gateway like cloudflare-ipfs.com

    return (
        <div style={styles.card}>
            <h3 style={styles.title}>{campaign.title || 'Untitled Campaign'}</h3>
            <p style={styles.creator}><i>by {campaign.creatorName || 'Unknown Creator'}</i></p>

             {/* Status Display */}
             <p style={{ ...styles.status, color: getStatusColor(campaign.status) }}>
                Status: {campaign.status?.replace(/_/g, ' ') || 'Unknown'}
             </p>

            {/* Basic Description */}
            <p style={styles.description}>
                {showDetails ? campaign.description : `${(campaign.description || '').substring(0, 80)}...`}
                {campaign.description && campaign.description.length > 80 && (
                    <button onClick={() => setShowDetails(!showDetails)} style={styles.detailsToggle}>
                        {showDetails ? 'Show Less' : 'Show More'}
                    </button>
                )}
            </p>

             {/* Progress Bar */}
             <div style={styles.progressContainer}>
                 <div style={styles.progressBarBackground}>
                     <div style={{ ...styles.progressBarFill, width: `${progress}%` }}></div>
                 </div>
                 <p style={styles.progressText}>
                    Raised: {formatAmount(campaign.amountRaised)} ETH / Goal: {formatAmount(campaign.goalAmount)} ETH ({progress.toFixed(1)}%)
                 </p>
            </div>

            {/* Links and Actions */}
            <div style={styles.linksAndActions}>
                 {campaign.details_ipfs_cid && !campaign.details_ipfs_cid.startsWith('N/A') && (
                    <a href={`${ipfsGateway}${campaign.details_ipfs_cid}`} target="_blank" rel="noopener noreferrer" style={styles.ipfsLink}>
                        View Details (IPFS)
                    </a>
                 )}
                 {/* Only show fund button if status is verified */}
                 {campaign.status === 'verified' && (
                     <button onClick={() => setShowPayment(!showPayment)} style={styles.fundButton}>
                        {showPayment ? 'Cancel Funding' : 'Fund Campaign'}
                    </button>
                 )}
            </div>


            {/* Show PaymentComponent when button is clicked */}
            {showPayment && campaign.status === 'verified' && (
                <PaymentComponent
                     campaignId={campaign._id} // Pass MongoDB ID
                     campaignTitle={campaign.title}
                     onPaymentSuccess={() => {
                         console.log("Payment successful callback received in Card.");
                         setShowPayment(false);
                         // TODO: Optionally trigger a refresh of this card's data or the list
                     }}
                 />
            )}
        </div>
    );
}

// Styles (Consider moving to CSS Modules or styled-components)
const styles = {
    card: {
        border: '1px solid #eee',
        padding: '15px 20px',
        borderRadius: '8px',
        width: '320px', // Fixed width or use flex-basis for responsiveness
        boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px', // Spacing between elements
        backgroundColor: 'white',
    },
    title: {
        margin: '0 0 5px 0',
        fontSize: '1.2em',
    },
    creator: {
        margin: '0 0 10px 0',
        fontSize: '0.9em',
        color: '#555',
    },
    status: {
        fontWeight: 'bold',
        fontSize: '0.9em',
        textTransform: 'capitalize',
    },
    description: {
        fontSize: '0.95em',
        color: '#333',
        lineHeight: '1.4',
        marginBottom: '10px',
    },
    detailsToggle: {
        background: 'none',
        border: 'none',
        color: '#007bff',
        cursor: 'pointer',
        fontSize: '0.9em',
        padding: '0 0 0 5px',
    },
    progressContainer: {
         marginBottom: '10px',
    },
     progressBarBackground: {
         background: '#e9ecef',
         borderRadius: '5px',
         height: '10px', // Thinner progress bar
         overflow: 'hidden',
         width: '100%',
    },
     progressBarFill: {
         background: '#28a745', // Green color for progress
         height: '100%',
         transition: 'width 0.5s ease-in-out',
         borderRadius: '5px',
    },
    progressText: {
         fontSize: '0.85em',
         marginTop: '5px',
         color: '#495057',
    },
     linksAndActions: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 'auto', // Push to bottom
        paddingTop: '10px',
        borderTop: '1px solid #f0f0f0',
    },
     ipfsLink: {
        fontSize: '0.9em',
        color: '#007bff',
        textDecoration: 'none',
     },
    // ipfsLinkHover: { textDecoration: 'underline' },
     fundButton: {
        padding: '6px 12px',
        fontSize: '0.9em',
        backgroundColor: '#007bff',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
     },
    // fundButtonHover: { backgroundColor: '#0056b3' },
};


export default CampaignCard;