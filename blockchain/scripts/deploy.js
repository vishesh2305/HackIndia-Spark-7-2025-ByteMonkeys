const hre = require("hardhat");
const fs = require('fs');
const path = require('path');

async function main() {
  // Get the deployer account
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with the account:", deployer.address);
  console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

  // Deploy the CampaignFunding contract
  const ContractFactory = await hre.ethers.getContractFactory("CampaignFunding");
  console.log("Deploying CampaignFunding contract...");
  const contract = await ContractFactory.deploy(); // Add constructor args if needed

  // Wait for the deployment transaction to be mined
  await contract.waitForDeployment();
  const contractAddress = await contract.getAddress();
  console.log(`CampaignFunding contract deployed to address: ${contractAddress}`);
  console.log("Deployment transaction hash:", contract.deploymentTransaction().hash);

  console.log("\n----------------------------------------------------");
  console.log("Saving contract address and ABI...");

  // Define paths
  const artifactsPath = path.join(__dirname, '..', 'artifacts', 'contracts', 'CampaignFunding.sol');
  const abiPath = path.join(artifactsPath, '/CampaignFunding.json');
  const frontendUtilsPath = path.join(__dirname, '..', '..', 'frontend', 'Aidly', 'src', 'utils'); // Correct path
  const envPath = path.join(__dirname, '..', '..', 'backend', '.env'); // Backend .env path

  // Load the ABI from Hardhat artifacts
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

    // Save ABI and address for frontend
    const frontendAbiPath = path.join(frontendUtilsPath, 'CampaignFunding.json');
    fs.writeFileSync(frontendAbiPath, JSON.stringify(deploymentInfo, null, 2));
    console.log(`Contract ABI and address saved for frontend at: ${frontendAbiPath}`);

    // Update backend .env file
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

  // Optional: Verify contract on Etherscan/Polygonscan (for non-local networks)
  if (hre.network.name !== "hardhat" && hre.network.name !== "localhost") {
    console.log("Waiting for block confirmations before verifying...");
    const deployTx = contract.deploymentTransaction();
    if (deployTx) {
      await deployTx.wait(6); // Wait fo4r 6 confirmations
      console.log("6 confirmations received. Attempting verification...");
      try {
        await hre.run("verify:verify", {
          address: contractAddress,
          constructorArguments: [], // Add constructor args if any
        });
        console.log("Contract verified successfully!");
      } catch (error) {
        console.error("Verification failed:", error);
      }
    } else {
      console.log("Could not get deployment transaction for verification.");
    }
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });