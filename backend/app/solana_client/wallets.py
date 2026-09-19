"""Devnet wallet management.

Person A: run `python -m app.solana_client.setup_wallets` once to generate
buyer/seller devnet keypairs and airdrop test SOL into them. Never use
mainnet, never use real money — devnet only.
"""
from __future__ import annotations

import json
import os

from solders.keypair import Keypair


def load_or_create_keypair(path: str) -> Keypair:
    """Load a keypair from a JSON file (Solana CLI format: array of 64 ints),
    or generate + save a new one if it doesn't exist yet."""
    if os.path.exists(path):
        with open(path) as f:
            secret = json.load(f)
        return Keypair.from_bytes(bytes(secret))

    keypair = Keypair()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(list(bytes(keypair)), f)
    return keypair
