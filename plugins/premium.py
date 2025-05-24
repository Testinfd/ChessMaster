import logging
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from info import ADMINS, PREMIUM_ENABLED
from database.users_chats_db import db
from utils import temp, get_readable_time
from Script import script

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("premium") & filters.private)
async def premium_command(client, message):
    """Show premium status or information about premium plans."""
    user_id = message.from_user.id
    
    # Check if premium feature is enabled
    if not PREMIUM_ENABLED:
        return await message.reply_text("Premium features are currently disabled.")
    
    # Get user details
    user = await db.get_user(user_id)
    is_premium = user and user.get("is_premium", False)
    
    # If user is premium, show details
    if is_premium:
        expiry = user.get("premium_expiry")
        if expiry:
            now = datetime.now()
            if expiry > now:
                time_left = expiry - now
                days = time_left.days
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                await message.reply_text(
                    "**✨ You have an active Premium subscription!**\n\n"
                    f"Your premium status will expire in:\n"
                    f"**{days}** days, **{hours}** hours, and **{minutes}** minutes.\n\n"
                    "Benefits of Premium:\n"
                    "• Priority access to all courses\n"
                    "• Faster downloads\n"
                    "• No download limitations\n"
                    "• Advanced search options\n"
                    "• Premium support\n\n"
                    "Thank you for supporting us!"
                )
            else:
                # Premium has expired
                await message.reply_text(
                    "**❌ Your Premium subscription has expired.**\n\n"
                    "Would you like to renew it?\n\n"
                    "Contact the administrator to renew your premium subscription."
                )
        else:
            # No expiry date (unlimited premium)
            await message.reply_text(
                "**✨ You have an unlimited Premium subscription!**\n\n"
                "Benefits of Premium:\n"
                "• Priority access to all courses\n"
                "• Faster downloads\n"
                "• No download limitations\n"
                "• Advanced search options\n"
                "• Premium support\n\n"
                "Thank you for supporting us!"
            )
    else:
        # User is not premium, show available plans
        buttons = [
            [InlineKeyboardButton("Contact Admin for Premium", url=f"https://t.me/{(await client.get_me()).username}?start=premium")]
        ]
        
        await message.reply_text(
            "**💎 Premium Features**\n\n"
            "Upgrade to Premium to unlock these benefits:\n\n"
            "• Priority access to all courses\n"
            "• Faster downloads\n"
            "• No download limitations\n"
            "• Advanced search options\n"
            "• Premium support\n\n"
            "Contact the administrator to purchase a premium subscription.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

@Client.on_message(filters.command("setpremium") & filters.user(ADMINS))
async def set_premium_command(client, message):
    """Command for admins to set a user's premium status."""
    if len(message.command) < 2:
        return await message.reply_text(
            "Please provide a user ID or username.\n\n"
            "Usage: `/setpremium user_id days`\n"
            "Example: `/setpremium 123456789 30`"
        )
    
    try:
        # Parse arguments
        user_arg = message.command[1]
        
        # Try to convert to integer for user ID
        try:
            user_id = int(user_arg)
        except ValueError:
            # If not an integer, assume it's a username
            if user_arg.startswith("@"):
                user_arg = user_arg[1:]
            # Try to get user from database by username
            users = await db.get_all_users()
            user_found = False
            async for user in users:
                if user.get("username") == user_arg:
                    user_id = user["_id"]
                    user_found = True
                    break
            if not user_found:
                return await message.reply_text(f"User with username @{user_arg} not found in database.")
        
        # Get duration in days
        days = 30  # Default
        if len(message.command) >= 3:
            try:
                days = int(message.command[2])
                if days <= 0:
                    return await message.reply_text("Duration must be a positive number of days.")
            except ValueError:
                return await message.reply_text("Duration must be a number.")
        
        # Calculate expiry date
        expiry_date = datetime.now() + timedelta(days=days)
        
        # Set premium status
        success = await db.set_premium_status(user_id, True, expiry_date)
        
        if success:
            # Add to cache
            if user_id not in temp.PREMIUM_USERS:
                temp.PREMIUM_USERS.append(user_id)
                
            await message.reply_text(
                f"✅ Successfully set premium status for user {user_id}.\n\n"
                f"Premium will expire in {days} days ({expiry_date.strftime('%Y-%m-%d %H:%M:%S')})."
            )
        else:
            await message.reply_text(f"❌ Failed to set premium status for user {user_id}.")
    
    except Exception as e:
        logger.error(f"Error setting premium status: {e}")
        await message.reply_text(f"❌ An error occurred: {str(e)}")

@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def remove_premium_command(client, message):
    """Command for admins to remove a user's premium status."""
    if len(message.command) < 2:
        return await message.reply_text(
            "Please provide a user ID or username.\n\n"
            "Usage: `/removepremium user_id`\n"
            "Example: `/removepremium 123456789`"
        )
    
    try:
        # Parse arguments
        user_arg = message.command[1]
        
        # Try to convert to integer for user ID
        try:
            user_id = int(user_arg)
        except ValueError:
            # If not an integer, assume it's a username
            if user_arg.startswith("@"):
                user_arg = user_arg[1:]
            # Try to get user from database by username
            users = await db.get_all_users()
            user_found = False
            async for user in users:
                if user.get("username") == user_arg:
                    user_id = user["_id"]
                    user_found = True
                    break
            if not user_found:
                return await message.reply_text(f"User with username @{user_arg} not found in database.")
        
        # Remove premium status
        success = await db.set_premium_status(user_id, False)
        
        if success:
            # Remove from cache
            if user_id in temp.PREMIUM_USERS:
                temp.PREMIUM_USERS.remove(user_id)
                
            await message.reply_text(f"✅ Successfully removed premium status for user {user_id}.")
        else:
            await message.reply_text(f"❌ Failed to remove premium status for user {user_id}.")
    
    except Exception as e:
        logger.error(f"Error removing premium status: {e}")
        await message.reply_text(f"❌ An error occurred: {str(e)}")

@Client.on_message(filters.command("premiumusers") & filters.user(ADMINS))
async def list_premium_users_command(client, message):
    """Command for admins to list all premium users."""
    try:
        premium_users = await db.get_premium_users()
        
        if not premium_users:
            return await message.reply_text("No premium users found.")
        
        text = "**💎 Premium Users:**\n\n"
        
        for i, user in enumerate(premium_users, 1):
            user_id = user["_id"]
            username = user.get("username", "No username")
            expiry = user.get("premium_expiry")
            
            if expiry:
                days_left = (expiry - datetime.now()).days
                text += f"{i}. ID: `{user_id}` | Username: @{username}\n   Expires in: {days_left} days ({expiry.strftime('%Y-%m-%d')})\n\n"
            else:
                text += f"{i}. ID: `{user_id}` | Username: @{username}\n   Expires: Never (Unlimited)\n\n"
            
            # Split message if it gets too long
            if i % 10 == 0 and i < len(premium_users):
                await message.reply_text(text)
                text = "**💎 Premium Users (continued):**\n\n"
        
        if text:
            await message.reply_text(text)
            
    except Exception as e:
        logger.error(f"Error listing premium users: {e}")
        await message.reply_text(f"❌ An error occurred: {str(e)}")

@Client.on_message(filters.command("checkpremium") & filters.user(ADMINS))
async def check_premium_command(client, message):
    """Command for admins to check a user's premium status."""
    if len(message.command) < 2:
        return await message.reply_text(
            "Please provide a user ID or username.\n\n"
            "Usage: `/checkpremium user_id`\n"
            "Example: `/checkpremium 123456789`"
        )
    
    try:
        # Parse arguments
        user_arg = message.command[1]
        
        # Try to convert to integer for user ID
        try:
            user_id = int(user_arg)
        except ValueError:
            # If not an integer, assume it's a username
            if user_arg.startswith("@"):
                user_arg = user_arg[1:]
            # Try to get user from database by username
            users = await db.get_all_users()
            user_found = False
            async for user in users:
                if user.get("username") == user_arg:
                    user_id = user["_id"]
                    user_found = True
                    break
            if not user_found:
                return await message.reply_text(f"User with username @{user_arg} not found in database.")
        
        # Get user details
        user = await db.get_user(user_id)
        
        if not user:
            return await message.reply_text(f"User with ID {user_id} not found in database.")
        
        is_premium = user.get("is_premium", False)
        
        if is_premium:
            expiry = user.get("premium_expiry")
            
            if expiry:
                now = datetime.now()
                if expiry > now:
                    time_left = expiry - now
                    days = time_left.days
                    hours, remainder = divmod(time_left.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    await message.reply_text(
                        f"✅ User {user_id} has premium status.\n\n"
                        f"Expires in: {days} days, {hours} hours, and {minutes} minutes\n"
                        f"Expiry date: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"Premium since: {user.get('premium_since', 'Unknown').strftime('%Y-%m-%d %H:%M:%S') if user.get('premium_since') else 'Unknown'}"
                    )
                else:
                    await message.reply_text(
                        f"❌ User {user_id}'s premium status has expired.\n\n"
                        f"Expired on: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Premium since: {user.get('premium_since', 'Unknown').strftime('%Y-%m-%d %H:%M:%S') if user.get('premium_since') else 'Unknown'}"
                    )
            else:
                await message.reply_text(
                    f"✅ User {user_id} has unlimited premium status.\n\n"
                    f"Premium since: {user.get('premium_since', 'Unknown').strftime('%Y-%m-%d %H:%M:%S') if user.get('premium_since') else 'Unknown'}"
                )
        else:
            await message.reply_text(f"❌ User {user_id} does not have premium status.")
        
    except Exception as e:
        logger.error(f"Error checking premium status: {e}")
        await message.reply_text(f"❌ An error occurred: {str(e)}")

# Run task to check for expired premium subscriptions
async def check_expired_premiums():
    """Task to periodically check for expired premium subscriptions."""
    while True:
        try:
            count = await db.process_expired_premiums()
            if count > 0:
                logger.info(f"Processed {count} expired premium subscriptions")
        except Exception as e:
            logger.error(f"Error processing expired premiums: {e}")
        
        # Run every hour
        await asyncio.sleep(3600)

# Start the task when the plugin is loaded
asyncio.create_task(check_expired_premiums()) 