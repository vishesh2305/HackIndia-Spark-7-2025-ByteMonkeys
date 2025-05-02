// HACKINDIA_PROJECT/frontend/src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import SignupPage from './pages/SignupPage.jsx'; // Use .jsx
import HomePage from './pages/HomePage.jsx';   // Use .jsx
import './App.css'; // Optional global styles
import { initWeb3 } from './utils/web3.jsx';

// Simple private route component using Outlet for nested routes
const PrivateRoute = () => {
  // Check authentication status (e.g., from localStorage)
  // This is a basic check; consider more robust auth state management
  const isAuthenticated = localStorage.getItem('isValidated') === 'true' && localStorage.getItem('userName');
  console.log("PrivateRoute Check: isAuthenticated =", isAuthenticated); // Debug log

  return isAuthenticated ? <Outlet /> : <Navigate to="/" replace />;
};

function App() {
    return (
        <Router>
            <div className="App"> {/* Optional: Add a container class */}
                {/* Consider adding a persistent Navbar/Header here */}
                <Routes>
                    {/* Public Route */}
                    <Route path="/" element={<SignupPage />} />

                    {/* Private Routes */}
                    <Route element={<PrivateRoute />}>
                        {/* All routes nested under PrivateRoute require authentication */}
                        <Route path="/home" element={<HomePage />} />
                        {/* Add other private routes here if needed */}
                        {/* Example: <Route path="/profile" element={<UserProfile />} /> */}
                    </Route>

                     {/* Fallback route for unknown paths */}
                     <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
                 {/* Consider adding a persistent Footer here */}
            </div>
        </Router>
    );
}

export default App;