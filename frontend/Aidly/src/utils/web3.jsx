// HACKINDIA_PROJECT/frontend/src/utils/web3.jsx
import { ethers } from 'ethers';

// Attempt to import ABI and address saved by deploy script
let campaignContractInfo = null;
try {
    // This assumes deploy.js saved CampaignFunding.json in src/utils/
    campaignContractInfo = require('./CampaignFunding.json');
} catch (error) {
    console.error(
        "ERROR: Could not load ./CampaignFunding.json.",
        "Ensure the contract is deployed and the deploy script ran successfully,",
        "saving the file to frontend/src/utils/."
    );
    // Display error to user or disable blockchain features
    // alert("Blockchain features unavailable: Contract details missing.");
}

const CONTRACT_ADDRESS = campaignContractInfo?.address;
const CONTRACT_ABI = campaignContractInfo?.abi;

// Check if contract address is valid (basic check)
if (!CONTRACT_ADDRESS || CONTRACT_ADDRESS === 'YOUR_DEPLOYED_CONTRACT_ADDRESS') {
    console.error(
        "ERROR: CampaignFunding Contract Address is not set correctly in CampaignFunding.json!",
        "Deploy the contract and ensure the deploy script updated the file."
    );
    // Optionally throw an error or display a message to the user
    // alert("Blockchain features are unavailable. Contract address not configured.");
}

let provider = null; // Use null initially
let signer = null;   // Use null initially
let contract = null; // CampaignFunding contract instance

// Function to check and initialize Ethers (idempotent)
export const initWeb3 = async () => {
    // If already initialized and connected, return true
    if (provider && signer && contract && window.ethereum?.isConnected()) {
         try {
             // Quick check if signer is still valid
             await signer.getAddress();
             console.log("Web3 already initialized and signer valid.");
             return true;
         } catch (e) {
              console.warn("Signer no longer valid, re-initializing...");
              // Reset vars to force re-initialization
              provider = null;
              signer = null;
              contract = null;
         }
    }

    if (!window.ethereum) {
        console.error('No Web3 provider found. Please install MetaMask or a compatible wallet.');
        // Avoid alerting every time, component can handle UI feedback
        // alert('Web3 wallet not detected. Please install MetaMask!');
        return false;
    }

    try {
        console.log("Initializing Web3 connection...");
        // Use ethers v6 BrowserProvider
        provider = new ethers.BrowserProvider(window.ethereum, 'any'); // 'any' allows network changes

        // Listen for network changes
        provider.on("network", (newNetwork, oldNetwork) => {
            // Required when network changes
            if (oldNetwork) {
                console.log(`Network changed from ${oldNetwork.name} to ${newNetwork.name}. Re-initializing contract instance.`);
                // Force re-initialization of contract instance on next call if needed
                contract = null; // Invalidate contract instance
                signer = null;   // Invalidate signer
                // Optionally reload page or prompt user
                // window.location.reload();
            }
        });

         // Listen for account changes
         window.ethereum.on('accountsChanged', (accounts) => {
            console.log('Accounts changed:', accounts);
            // Handle account change, e.g., update UI, require re-authentication
            signer = null; // Invalidate signer
            contract = null; // Invalidate contract instance tied to old signer
             // Optionally reload or update state
             window.location.reload(); // Simplest way to handle state change
         });


        // Request account access if needed (returns accounts array)
        console.log("Requesting account access...");
        const accounts = await provider.send("eth_requestAccounts", []);
        if (!accounts || accounts.length === 0) {
            console.error("No accounts found or permission denied.");
            // alert("Wallet connection failed or permission denied.");
            return false;
        }
        console.log("Wallet accounts accessed:", accounts);

        // Get the signer (account)
        signer = await provider.getSigner();
        const signerAddress = await signer.getAddress();
        console.log('Signer obtained:', signerAddress);

        // Create contract instance
        if (!CONTRACT_ADDRESS || !CONTRACT_ABI) {
             console.error("Contract Address or ABI is missing.");
            //  alert("Contract information missing. Cannot initialize blockchain interaction.");
             return false;
        }
        contract = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, signer);
        console.log('CampaignFunding Contract instance created at:', contract.target); // Use contract.target for address in v6

        return true; // Initialization successful
    } catch (error) {
        console.error('Error initializing Web3/Ethers:', error);
        // alert(`Failed to connect to Wallet or Contract: ${error?.message || error}. Please check console.`);
        // Reset state variables on error
        provider = null;
        signer = null;
        contract = null;
        return false;
    }
};

// Get the connected signer address
export const getSignerAddress = async () => {
    if (!signer) {
        console.log("Signer not available, attempting to initialize Web3...");
        const initialized = await initWeb3();
        if (!initialized || !signer) return null; // Check signer again after init
    }
    try {
        return await signer.getAddress();
    } catch (error) {
        console.error("Error getting signer address:", error);
        // Possibly signer became invalid (e.g., user locked wallet)
        signer = null; // Invalidate signer
        contract = null;
        return null;
    }
};

// Store validation hash on the CampaignFunding contract
export const storeValidationHashOnChain = async (dataHash) => {
     if (!contract || !signer) {
        console.error('Web3/Contract not initialized. Cannot store validation hash.');
        const initialized = await initWeb3(); // Attempt re-initialization
        if (!initialized || !contract || !signer) {
             alert("Wallet or Contract not initialized. Please connect/reconnect wallet first.");
             return null;
        }
    }

     if (!dataHash || typeof dataHash !== 'string' || !dataHash.startsWith('0x') || dataHash.length !== 66) {
         console.error("Invalid dataHash provided for blockchain storage:", dataHash);
         alert("Invalid data hash format for blockchain storage.");
         return null;
     }

     try {
         console.log(`Attempting to store validation hash on chain: ${dataHash}`);
         // Ensure function name matches contract: 'storeValidationHash'
         const tx = await contract.storeValidationHash(dataHash);
         console.log('Store hash transaction sent:', tx.hash);

         // Wait for transaction confirmation (recommended)
         alert(`Transaction sent (Hash: ${tx.hash.substring(0,10)}...). Waiting for confirmation...`); // Provide feedback
         const receipt = await tx.wait(1); // Wait for 1 confirmation
         console.log('Store hash transaction confirmed:', receipt);

         if (receipt?.status === 1) {
             console.log('Validation Hash stored successfully!');
             return tx.hash; // Return hash on success
         } else {
             console.error('Blockchain transaction failed (Status 0). Receipt:', receipt);
             alert('Blockchain transaction failed. Check console/wallet for details.');
             return null;
         }
     } catch (error) {
        // Handle common errors like user rejection
        if (error.code === 'ACTION_REJECTED') {
             console.warn('User rejected the transaction.');
             alert('Transaction rejected by user.');
        } else {
            console.error('Error storing validation hash:', error);
            alert(`Failed to store validation hash: ${error?.reason || error?.message || error}`);
        }
        return null;
     }
}

// Fund a campaign
export const contributeToCampaign = async (campaignId, amountInEther) => {
    if (!contract || !signer) {
        console.error('Web3/Contract not initialized. Cannot contribute.');
         const initialized = await initWeb3(); // Attempt re-initialization
         if (!initialized || !contract || !signer) {
              alert("Wallet or Contract not initialized. Please connect/reconnect wallet first.");
              return null; // Indicate failure
         }
    }

    try {
        // Validate amount
        if (isNaN(parseFloat(amountInEther)) || parseFloat(amountInEther) <= 0) {
             alert("Invalid contribution amount.");
             return null;
        }
        const amountInWei = ethers.parseEther(amountInEther.toString()); // Convert Ether string to Wei BigInt
        console.log(`Contributing ${amountInEther} ETH (${amountInWei} WEI) to campaign ID ${campaignId}`);
        const signerAddress = await signer.getAddress();

        // Send transaction to the 'contribute' function
        // Estimate gas (optional, but good practice for complex functions)
        // try {
        //    const gasEstimate = await contract.contribute.estimateGas(campaignId, { value: amountInWei });
        //    console.log("Estimated gas:", gasEstimate.toString());
        //    // Add buffer: const gasLimit = gasEstimate * BigInt(12) / BigInt(10); // 20% buffer
        // } catch (estimateError) {
        //     console.error("Gas estimation failed:", estimateError);
        //     alert(`Could not estimate gas: ${estimateError?.reason || estimateError?.message}`);
        //     return null;
        // }

        const tx = await contract.contribute(campaignId, {
             value: amountInWei
             // gasLimit: gasLimit // Optional: Use estimated gas limit
             });
        console.log('Contribution transaction sent:', tx.hash);

        // Wait for transaction confirmation
        alert(`Contribution sent (Tx: ${tx.hash.substring(0,10)}...). Waiting for confirmation...`);
        const receipt = await tx.wait(1); // Wait for 1 confirmation
        console.log('Contribution transaction confirmed:', receipt);

        if (receipt?.status === 1) {
            console.log('Contribution successful!');
            // Return necessary details for backend recording
            return {
                transactionHash: tx.hash,
                amount: amountInEther, // Send amount back in Ether string format
                funderAddress: signerAddress
            };
        } else {
            console.error('Contribution transaction failed on chain (Status 0). Receipt:', receipt);
            alert('Blockchain transaction failed. Check console/wallet for details.');
            return null;
        }
    } catch (error) {
         if (error.code === 'ACTION_REJECTED') {
             console.warn('User rejected the contribution transaction.');
             alert('Contribution transaction rejected by user.');
         } else {
             console.error('Error contributing to campaign:', error);
             alert(`Contribution failed: ${error?.reason || error?.message || error}`); // Try to get revert reason
         }
        return null; // Indicate failure
    }
};


// Hash data using ethers.js utility (keccak256)
export const hashData = (data) => {
    if (typeof data !== 'object' || data === null) {
        console.error("hashData requires an object input.");
        return null;
    }
    try {
        // Ensure consistent JSON stringification (sort keys, compact)
        const sortedDataString = JSON.stringify(data, Object.keys(data).sort(), 0); // No spaces for compact string
        // Compute Keccak-256 hash (standard for Ethereum) using ethers
        const hash = ethers.keccak256(ethers.toUtf8Bytes(sortedDataString));
        console.log("Hashing data:", sortedDataString, "-> Hash:", hash);
        // Ensure it returns the '0x' prefixed hex string
        return hash;
    } catch (error) {
        console.error("Error hashing data with ethers:", error);
        return null;
    }
};