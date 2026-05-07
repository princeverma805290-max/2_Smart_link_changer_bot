import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import MONGO_URL, OWNER_ID, DEFAULT_REQ_DELAY, PIC_START

logger = logging.getLogger(__name__)

client   = AsyncIOMotorClient(MONGO_URL)
db       = client["tp_links_bot"]

col_config   = db["config"]
col_admins   = db["admins"]
col_channels = db["channels"]
col_tokens   = db["tokens"]
col_pending  = db["pending"]
col_users    = db["users"]


# ── CONFIG ───────────────────────────────────────────
async def get_config() -> dict:
    cfg = await col_config.find_one({"_id": "main"})
    if not cfg:
        cfg = {
            "_id":       "main",
            "owner_id":  OWNER_ID,
            "req_mode":  True,
            "req_delay": DEFAULT_REQ_DELAY,
            "start_pic": PIC_START,
            "stats":     {"total_approved": 0, "total_requests": 0}
        }
        await col_config.insert_one(cfg)
    return cfg

async def set_config(key: str, value):
    await col_config.update_one(
        {"_id": "main"}, {"$set": {key: value}}, upsert=True
    )

async def inc_stat(key: str, amount: int = 1):
    await col_config.update_one(
        {"_id": "main"}, {"$inc": {f"stats.{key}": amount}}, upsert=True
    )


# ── OWNER / ADMINS ───────────────────────────────────
async def get_owner() -> int:
    cfg = await get_config()
    return cfg.get("owner_id", OWNER_ID)

async def is_owner(uid: int) -> bool:
    return uid == await get_owner()

async def is_admin(uid: int) -> bool:
    if await is_owner(uid):
        return True
    return bool(await col_admins.find_one({"user_id": uid}))

async def add_admin(uid: int) -> bool:
    if await col_admins.find_one({"user_id": uid}):
        return False
    await col_admins.insert_one({"user_id": uid})
    return True

async def remove_admin(uid: int) -> bool:
    res = await col_admins.delete_one({"user_id": uid})
    return res.deleted_count > 0

async def get_all_admins() -> list:
    return [d["user_id"] async for d in col_admins.find({})]


# ── CHANNELS ─────────────────────────────────────────
async def add_channel(channel_id: int, channel_name: str, invite_link: str, token: str):
    await col_channels.update_one(
        {"channel_id": channel_id},
        {"$set": {
            "channel_id":   channel_id,
            "channel_name": channel_name,
            "invite_link":  invite_link,
            "token":        token,
            "approve_on":   True,
            "dm_on":        True,
        }},
        upsert=True
    )

async def remove_channel(channel_id: int) -> bool:
    res = await col_channels.delete_one({"channel_id": channel_id})
    await col_tokens.delete_one({"channel_id": channel_id})
    await col_pending.delete_many({"channel_id": channel_id})
    return res.deleted_count > 0

async def get_channel(channel_id: int) -> dict | None:
    return await col_channels.find_one({"channel_id": channel_id})

async def get_all_channels() -> list:
    return [d async for d in col_channels.find({})]

async def update_channel(channel_id: int, key: str, value):
    await col_channels.update_one({"channel_id": channel_id}, {"$set": {key: value}})

async def channel_exists(channel_id: int) -> bool:
    return bool(await col_channels.find_one({"channel_id": channel_id}))


# ── TOKENS ───────────────────────────────────────────
async def set_token(channel_id: int, token: str, expires_at: float):
    await col_tokens.update_one(
        {"channel_id": channel_id},
        {"$set": {"channel_id": channel_id, "token": token, "expires_at": expires_at}},
        upsert=True
    )

async def get_token_by_channel(channel_id: int) -> dict | None:
    return await col_tokens.find_one({"channel_id": channel_id})

async def get_channel_by_token(token: str) -> dict | None:
    doc = await col_tokens.find_one({"token": token})
    if not doc:
        return None
    if doc["expires_at"] < time.time():
        return None
    return doc

async def clean_expired_tokens():
    await col_tokens.delete_many({"expires_at": {"$lt": time.time()}})


# ── PENDING ──────────────────────────────────────────
async def add_pending(channel_id: int, user_id: int, first_name: str, username: str):
    if not await col_pending.find_one({"channel_id": channel_id, "user_id": user_id}):
        await col_pending.insert_one({
            "channel_id": channel_id,
            "user_id":    user_id,
            "first_name": first_name,
            "username":   username,
            "req_time":   time.time(),
        })

async def remove_pending(channel_id: int, user_id: int):
    await col_pending.delete_one({"channel_id": channel_id, "user_id": user_id})

async def get_pending_by_channel(channel_id: int) -> list:
    return [d async for d in col_pending.find({"channel_id": channel_id})]

async def count_pending(channel_id: int) -> int:
    return await col_pending.count_documents({"channel_id": channel_id})


# ── USERS ────────────────────────────────────────────
async def add_user(user_id: int):
    if not await col_users.find_one({"user_id": user_id}):
        await col_users.insert_one({"user_id": user_id})

async def get_all_users() -> list:
    return [d["user_id"] async for d in col_users.find({})]

async def count_users() -> int:
    return await col_users.count_documents({})

async def remove_user(user_id: int):
    await col_users.delete_one({"user_id": user_id})
          
