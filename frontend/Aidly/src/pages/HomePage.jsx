// HACKINDIA_PROJECT/frontend/src/components/HomePage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CampaignList from '../components/CampaignList.jsx';
import CampaignForm from '../components/CampaignForm.jsx';
// Removed checkAuthStatus import as the basic check is done here, backend check adds complexity

function HomePage() {
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [userName, setUserName] = useState('');
    const [shouldRefreshList, setShouldRefreshList] = useState(false); // State to trigger list refresh
    const navigate = useNavigate();

     // Get username and check validation status on load
    useEffect(() => {
        const storedName = localStorage.getItem('userName');
        const isValidated = localStorage.getItem('isValidated') === 'true';

        if (!storedName || !isValidated) {
            console.warn("User not validated or name missing in localStorage, redirecting to signup.");
            // Clear potentially partial auth state
            localStorage.removeItem('userName');
            localStorage.removeItem('isValidated');
            navigate('/'); // Redirect to signup/login page
        } else {
            setUserName(storedName);
            console.log(`Welcome back, validated user: ${storedName}`);
            // Optional: Could add a periodic checkAuthStatus(storedName) call to backend
            // to ensure session validity if backend sessions are implemented.
        }
    }, [navigate]); // Re-run if navigate changes (shouldn't happen often)

    const handleLogout = () => {
        console.log("Logging out user:", userName);
        localStorage.removeItem('userName');
        localStorage.removeItem('isValidated');
        // Optionally call a backend logout endpoint if sessions are used
        navigate('/');
    };

    const handleCampaignCreated = () => {
        // Callback after form submission to hide form and trigger list refresh
        console.log("Campaign created/submitted, hiding form and refreshing list.");
        setShowCreateForm(false);
        setShouldRefreshList(true); // Signal CampaignList to refresh
    };

    const handleSuccessfulPayment = () => {
        console.log("Payment successful, signaling list refresh.");
        setShouldRefreshList(true); // Trigger refresh in CampaignList
    };


    // Reset refresh trigger after CampaignList has potentially used it
    useEffect(() => {
        if (shouldRefreshList) {
            setShouldRefreshList(false);
        }
    }, [shouldRefreshList]);

    return (
        <div style={styles.homeContainer}>
            <header style={styles.header}>
                <h1>Campaign Dashboard</h1>
                <div style={styles.headerRight}>
                     <span style={styles.welcomeMessage}>Welcome, {userName}!</span>
                     <button onClick={() => setShowCreateForm(!showCreateForm)} style={styles.button}>
                         {showCreateForm ? 'View Campaigns' : '+ Create Campaign'}
                     </button>
                     <button onClick={handleLogout} style={{ ...styles.button, ...styles.logoutButton }}>Logout</button>
                 </div>
            </header>

            <main style={styles.mainContent}>
                {showCreateForm ? (
                    <CampaignForm userName={userName} onCampaignCreated={handleCampaignCreated} />
                ) : (
                    <CampaignList refreshTrigger={shouldRefreshList} onSuccessfulPayment={handleSuccessfulPayment}/> // Pass refresh trigger
                )}
            </main>
        </div>
    );
}

// Basic Styles
const styles = {
    homeContainer: {
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh', // Ensure footer stays down if content is short
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '15px 30px',
        backgroundColor: '#f8f9fa', // Light background
        borderBottom: '1px solid #dee2e6',
        flexShrink: 0, // Prevent header from shrinking
    },
     headerRight: {
        display: 'flex',
        alignItems: 'center',
        gap: '15px',
    },
    welcomeMessage: {
        fontWeight: 'bold',
        marginRight: '10px',
    },
    mainContent: {
        padding: '20px 30px',
        flexGrow: 1, // Allow main content to take up available space
    },
    button: {
        padding: '8px 15px',
        backgroundColor: '#007bff',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.95em',
        transition: 'background-color 0.2s',
    },
    // buttonHover: { // Example: Add :hover styles in CSS
    //     backgroundColor: '#0056b3',
    // },
     logoutButton: {
        backgroundColor: '#dc3545', // Red for logout
     }
    // logoutButtonHover: {
    //     backgroundColor: '#c82333',
    // }
};


export default HomePage;