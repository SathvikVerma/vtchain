"""Central config, loaded from environment variables (.env)."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "vtchain"

    ans_api_base_url: str = ""
    ans_api_key: str = ""
    ans_use_mock: bool = True
    ans_root_domain: str = "vtchain.xyz"  # real GoDaddy-registered domain

    # Real GoDaddy-assigned ANS agent IDs (from `ans-cli register`, one-time
    # setup outside this app). Maps our internal agent_id -> the UUID GoDaddy
    # actually tracks status for. Empty string = not registered for real ANS.
    ans_buyer_agent_id: str = ""
    ans_seller_agent_id: str = ""
    ans_auditor_agent_id: str = ""

    solana_rpc_url: str = "https://api.devnet.solana.com"
    solana_buyer_keypair_path: str = "./keys/buyer.json"
    solana_seller_keypair_path: str = "./keys/seller.json"

    class Config:
        env_file = ".env"


settings = Settings()
