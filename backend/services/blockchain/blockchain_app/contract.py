import os
from pathlib import Path

from django.conf import settings
from solcx import compile_source, install_solc, set_solc_version

from .web3_client import get_web3, get_deployer_account


# Path to the Solidity contract file
CONTRACT_PATH = Path(__file__).resolve().parent / 'QentisRegistry.sol'


def compile_contract():
    """
    Reads the Solidity file and compiles it to bytecode + ABI.
    Installs solc 0.8.0 if not already installed.
    bytecode — the machine code deployed to the blockchain
    ABI      — the interface that tells web3 how to call the contract functions
    """
    try:
        install_solc('0.8.0')
    except Exception:
        pass  # Already installed

    try:
        set_solc_version('0.8.0')
    except Exception:
        pass

    source = CONTRACT_PATH.read_text()

    compiled = compile_source(
        source,
        output_values=['abi', 'bin'],
        solc_version='0.8.0'
    )

    # The key format after compilation is <stdin>:ContractName
    contract_id = '<stdin>:QentisRegistry'
    contract_interface = compiled[contract_id]

    return contract_interface['abi'], contract_interface['bin']


def deploy_contract():
    """
    Deploys the smart contract to Ganache.
    Called once when the blockchain service starts for the first time.
    Returns the deployed contract address.
    """
    w3        = get_web3()
    deployer  = get_deployer_account(w3)
    abi, bytecode = compile_contract()

    Contract   = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash    = Contract.constructor().transact({'from': deployer})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_receipt.contractAddress


def get_contract():
    """
    Returns a contract instance using the deployed address from settings.
    Every view that needs to call a contract function uses this.
    """
    w3  = get_web3()
    abi, _ = compile_contract()

    contract = w3.eth.contract(
        address=settings.CONTRACT_ADDRESS,
        abi=abi
    )

    return w3, contract


def store_hash_on_chain(item_hash, category, issuer_id, issuer_name):
    """
    Writes a new item hash to the blockchain.
    Called when an item is registered.
    Returns the transaction hash as proof of storage.
    """
    w3, contract = get_contract()
    deployer     = get_deployer_account(w3)

    tx_hash = contract.functions.storeHash(
        item_hash,
        category,
        issuer_id,
        issuer_name
    ).transact({'from': deployer})

    w3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_hash.hex()


def verify_hash_on_chain(item_hash):
    """
    Reads a hash from the blockchain and returns its record.
    This is a read operation — it costs no gas.
    Returns a dict with exists, revoked, category, issuer info, timestamp.
    """
    _, contract = get_contract()

    result = contract.functions.verifyHash(item_hash).call()

    return {
        'exists':        result[0],
        'revoked':       result[1],
        'category':      result[2],
        'issuer_id':     result[3],
        'issuer_name':   result[4],
        'timestamp':     result[5],
        'revoke_reason': result[6],
    }


def revoke_hash_on_chain(item_hash, reason):
    """
    Marks a hash as revoked on the blockchain.
    Called when an issuer revokes an item.
    """
    w3, contract = get_contract()
    deployer     = get_deployer_account(w3)

    tx_hash = contract.functions.revokeHash(
        item_hash,
        reason
    ).transact({'from': deployer})

    w3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_hash.hex()