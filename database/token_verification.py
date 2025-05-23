import datetime
import uuid
import logging
from info import DATABASE_URI, DATABASE_NAME, TOKEN_COLLECTION, TOKEN_VERIFICATION_ENABLED
from .db_helpers import get_mongo_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = get_mongo_client(DATABASE_URI)
db = client[DATABASE_NAME]
tokens_col = db[TOKEN_COLLECTION]

async def create_token(user_id, days_valid=30, usage_limit=1):
    """Create a new verification token for a user."""
    if not TOKEN_VERIFICATION_ENABLED:
        return None, "Token verification is not enabled"
        
    try:
        token = str(uuid.uuid4())
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=days_valid)
        
        token_doc = {
            "token": token,
            "created_by": user_id,
            "created_at": datetime.datetime.now(),
            "expires_at": expiry_date,
            "usage_limit": usage_limit,
            "usage_count": 0,
            "active": True
        }
        
        tokens_col.insert_one(token_doc)
        return token, None
    except Exception as e:
        logger.error(f"Error creating token: {e}")
        return None, str(e)

async def verify_token(token):
    """Check if a token is valid and update its usage count."""
    if not TOKEN_VERIFICATION_ENABLED:
        return True, None
        
    try:
        token_doc = tokens_col.find_one({"token": token})
        
        if not token_doc:
            return False, "Invalid token"
            
        if not token_doc.get("active", False):
            return False, "Token is deactivated"
            
        current_time = datetime.datetime.now()
        expiry_time = token_doc.get("expires_at")
        
        if current_time > expiry_time:
            return False, "Token has expired"
            
        usage_count = token_doc.get("usage_count", 0)
        usage_limit = token_doc.get("usage_limit", 1)
        
        if usage_count >= usage_limit:
            return False, "Token usage limit reached"
            
        # Update usage count
        tokens_col.update_one(
            {"token": token},
            {"$inc": {"usage_count": 1}}
        )
        
        return True, None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return False, str(e)

async def get_token_info(token):
    """Get information about a token."""
    if not TOKEN_VERIFICATION_ENABLED:
        return None
        
    try:
        return tokens_col.find_one({"token": token})
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        return None

async def deactivate_token(token):
    """Deactivate a token."""
    if not TOKEN_VERIFICATION_ENABLED:
        return False
        
    try:
        result = tokens_col.update_one(
            {"token": token},
            {"$set": {"active": False}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error deactivating token: {e}")
        return False

async def list_user_tokens(user_id):
    """List all tokens created by a user."""
    if not TOKEN_VERIFICATION_ENABLED:
        return []
        
    try:
        tokens = []
        cursor = tokens_col.find({"created_by": user_id})
        
        for token in cursor:
            tokens.append(token)
            
        return tokens
    except Exception as e:
        logger.error(f"Error listing user tokens: {e}")
        return [] 