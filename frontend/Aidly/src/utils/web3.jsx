import { ethers } from 'ethers';

// Attempt to import ABI and address saved by deploy script
let campaignContractInfo = null;

try {
    // This assumes deploy.js saved CampaignFunding.json in src/utils/
    campaignContractInfo = require('./CampaignFunding.json');
} catch (error) {
    console.error(
        "ERROR: Could not load ./CampaignFunding.json.\n",
        "Ensure the contract is deployed and the deploy script ran successfully,\n",
        "saving the file to frontend/src/utils/."
    );
    // CRITICAL: Do not proceed if ABI is missing.  Other functions will fail.
    // Consider setting a global flag or throwing an error here.
    campaignContractInfo = { address: null, abi: null }; // Set to null to prevent further errors
    // alert("Blockchain features unavailable: Contract details missing."); // Remove alert.  Handle in component.
}

const CONTRACT_ADDRESS = campaignContractInfo?.address;
console.log(campaignContractInfo);
const CONTRACT_ABI = campaignContractInfo?.abi;

// Check if contract address is valid (basic check)
if (!CONTRACT_ADDRESS || !ethers.isAddress(CONTRACT_ADDRESS)) {
    console.error(
        "ERROR: CampaignFunding Contract Address is not set correctly in CampaignFunding.json!\n",
        "Deploy the contract and ensure the deploy script updated the file."
    );
    // CRITICAL:  Contract address is invalid.  Do not proceed.
    // alert("Blockchain features are unavailable. Contract address not configured."); // Remove alert
}

let provider = null; // Use null initially
let signer = null;   // Use null initially
let contract = null; // CampaignFunding contract instance
let web3Initialized = false; // Track overall initialization state

// Function to check and initialize Ethers (idempotent)
export const initWeb3 = async () => {
    if (web3Initialized) {
        console.log("Web3 already initialized.");
        return true;
    }

    if (!window.ethereum) {
        console.error('No Web3 provider found. Please install MetaMask or a compatible wallet.');
        // IMPORTANT: Do NOT alert here.  Let the component that calls initWeb3 handle this.
        return false;
    }

    try {
        console.log("Initializing Web3 connection...");
        // Use ethers v6 BrowserProvider
        provider = new ethers.BrowserProvider(window.ethereum, 'any'); // 'any' allows network changes

        // Listen for network changes (Crucial for preventing stale contract instances)
        provider.on("network", (newNetwork, oldNetwork) => {
            console.log(`Network changed from ${oldNetwork?.name || 'unknown'} to ${newNetwork.name}`);
            // Reset everything when network changes.
            provider = null;
            signer = null;
            contract = null;
            web3Initialized = false; // Reset the flag
            // Consider forcing a page reload, or emitting an event for components to react.
            window.location.reload(); // Simplest, but can be disruptive.
        });

        // Request account access
        const accounts = await provider.send("eth_requestAccounts", []);
        if (!accounts || accounts.length === 0) {
            console.error("No accounts found or permission denied.");
            return false;
        }

        // Get the signer
        signer = await provider.getSigner();
        const signerAddress = await signer.getAddress();
        console.log('Signer obtained:', signerAddress);

        // Create contract instance
        if (!CONTRACT_ADDRESS || !CONTRACT_ABI) {
            console.error("Contract Address or ABI is missing.");
            return false;
        }
        contract = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, signer);
        console.log('CampaignFunding Contract instance created at:', contract.target);

        web3Initialized = true; // Set the flag only on full success
        return true; // Initialization successful
    } catch (error) {
        console.error('Error initializing Web3/Ethers:', error);
        // IMPORTANT:  Handle specific errors and log them verbosely.
        provider = null;
        signer = null;
        contract = null;
        web3Initialized = false;
        return false; // Return false to indicate failure
    }
};

// Helper function to ensure Web3 is initialized
const ensureWeb3Initialized = async () => {
    if (!web3Initialized) {
        console.warn("Web3 is not initialized.  Attempting to initialize...");
        const success = await initWeb3();
        if (!success) {
            const errorMessage = "Wallet or Contract not initialized. Please connect/reconnect your wallet.";
            console.error(errorMessage);
            alert(errorMessage); // Alert user
            return false; // Return false if initWeb3 fails
        }
    }
    return true; // Return true if already initialized or initialized successfully
};

// Get the connected signer address
export const getSignerAddress = async () => {
    if (!await ensureWeb3Initialized()) {
        return null;
    }
    try {
        return await signer.getAddress();
    } catch (error) {
        console.error("Error getting signer address:", error);
        signer = null;
        contract = null;
        web3Initialized = false;
        return null;
    }
};

// Store validation hash on the CampaignFunding contract
export const storeValidationHashOnChain = async (dataHash) => {
    if (!await ensureWeb3Initialized()) {
        return null;
    }

    if (!dataHash || typeof dataHash !== 'string' || !dataHash.startsWith('0x') || dataHash.length !== 66) {
        console.error("Invalid dataHash provided for blockchain storage:", dataHash);
        alert("Invalid data hash format for blockchain storage.");
        return null;
    }

    try {
        console.log(`Attempting to store validation hash on chain: ${dataHash}`);
        const tx = await contract.storeValidationHash(dataHash);
        console.log('Store hash transaction sent:', tx.hash);

        // Wait for transaction confirmation (recommended)
        alert(`Transaction sent (Hash: ${tx.hash.substring(0, 10)}...). Waiting for confirmation...`);
        const receipt = await tx.wait(1);
        console.log('Store hash transaction confirmed:', receipt);

        if (receipt?.status === 1) {
            console.log('Validation Hash stored successfully!');
            return tx.hash;
        } else {
            console.error('Blockchain transaction failed (Status 0). Receipt:', receipt);
            alert('Blockchain transaction failed. Check console/wallet for details.');
            return null;
        }
    } catch (error) {
        // Handle common errors
        if (error.code === 'ACTION_REJECTED') {
            console.warn('User rejected the transaction.');
            alert('Transaction rejected by user.');
        } else {
            console.error('Error storing validation hash:', error);
            alert(`Failed to store validation hash: ${error?.reason || error?.message || error}`);
        }
        return null;
    }
};

// Fund a campaign
export const contributeToCampaign = async (campaignId, amountInEther) => {
    if (!await ensureWeb3Initialized()) {
        return null;
    }

    try {
        // Validate amount
        if (isNaN(parseFloat(amountInEther)) || parseFloat(amountInEther) <= 0) {
            alert("Invalid contribution amount.");
            return null;
        }

        const amountInWei = ethers.parseEther(amountInEther.toString());
        console.log(`Contributing ${amountInEther} ETH (${amountInWei} WEI) to campaign ID ${campaignId}`);
        const signerAddress = await signer.getAddress();

        const tx = await contract.contribute(campaignId, {
            value: amountInWei
        });
        console.log('Contribution transaction sent:', tx.hash);

        // Wait for transaction confirmation
        alert(`Contribution sent (Tx: ${tx.hash.substring(0, 10)}...). Waiting for confirmation...`);
        const receipt = await tx.wait(1);
        console.log('Contribution transaction confirmed:', receipt);

        if (receipt?.status === 1) {
            console.log('Contribution successful!');
            return {
                transactionHash: tx.hash,
                amount: amountInEther,
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
            alert(`Contribution failed: ${error?.reason || error?.message || error}`);
        }
        return null;
    }
};

// Hash data using ethers.js utility (keccak256)
export const hashData = (data) => {
    if (typeof data !== 'object' || data === null) {
        console.error("hashData requires an object input.");
        return null;
    }
    try {
        const sortedDataString = JSON.stringify(data, Object.keys(data).sort(), 0);
        const hash = ethers.keccak256(ethers.toUtf8Bytes(sortedDataString));
        console.log("Hashing data:", sortedDataString, "-> Hash:", hash);
        return hash;
    } catch (error) {
        console.error("Error hashing data with ethers:", error);
        return null;
    }
};
