"""MongoDB connection (Motor async client) + logging helper."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings
from .models.schemas import TransactionRecord

_client = AsyncIOMotorClient(settings.mongodb_uri)
db = _client[settings.mongodb_db_name]
transactions = db["transactions"]


async def save_transaction(record: TransactionRecord) -> None:
    await transactions.update_one(
        {"transaction_id": record.transaction_id},
        {"$set": record.model_dump(mode="json")},
        upsert=True,
    )


async def get_transaction(transaction_id: str) -> dict | None:
    return await transactions.find_one({"transaction_id": transaction_id}, {"_id": 0})


async def list_transactions(limit: int = 20) -> list[dict]:
    cursor = transactions.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]
