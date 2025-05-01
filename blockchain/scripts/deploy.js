// HACKINDIA_PROJECT/blockchain/scripts/deploy.js
const hre = require("hardhat");
const fs = require('fs'); // Import fs for writing address/abi
const path = require('path');

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with the account:", deployer.address);
  console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

  const ContractFactory = await hre.ethers.getContractFactory("CampaignFunding"); // <-- Use correct contract name
  console.log("Deploying CampaignFunding contract...");

  const contract = await ContractFactory.deploy(/* constructor args if any */);

  // Wait for the deployment transaction to be mined and confirmed
  await contract.waitForDeployment(); // Recommended way for ethers v6+ with hardhat

  const contractAddress = await contract.getAddress();
  console.log(`CampaignFunding contract deployed to address: ${contractAddress}`);
  console.log("Deployment transaction hash:", contract.deploymentTransaction().hash);

  console.log("\n----------------------------------------------------");
  console.log("Saving contract address and ABI...");

  // --- Save ABI and Address ---
  const artifactsPath = path.join(__dirname, '..', 'artifacts', 'contracts', 'CampaignFunding.sol');
  const abiPath = path.join(artifactsPath, 'CampaignFunding.json');
  const frontendUtilsPath = path.join(__dirname, '..', '..', 'frontend', 'src', 'utils'); // Path to frontend utils
  const configPath = path.join(__dirname, '..', '..', 'config'); // Path to backend config

  if (fs.existsSync(abiPath)) {
    const contractJson = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
    const deploymentInfo = {
      address: contractAddress,
      abi: contractJson.abi
    };

    // Ensure frontend utils directory exists
    if (!fs.existsSync(frontendUtilsPath)) {
       fs.mkdirSync(frontendUtilsPath, { recursive: true });
       console.log(`Created frontend utils directory: ${frontendUtilsPath}`);
    }
    // Ensure config directory exists (it should, but check anyway)
     if (!fs.existsSync(configPath)) {
       fs.mkdirSync(configPath, { recursive: true });
       console.log(`Created config directory: ${configPath}`);
    }


    // Save ABI for frontend
    const frontendAbiPath = path.join(frontendUtilsPath, 'CampaignFunding.json');
    fs.writeFileSync(frontendAbiPath, JSON.stringify(deploymentInfo, null, 2));
    console.log(`Contract ABI and address saved for frontend at: ${frontendAbiPath}`);

    // Update .env file (be careful with this - manual update is safer)
    const envPath = path.join(__dirname, '..', '..', '.env');
     let envContent = "";
     if (fs.existsSync(envPath)) {
        envContent = fs.readFileSync(envPath, 'utf8');
     }

     const addressEnvVar = `CAMPAIGN_CONTRACT_ADDRESS=${contractAddress}`;

     if (envContent.includes('CAMPAIGN_CONTRACT_ADDRESS=')) {
        envContent = envContent.replace(/CAMPAIGN_CONTRACT_ADDRESS=.*/g, addressEnvVar);
        console.log(`Updated CAMPAIGN_CONTRACT_ADDRESS in ${envPath}`);
     } else {
        envContent += `\n${addressEnvVar}`;
        console.log(`Added CAMPAIGN_CONTRACT_ADDRESS to ${envPath}`);
     }
     fs.writeFileSync(envPath, envContent);
     console.warn("ACTION REQUIRED: Restart your backend server for the new contract address to take effect.");


  } else {
    console.error(`Error: ABI file not found at ${abiPath}. Cannot save deployment info.`);
  }
  console.log("----------------------------------------------------");


   // Optional: Verify contract on Etherscan/Polygonscan etc.
   if (hre.network.name !== "hardhat" && hre.network.name !== "localhost") {
       console.log("Waiting for block confirmations before verifying...");
       // Wait for confirmations (adjust number as needed for the network)
       const deployTx = contract.deploymentTransaction();
       if (deployTx){
           await deployTx.wait(6);
           console.log("6 confirmations received. Attempting verification...");
           try {
             await hre.run("verify:verify", {
                 address: contractAddress,
                 constructorArguments: [/* constructor args if any */],
                 // Add contract path if needed: contract: "contracts/CampaignFunding.sol:CampaignFunding"
             });
             console.log("Contract verified successfully!");
           } catch (error) {
             console.error("Verification failed:", error);
             // Common issue: Source code not flatten/uploaded correctly, or bytecode mismatch.
           }
       } else {
           console.log("Could not get deployment transaction for verification.")
       }

   }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });