import React from 'react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client' // Correct import for React 18+
import './index.css'
import App from './App.jsx'
import { PayPalScriptProvider } from "@paypal/react-paypal-js";

const paypalClientId = import.meta.env.VITE_PAYPAL_CLIENT_ID;

if (!paypalClientId) {
    console.error("FATAL ERROR: PayPal Client ID not found in environment variables (VITE_PAYPAL_CLIENT_ID).");
    // Optionally render an error message instead of the app
}

const initialOptions = {
    "client-id": paypalClientId,
    currency: "USD", // Set a default currency (can be dynamic later)
    intent: "capture", // Match backend intent ('sale' maps to capture)
};

const root = createRoot(document.getElementById('root')); // Create root correctly for React 18
root.render(
  <React.StrictMode>
    {/* Only render provider if client ID exists */}
    {paypalClientId ? (
        <PayPalScriptProvider options={initialOptions}>
            <App />
        </PayPalScriptProvider>
    ) : (
         <div>Error: PayPal configuration missing.</div>
    )}
  </React.StrictMode>
);
