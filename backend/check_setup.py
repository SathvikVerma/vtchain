"""Self-serve setup status checker — run this anytime to see exactly what's
configured vs. still needed, without having to ask anyone.

    python check_setup.py
"""
import os
import sys

from dotenv import dotenv_values

ENV_PATH = ".env"


def status_line(label: str, ok: bool, detail: str = "") -> None:
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))


def main() -> None:
    if not os.path.exists(ENV_PATH):
        print("❌ No .env file found. Run: cp .env.example .env")
        sys.exit(1)

    env = dotenv_values(ENV_PATH)

    print("=== VTChain setup status ===\n")

    print("Gemini (negotiation + auditor):")
    gemini_key = env.get("GEMINI_API_KEY", "")
    status_line("GEMINI_API_KEY set", bool(gemini_key), "ready" if gemini_key else "get one at aistudio.google.com")

    print("\nMongoDB Atlas (transaction logging):")
    mongo_uri = env.get("MONGODB_URI", "")
    is_placeholder = "user:pass@cluster.mongodb.net" in mongo_uri
    status_line(
        "MONGODB_URI set to a real cluster",
        bool(mongo_uri) and not is_placeholder,
        "still the placeholder — sign up free at mongodb.com/cloud/atlas" if is_placeholder else "ready",
    )

    print("\nGoDaddy ANS (identity verification):")
    ans_mock = env.get("ANS_USE_MOCK", "true").lower() == "true"
    ans_base = env.get("ANS_API_BASE_URL", "")
    ans_key = env.get("ANS_API_KEY", "")
    if ans_mock:
        status_line("Running in MOCK mode", True, "fully demoable, not hitting a real GoDaddy server")
    else:
        status_line("ANS_API_BASE_URL set", bool(ans_base))
        status_line("ANS_API_KEY set", bool(ans_key))
    ans_domain = env.get("ANS_ROOT_DOMAIN", "")
    is_real_domain = bool(ans_domain) and ans_domain != "vtchain.xyz"
    status_line(
        "ANS_ROOT_DOMAIN is a real registered domain",
        is_real_domain,
        f"currently '{ans_domain}' — update once you've registered with code MLH0918VTH" if not is_real_domain else "ready",
    )

    print("\nSolana devnet:")
    buyer_key_path = env.get("SOLANA_BUYER_KEYPAIR_PATH", "./keys/buyer.json")
    seller_key_path = env.get("SOLANA_SELLER_KEYPAIR_PATH", "./keys/seller.json")
    buyer_exists = os.path.exists(buyer_key_path)
    seller_exists = os.path.exists(seller_key_path)
    status_line("Buyer wallet generated", buyer_exists, "run: python -m app.solana_client.setup_wallets" if not buyer_exists else "ready")
    status_line("Seller wallet generated", seller_exists)

    print("\n=== What's blocking a full live run ===")
    blockers = []
    if not gemini_key:
        blockers.append("Set GEMINI_API_KEY in .env")
    if is_placeholder:
        blockers.append("Set a real MONGODB_URI in .env (or the app will fail on any DB write)")
    if not buyer_exists or not seller_exists:
        blockers.append("Run: python -m app.solana_client.setup_wallets")
    if not is_real_domain:
        blockers.append("(optional but recommended) Register your GoDaddy domain and set ANS_ROOT_DOMAIN")

    if blockers:
        for b in blockers:
            print(f"  - {b}")
    else:
        print("  Nothing blocking — you're ready for a live run.")
        print("  Try: python -m app.agents.test_negotiation")


if __name__ == "__main__":
    main()
