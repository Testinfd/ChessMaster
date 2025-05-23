import datetime
from pymongo.errors import DuplicateKeyError
from info import DATABASE_URI, DATABASE_NAME
from .db_helpers import get_mongo_client

client = get_mongo_client(DATABASE_URI)
db = client[DATABASE_NAME]
users_collection = db.users
chats_collection = db.chats

class Database:
    def __init__(self):
        self.user_count = users_collection.count_documents({})
        self.chat_count = chats_collection.count_documents({})

    async def add_user(self, user_id, username=None):
        """Add a new user or update user info."""
        try:
            user = {
                "_id": user_id,
                "username": username,
                "join_date": datetime.datetime.now()
            }
            
            users_collection.update_one(
                {"_id": user_id},
                {"$set": user},
                upsert=True
            )
            if users_collection.count_documents({"_id": user_id}) == 1:
                self.user_count += 1
            
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False

    async def get_user(self, user_id):
        """Get a user from the database."""
        try:
            return users_collection.find_one({"_id": user_id})
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    async def remove_user(self, user_id):
        """Remove a user from the database."""
        try:
            users_collection.delete_one({"_id": user_id})
            self.user_count -= 1
            return True
        except Exception as e:
            print(f"Error removing user: {e}")
            return False

    async def add_chat(self, chat_id, title=None):
        """Add a new chat or update chat info."""
        try:
            chat = {
                "_id": chat_id,
                "title": title,
                "join_date": datetime.datetime.now()
            }
            
            chats_collection.update_one(
                {"_id": chat_id},
                {"$set": chat},
                upsert=True
            )
            if chats_collection.count_documents({"_id": chat_id}) == 1:
                self.chat_count += 1
            
            return True
        except Exception as e:
            print(f"Error adding chat: {e}")
            return False

    async def remove_chat(self, chat_id):
        """Remove a chat from the database."""
        try:
            chats_collection.delete_one({"_id": chat_id})
            self.chat_count -= 1
            return True
        except Exception as e:
            print(f"Error removing chat: {e}")
            return False

    async def get_all_users(self):
        """Retrieve all user records from the database."""
        return users_collection.find({})

    async def get_all_chats(self):
        """Retrieve all chat records from the database."""
        return chats_collection.find({})

    async def get_user_count(self):
        """Get the number of users in the database."""
        return self.user_count

    async def get_chat_count(self):
        """Get the number of chats in the database."""
        return self.chat_count

    async def get_db_size(self):
        """Get the total size of the database."""
        return db.command("dbstats")["dataSize"]

    async def get_bot_stats(self):
        """Get overall bot statistics."""
        return {
            "users_count": self.user_count,
            "chats_count": self.chat_count,
            "db_size": await self.get_db_size()
        }

    async def get_banned(self):
        """Get banned users and chats."""
        banned_users = list(users_collection.find({"ban_status.is_banned": True}))
        banned_chats = list(chats_collection.find({"ban_status.is_banned": True}))
        return banned_users, banned_chats

    async def ban_user(self, user_id, ban_reason="No reason"):
        """Ban a user."""
        ban_status = {"is_banned": True, "ban_reason": ban_reason}
        users_collection.update_one({"_id": user_id}, {"$set": {"ban_status": ban_status}})

    async def unban_user(self, user_id):
        """Unban a user."""
        ban_status = {"is_banned": False, "ban_reason": ""}
        users_collection.update_one({"_id": user_id}, {"$set": {"ban_status": ban_status}})

    async def ban_chat(self, chat_id, ban_reason="No reason"):
        """Ban a chat."""
        ban_status = {"is_banned": True, "ban_reason": ban_reason}
        chats_collection.update_one({"_id": chat_id}, {"$set": {"ban_status": ban_status}})

    async def unban_chat(self, chat_id):
        """Unban a chat."""
        ban_status = {"is_banned": False, "ban_reason": ""}
        chats_collection.update_one({"_id": chat_id}, {"$set": {"ban_status": ban_status}})
        
    async def is_user_exist(self, user_id):
        """Check if a user exists in the database."""
        return users_collection.count_documents({"_id": user_id}) > 0
        
    async def set_premium_status(self, user_id, status=True, expiry_date=None):
        """Set a user's premium status."""
        if expiry_date is None:
            # Default to 30 days if no expiry date is provided
            expiry_date = datetime.datetime.now() + datetime.timedelta(days=30)
            
        premium_data = {
            "is_premium": status,
            "premium_since": datetime.datetime.now() if status else None,
            "premium_expiry": expiry_date if status else None
        }
        
        result = users_collection.update_one(
            {"_id": user_id},
            {"$set": premium_data}
        )
        
        return result.modified_count > 0
        
    async def update_user_verification(self, user_id, verified=True):
        """Update a user's verification status."""
        verification_data = {
            "is_verified": verified,
            "verified_at": datetime.datetime.now() if verified else None
        }
        
        result = users_collection.update_one(
            {"_id": user_id},
            {"$set": verification_data}
        )
        
        return result.modified_count > 0
        
    async def add_referral(self, user_id, referred_by):
        """Add a referral relationship."""
        from info import REFER_SYSTEM_ENABLED
        
        if not REFER_SYSTEM_ENABLED:
            return False
            
        # Check if the user exists
        if not await self.is_user_exist(user_id):
            await self.add_user(user_id)
            
        # Add referral information
        referral_data = {
            "referred_by": referred_by,
            "referred_at": datetime.datetime.now()
        }
        
        result = users_collection.update_one(
            {"_id": user_id},
            {"$set": referral_data}
        )
        
        # Update referrer's stats
        if result.modified_count > 0:
            users_collection.update_one(
                {"_id": referred_by},
                {"$inc": {"referral_count": 1}}
            )
            
        return result.modified_count > 0
        
    async def get_premium_users(self):
        """Get all premium users."""
        current_time = datetime.datetime.now()
        
        # Find users where is_premium is true and premium_expiry is in the future
        premium_users = list(users_collection.find({
            "is_premium": True,
            "premium_expiry": {"$gt": current_time}
        }))
        
        return premium_users
        
    async def get_expired_premium_users(self):
        """Get users whose premium status has expired."""
        current_time = datetime.datetime.now()
        
        # Find users where is_premium is true but premium_expiry is in the past
        expired_users = list(users_collection.find({
            "is_premium": True,
            "premium_expiry": {"$lt": current_time}
        }))
        
        return expired_users
        
    async def process_expired_premiums(self):
        """Process expired premium subscriptions."""
        expired_users = await self.get_expired_premium_users()
        
        for user in expired_users:
            # Set premium status to false
            await self.set_premium_status(user["_id"], False)
            
        return len(expired_users)

db = Database() 