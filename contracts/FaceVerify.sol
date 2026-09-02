// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title FaceVerify
 * @notice Stores SHA-256 fingerprints of discovered social media posts
 *         for tamper-evident verification on the Sepolia testnet.
 */
contract FaceVerify {
    struct Verification {
        bytes32 postHash;       // SHA-256 fingerprint of the post
        string  postUrl;        // Original post URL
        string  title;          // Post title or description
        string  source;         // Platform name (Instagram, Twitter, etc.)
        uint256 timestamp;      // Block timestamp when recorded
        address uploader;       // Wallet that submitted this record
    }

    // postHash => Verification
    mapping(bytes32 => Verification) public verifications;

    // All stored hashes (for enumeration)
    bytes32[] public storedHashes;

    event PostVerified(
        bytes32 indexed postHash,
        string  postUrl,
        string  source,
        uint256 timestamp,
        address uploader
    );

    /**
     * @notice Store a new post fingerprint on-chain.
     * @param _postHash  SHA-256 hash of the post metadata.
     * @param _postUrl   URL of the discovered post.
     * @param _title     Post title or caption.
     * @param _source    Platform name.
     */
    function verifyPost(
        bytes32 _postHash,
        string calldata _postUrl,
        string calldata _title,
        string calldata _source
    ) external {
        require(verifications[_postHash].timestamp == 0, "Hash already stored");

        verifications[_postHash] = Verification({
            postHash:   _postHash,
            postUrl:    _postUrl,
            title:      _title,
            source:     _source,
            timestamp:  block.timestamp,
            uploader:   msg.sender
        });

        storedHashes.push(_postHash);

        emit PostVerified(_postHash, _postUrl, _source, block.timestamp, msg.sender);
    }

    /**
     * @notice Check whether a post hash has been previously recorded.
     * @param _postHash  SHA-256 hash to verify.
     * @return exists    True if the hash is on-chain.
     */
    function isVerified(bytes32 _postHash) external view returns (bool exists) {
        exists = verifications[_postHash].timestamp != 0;
    }

    /**
     * @notice Retrieve the full verification record for a given hash.
     * @param _postHash  SHA-256 hash to look up.
     */
    function getVerification(bytes32 _postHash)
        external
        view
        returns (
            bytes32 postHash,
            string memory postUrl,
            string memory title,
            string memory source,
            uint256 timestamp,
            address uploader
        )
    {
        Verification storage v = verifications[_postHash];
        require(v.timestamp != 0, "Hash not found");
        return (v.postHash, v.postUrl, v.title, v.source, v.timestamp, v.uploader);
    }

    /**
     * @notice Return total number of stored hashes.
     */
    function getStoredCount() external view returns (uint256) {
        return storedHashes.length;
    }
}
