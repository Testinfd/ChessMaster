import logging
import random
import string
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from info import DATABASE_URI, DATABASE_NAME, TOKEN_COLLECTION
from .db_helpers import get_mongo_client

logger = logging.getLogger(__name__)

client = get_mongo_client(DATABASE_URI)
db = client[DATABASE_NAME]
tokens_col = db[TOKEN_COLLECTION]

# Make sure we have proper indexes
tokens_col.create_index("token", unique=True)
tokens_col.create_index("user_id")

async def generate_token(admin_id=None, max_uses=1, expiry_days=None):
    """Generate a new verification token."""
    # Generate a random 8-character alphanumeric token
    token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # Set expiry date if specified
    expiry = None
    if expiry_days:
        from datetime import timedelta
        expiry = datetime.now() + timedelta(days=expiry_days)
    
    # Create token document
    token_doc = {
        "token": token,
        "created_by": admin_id,
        "created_on": datetime.now(),
        "max_uses": max_uses,
        "uses": 0,
        "expiry": expiry,
        "is_active": True,
        "users": []
    }
    
    try:
        tokens_col.insert_one(token_doc)
        return True, token
    except DuplicateKeyError:
        # In the rare case of a duplicate token, try again
        return await generate_token(admin_id, max_uses, expiry_days)
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return False, None

async def verify_user_token(token, user_id):
    """Verify a token for a user and mark it as used."""
    # Find the token
    token_doc = tokens_col.find_one({"token": token, "is_active": True})
    
    if not token_doc:
        return False, "Invalid or inactive token."
    
    # Check if token has expired
    if token_doc.get("expiry") and datetime.now() > token_doc["expiry"]:
        tokens_col.update_one({"token": token}, {"$set": {"is_active": False}})
        return False, "Token has expired."
    
    # Check if user has already used this token
    if user_id in token_doc.get("users", []):
        return True, "Token already used by this user."
    
    # Check if max uses reached
    if token_doc.get("max_uses") and token_doc.get("uses", 0) >= token_doc["max_uses"]:
        tokens_col.update_one({"token": token}, {"$set": {"is_active": False}})
        return False, "Token has reached maximum usage limit."
    
    # Update token usage
    result = tokens_col.update_one(
        {"token": token},
        {
            "$inc": {"uses": 1},
            "$push": {"users": user_id},
            "$set": {"is_active": token_doc.get("max_uses") is None or token_doc.get("uses", 0) + 1 < token_doc["max_uses"]}
        }
    )
    
    if result.modified_count > 0:
        # Also mark user as verified in users collection
        from database.users_chats_db import db as users_db
        users_db.update_one(
            {"id": user_id},
            {"$set": {"verified": True, "verified_on": datetime.now()}}
        )
        return True, "Token verified successfully."
    
    return False, "Failed to verify token."

async def get_token_info(token):
    """Get information about a token."""
    token_doc = tokens_col.find_one({"token": token})
    if not token_doc:
        return None
    return token_doc

async def is_user_verified(user_id):
    """Check if a user is verified."""
    from database.users_chats_db import db as users_db
    user = users_db.find_one({"id": user_id})
    return user and user.get("verified", False)

async def get_all_tokens(active_only=False, admin_id=None, limit=100):
    """Get all tokens with optional filtering."""
    query = {}
    if active_only:
        query["is_active"] = True
    if admin_id:
        query["created_by"] = admin_id
    
    tokens = []
    cursor = tokens_col.find(query).sort("created_on", -1).limit(limit)
    
    for token in cursor:
        tokens.append(token)
    
    return tokens

async def delete_token(token):
    """Delete a token."""
    result = tokens_col.delete_one({"token": token})
    return result.deleted_count > 0

async def disable_token(token):
    """Disable a token without deleting it."""
    result = tokens_col.update_one({"token": token}, {"$set": {"is_active": False}})
    return result.modified_count > 0 