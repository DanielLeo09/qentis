from web3 import Web3
from django.conf import settings


def get_web3():
    """
    Returns a connected Web3 instance pointing at Ganache.
    Ganache runs at http://ganache:8545 inside Docker.
    """
    w3 = Web3(Web3.HTTPProvider(settings.GANACHE_URL))

    if not w3.is_connected():
        raise ConnectionError(
            f"Cannot connect to Ganache at {settings.GANACHE_URL}. "
            "Make sure Ganache is running in Docker."
        )

    return w3


def get_deployer_account(w3):
    """
    Returns the first Ganache account.
    Ganache auto-generates 10 funded accounts on startup.
    We always use account[0] as the deployer.
    """
    return w3.eth.accounts[0]