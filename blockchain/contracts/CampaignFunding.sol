// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.0 <0.9.0;

contract CampaignFunding {

    struct Campaign {
        uint256 id;
        address payable creator; // Address of the campaign creator
        string title;
        string detailsIpfsCID; // IPFS hash for full details (description, etc.)
        uint256 goalAmount;     // Funding goal in WEI
        uint256 amountRaised;   // Current amount raised in WEI
        uint256 deadline;       // Unix timestamp for campaign end (0 for no deadline)
        CampaignStatus status; // Status: Pending, Verified, Rejected, Completed, Expired
        mapping(address => uint256) funders; // Track amount funded by each address
    }

    enum CampaignStatus { Pending, Verified, Rejected, Completed, Expired }

    // Mapping validation data hashes (from your existing logic)
    mapping(string => bool) public validationDataHashes; // hash => exists

    // Mapping from campaign ID to Campaign struct
    mapping(uint256 => Campaign) public campaigns;
    uint256 public campaignCounter; // To generate unique campaign IDs

    address public owner; // Contract owner (deployer) for administrative tasks

    event CampaignCreated(uint256 id, address creator, string title, uint256 goal, uint256 deadline);
    event CampaignStatusUpdated(uint256 id, CampaignStatus newStatus);
    event ContributionReceived(uint256 campaignId, address funder, uint256 amount);
    event FundsWithdrawn(uint256 campaignId, address creator, uint256 amount);
    event ValidationHashStored(string dataHash);


    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    modifier onlyVerifiedCampaign(uint256 _id) {
        require(campaigns[_id].id != 0, "Campaign does not exist");
        require(campaigns[_id].status == CampaignStatus.Verified, "Campaign is not verified for funding");
        // Optionally check deadline
        // require(block.timestamp < campaigns[_id].deadline || campaigns[_id].deadline == 0, "Campaign has ended");
        _;
    }

    constructor() {
        owner = msg.sender;
        campaignCounter = 0;
    }

    // --- Validation Hash Storage (from your original contract) ---
    function storeValidationHash(string memory _hash) public {
        // Add permission control if needed (e.g., only backend server)
        require(!validationDataHashes[_hash], "Hash already stored");
        validationDataHashes[_hash] = true;
        emit ValidationHashStored(_hash);
    }

    // --- Campaign Management ---

    function createCampaign(
        string memory _title,
        string memory _detailsIpfsCID,
        uint256 _goalAmount, // In WEI
        uint256 _deadline // Unix timestamp, 0 for no deadline
    ) public returns (uint256) {
        // Optional: Check if msg.sender is validated (requires linking validation hash to address)
        campaignCounter++;
        Campaign storage newCampaign = campaigns[campaignCounter];
        newCampaign.id = campaignCounter;
        newCampaign.creator = payable(msg.sender); // Or pass creator address if backend calls this
        newCampaign.title = _title;
        newCampaign.detailsIpfsCID = _detailsIpfsCID;
        newCampaign.goalAmount = _goalAmount;
        newCampaign.amountRaised = 0;
        newCampaign.deadline = _deadline;
        newCampaign.status = CampaignStatus.Pending; // Requires verification

        emit CampaignCreated(campaignCounter, newCampaign.creator, _title, _goalAmount, _deadline);
        return campaignCounter;
    }

    function updateCampaignStatus(uint256 _id, CampaignStatus _newStatus) public onlyOwner {
        require(campaigns[_id].id != 0, "Campaign does not exist");
        require(campaigns[_id].status != CampaignStatus.Completed && campaigns[_id].status != CampaignStatus.Expired, "Campaign already finished");

        campaigns[_id].status = _newStatus;
        emit CampaignStatusUpdated(_id, _newStatus);
    }

    // --- Funding ---

    function contribute(uint256 _id) public payable onlyVerifiedCampaign(_id) {
        require(msg.value > 0, "Contribution must be positive");

        Campaign storage campaign = campaigns[_id];

        campaign.funders[msg.sender] += msg.value;
        campaign.amountRaised += msg.value;

        emit ContributionReceived(_id, msg.sender, msg.value);

        // Optional: Check if goal reached and update status
        if (campaign.amountRaised >= campaign.goalAmount) {
            // Mark as completed? Or just allow withdrawal?
            // campaigns[_id].status = CampaignStatus.Completed;
            // emit CampaignStatusUpdated(_id, CampaignStatus.Completed);
        }
    }

    // --- Withdrawal ---

    function withdrawFunds(uint256 _id) public {
        Campaign storage campaign = campaigns[_id];
        require(campaign.id != 0, "Campaign does not exist");
        require(msg.sender == campaign.creator, "Only creator can withdraw");
        // Allow withdrawal only if goal reached OR deadline passed (depending on rules)
        require(campaign.amountRaised >= campaign.goalAmount || (campaign.deadline != 0 && block.timestamp >= campaign.deadline), "Withdrawal conditions not met");
        // Ensure funds haven't been withdrawn already (add a flag if needed)
        require(campaign.amountRaised > 0, "No funds to withdraw");

        uint256 amountToWithdraw = campaign.amountRaised;
        campaign.amountRaised = 0; // Prevent re-entrancy

        // Transfer funds
        (bool success, ) = campaign.creator.call{value: amountToWithdraw}("");
        require(success, "Transfer failed.");

        emit FundsWithdrawn(_id, campaign.creator, amountToWithdraw);
        // Optionally update status to Completed after withdrawal
        if (campaign.status != CampaignStatus.Completed) {
            campaign.status = CampaignStatus.Completed;
            emit CampaignStatusUpdated(_id, CampaignStatus.Completed);
        }
    }

    // --- Getters ---
    function getCampaignDetails(uint256 _id) public view returns (
        uint256 id,
        address creator,
        string memory title,
        string memory detailsIpfsCID,
        uint256 goalAmount,
        uint256 amountRaised,
        uint256 deadline,
        CampaignStatus status
    ) {
        Campaign storage c = campaigns[_id];
        return (
            c.id,
            c.creator,
            c.title,
            c.detailsIpfsCID,
            c.goalAmount,
            c.amountRaised,
            c.deadline,
            c.status
        );
    }

    function getFunderContribution(uint256 _campaignId, address _funder) public view returns (uint256) {
        return campaigns[_campaignId].funders[_funder];
    }

     // Fallback function to receive Ether directly (optional)
    receive() external payable {
        // Maybe emit an event or revert if direct transfers aren't desired
    }
}