from django.apps import AppConfig


class BlockchainAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blockchain_app'

    def ready(self):
        """
        Called when Django starts.
        Pre-installs the Solidity compiler so it is ready
        when the first hash store request comes in.
        """
        try:
            from solcx import install_solc, set_solc_version
            install_solc('0.8.0')
            set_solc_version('0.8.0')
            print("✅ solc 0.8.0 ready")
        except Exception as e:
            print(f"⚠️ solc install warning: {e}")