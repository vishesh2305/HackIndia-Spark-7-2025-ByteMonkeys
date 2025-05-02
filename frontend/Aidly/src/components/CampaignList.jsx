// HACKINDIA_PROJECT/frontend/src/components/CampaignList.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { fetchCampaigns } from '../utils/api.jsx'; // Use .jsx
import CampaignCard from './CampaignCard.jsx';   // Use .jsx

function CampaignList({ refreshTrigger, onSuccessfulPayment }) { // Accept refresh trigger prop
    const [campaigns, setCampaigns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filterStatus, setFilterStatus] = useState('verified'); // Default filter

    // useCallback ensures loadCampaigns doesn't change on every render unless filterStatus changes
    const loadCampaigns = useCallback(async () => {
        console.log(`Loading campaigns with status: ${filterStatus}`);
        setLoading(true);
        setError(null);
        try {
            const data = await fetchCampaigns(filterStatus); // Use current filter status
            // Ensure data is an array
            setCampaigns(Array.isArray(data) ? data : []);
        } catch (err) {
            setError(err.message);
            console.error("Error fetching campaigns:", err);
            setCampaigns([]); // Clear campaigns on error
        } finally {
            setLoading(false);
        }
    }, [filterStatus]); // Dependency: re-create loadCampaigns only if filterStatus changes

    // Initial load and reload when filter changes
    useEffect(() => {
        loadCampaigns();
    }, [loadCampaigns]); // Run when loadCampaigns function itself changes (due to filterStatus)

    // Reload when the refreshTrigger prop changes (from HomePage)
    useEffect(() => {
        if (refreshTrigger) {
            console.log("Refresh trigger received, reloading campaigns...");
            loadCampaigns();
        }
    }, [refreshTrigger, loadCampaigns]); // Depend on trigger and loadCampaigns

    const handleFilterChange = (e) => {
        setFilterStatus(e.target.value);
    }

    const renderContent = () => {
        if (loading) return <p style={styles.message}>Loading campaigns...</p>;
        if (error) return <p style={styles.errorMessage}>Error loading campaigns: {error}</p>;
        if (campaigns.length === 0) return <p style={styles.message}>No campaigns found matching the filter '{filterStatus}'.</p>;

        return (
            <div style={styles.listContainer}>
                {campaigns.map(campaign => (
                    // Ensure campaign has a unique _id before rendering card
                    campaign?._id ? <CampaignCard key={campaign._id} campaign={campaign} onSuccessfulPayment={onSuccessfulPayment}/> : null
                ))}
            </div>
        );
    }

    return (
        <div>
            <div style={styles.controls}>
                <h2>Campaigns</h2>
                <div>
                     <label htmlFor="statusFilter" style={{marginRight: '10px'}}>Filter by Status:</label>
                     <select id="statusFilter" value={filterStatus} onChange={handleFilterChange} style={styles.select}>
                         <option value="verified">Verified</option>
                         <option value="pending_verification">Pending Verification</option>
                         <option value="rejected">Rejected</option>
                         {/* Add other statuses if needed (e.g., completed, expired) */}
                         <option value="all">All</option>
                     </select>
                     <button onClick={loadCampaigns} disabled={loading} style={styles.button}>
                        {loading ? 'Refreshing...' : 'Refresh List'}
                     </button>
                </div>
            </div>
            {renderContent()}
        </div>
    );
}

// Basic Styles
const styles = {
    controls: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        paddingBottom: '10px',
        borderBottom: '1px solid #eee',
    },
    select: {
        padding: '5px 8px',
        marginRight: '15px',
        borderRadius: '4px',
        border: '1px solid #ccc',
    },
    button: {
        padding: '6px 12px',
        backgroundColor: '#6c757d', // Grey color
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.9em',
    },
    listContainer: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '20px', // Spacing between cards
    },
    message: {
        marginTop: '20px',
        textAlign: 'center',
        color: '#6c757d', // Grey text
    },
     errorMessage: {
        marginTop: '20px',
        textAlign: 'center',
        color: 'red',
        fontWeight: 'bold',
    }
};

export default CampaignList;