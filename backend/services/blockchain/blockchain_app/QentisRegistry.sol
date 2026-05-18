// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract QentisRegistry {

    struct ItemRecord {
        string  itemHash;
        string  category;
        string  issuerId;
        string  issuerName;
        uint256 timestamp;
        bool    exists;
        bool    revoked;
        string  revokeReason;
    }

    mapping(string => ItemRecord) private records;
    string[] private allHashes;
    address public owner;

    event ItemRegistered(
        string indexed itemHash,
        string category,
        string issuerId,
        string issuerName,
        uint256 timestamp
    );

    event ItemRevoked(
        string indexed itemHash,
        string reason,
        uint256 timestamp
    );

    constructor() {
        owner = msg.sender;
    }

    function storeHash(
        string memory _itemHash,
        string memory _category,
        string memory _issuerId,
        string memory _issuerName
    ) public {
        require(!records[_itemHash].exists, "Hash already registered.");

        records[_itemHash] = ItemRecord({
            itemHash:     _itemHash,
            category:     _category,
            issuerId:     _issuerId,
            issuerName:   _issuerName,
            timestamp:    block.timestamp,
            exists:       true,
            revoked:      false,
            revokeReason: ""
        });

        allHashes.push(_itemHash);

        emit ItemRegistered(
            _itemHash,
            _category,
            _issuerId,
            _issuerName,
            block.timestamp
        );
    }

    function verifyHash(string memory _itemHash)
        public
        view
        returns (
            bool exists,
            bool revoked,
            string memory category,
            string memory issuerId,
            string memory issuerName,
            uint256 timestamp,
            string memory revokeReason
        )
    {
        ItemRecord memory record = records[_itemHash];
        return (
            record.exists,
            record.revoked,
            record.category,
            record.issuerId,
            record.issuerName,
            record.timestamp,
            record.revokeReason
        );
    }

    function revokeHash(string memory _itemHash, string memory _reason)
        public
    {
        require(records[_itemHash].exists, "Hash not found.");
        require(!records[_itemHash].revoked, "Already revoked.");

        records[_itemHash].revoked      = true;
        records[_itemHash].revokeReason = _reason;

        emit ItemRevoked(_itemHash, _reason, block.timestamp);
    }

    function getTotalRecords() public view returns (uint256) {
        return allHashes.length;
    }
}