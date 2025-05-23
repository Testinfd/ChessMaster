import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import ADMINS, TOKEN_VERIFICATION_ENABLED
from database.token_verification import create_token, verify_token, list_user_tokens, deactivate_token

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@Client.on_message(filters.command("verify") & filters.private)
async def verify_command(client, message):
    """Command to verify a token."""
    if not TOKEN_VERIFICATION_ENABLED:
        return await message.reply_text("Token verification is not enabled on this bot.")
        
    # Check if command has a token parameter
    if len(message.command) < 2:
        return await message.reply_text(
            "Please provide a token to verify.\n\n"
            "Usage: /verify YOUR_TOKEN"
        )
        
    token = message.command[1]
    user_id = message.from_user.id
    
    # Verify the token
    valid, error = await verify_token(token)
    
    if valid:
        # Update user as verified in database
        from database.users_chats_db import db
        await db.update_user_verification(user_id, True)
        
        await message.reply_text(
            "✅ Your token has been verified successfully!\n\n"
            "You now have access to all features of the bot."
        )
    else:
        await message.reply_text(
            f"❌ Token verification failed.\n\n"
            f"Error: {error or 'Invalid token'}\n\n"
            f"Please contact the bot administrator for a valid token."
        )

@Client.on_message(filters.command("gentoken") & filters.user(ADMINS))
async def generate_token_command(client, message):
    """Command for admins to generate verification tokens."""
    if not TOKEN_VERIFICATION_ENABLED:
        return await message.reply_text("Token verification is not enabled on this bot.")
        
    usage_limit = 1
    days_valid = 30
    
    # Check for parameters
    if len(message.command) > 1:
        try:
            usage_limit = int(message.command[1])
        except ValueError:
            pass
            
    if len(message.command) > 2:
        try:
            days_valid = int(message.command[2])
        except ValueError:
            pass
            
    # Generate the token
    token, error = await create_token(message.from_user.id, days_valid, usage_limit)
    
    if token:
        await message.reply_text(
            f"✅ New token generated successfully!\n\n"
            f"Token: `{token}`\n"
            f"Usage Limit: {usage_limit}\n"
            f"Valid for: {days_valid} days\n\n"
            f"Users can verify with: /verify {token}",
            quote=True
        )
    else:
        await message.reply_text(
            f"❌ Failed to generate token.\n\n"
            f"Error: {error or 'Unknown error'}",
            quote=True
        )

@Client.on_message(filters.command("mytokens") & filters.user(ADMINS))
async def my_tokens_command(client, message):
    """Command for admins to list their generated tokens."""
    if not TOKEN_VERIFICATION_ENABLED:
        return await message.reply_text("Token verification is not enabled on this bot.")
        
    user_id = message.from_user.id
    tokens = await list_user_tokens(user_id)
    
    if not tokens:
        return await message.reply_text("You haven't created any tokens yet.")
        
    response = "🔑 **Your Generated Tokens**\n\n"
    
    for i, token in enumerate(tokens, 1):
        token_str = token["token"]
        created_at = token["created_at"].strftime("%Y-%m-%d")
        expires_at = token["expires_at"].strftime("%Y-%m-%d")
        usage = f"{token.get('usage_count', 0)}/{token.get('usage_limit', 1)}"
        status = "✅ Active" if token.get("active", False) else "❌ Inactive"
        
        response += f"{i}. `{token_str}`\n"
        response += f"   Created: {created_at} | Expires: {expires_at}\n"
        response += f"   Usage: {usage} | Status: {status}\n\n"
        
    await message.reply_text(response, quote=True)

@Client.on_message(filters.command("revoketoken") & filters.user(ADMINS))
async def revoke_token_command(client, message):
    """Command for admins to revoke a token."""
    if not TOKEN_VERIFICATION_ENABLED:
        return await message.reply_text("Token verification is not enabled on this bot.")
        
    if len(message.command) < 2:
        return await message.reply_text(
            "Please provide a token to revoke.\n\n"
            "Usage: /revoketoken TOKEN"
        )
        
    token = message.command[1]
    success = await deactivate_token(token)
    
    if success:
        await message.reply_text(
            "✅ Token has been revoked successfully.\n\n"
            "This token can no longer be used for verification.",
            quote=True
        )
    else:
        await message.reply_text(
            "❌ Failed to revoke token.\n\n"
            "Please check if the token exists and try again.",
            quote=True
        ) 