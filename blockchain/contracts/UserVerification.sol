pragma solidity ^0.8.0;

contract UserVerification {
    struct VerificationData {
        bool faceMatch;
        bool ocrMatch;
        string dataHash; // Hash of the user's validated data
        uint timestamp;
    }

    mapping(string => VerificationData) public verifications; // Mapping from a unique user identifier (e.g., hash of Aadhar) to verification data

    event UserVerified(string userId, string dataHash, uint timestamp);

    function storeVerification(string memory userId, bool faceMatch, bool ocrMatch, string memory dataHash) public {
        require(!verifications[userId].faceMatch, "Verification already exists for this user"); // Prevent overwrites

        verifications[userId] = VerificationData(faceMatch, ocrMatch, dataHash, block.timestamp);
        emit UserVerified(userId, dataHash, block.timestamp);
    }

    function getVerification(string memory userId) public view returns (bool, bool, string memory, uint) {
        return (
            verifications[userId].faceMatch,
            verifications[userId].ocrMatch,
            verifications[userId].dataHash,
            verifications[userId].timestamp
        );
    }
}