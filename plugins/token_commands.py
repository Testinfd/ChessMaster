import logging
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from info import ADMINS, TOKEN_VERIFICATION_ENABLED
from database.token_db import (
    generate_token, verify_user_token, get_token_info, 
    is_user_verified, get_all_tokens, delete_token, disable_token
)
from utils import check_token_required

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("token") & filters.private)
async def token_command(client, message):
    """Handle token verification or show token status."""
    user_id = message.from_user.id
    
    # Check if token verification is enabled
    if not TOKEN_VERIFICATION_ENABLED:
        return await message.reply_text("Token verification is currently disabled.")
    
    # Check if user is already verified
    if await is_user_verified(user_id) and user_id not in ADMINS:
        return await message.reply_text("✅ You are already verified. No token needed.")
    
    # If command has arguments and user is not an admin, try to verify token
    if len(message.command) > 1 and user_id not in ADMINS:
        token = message.command[1].upper()
        success, msg = await verify_user_token(token, user_id)
        
        if success:
            return await message.reply_text(f"✅ {msg}\nYou can now use all features of the bot.")
        else:
            return await message.reply_text(f"❌ {msg}")
    
    # For admins or users without token, show help
    if user_id in ADMINS:
        await message.reply_text(
            "**🔑 Token Management Commands:**\n\n"
            "/token - Show this help message\n"
            "/token <code> - Verify a token (for users)\n"
            "/gentoken - Generate a new token\n"
            "/gentoken <max_uses> - Generate token with max uses\n"
            "/gentoken <max_uses> <days> - Generate token with expiry\n"
            "/mytokens - List tokens you've created\n"
            "/tokeninfo <code> - Get token information\n"
            "/deltoken <code> - Delete a token\n"
            "/disabletoken <code> - Disable a token\n\n"
            "Token verification is currently **enabled**."
        )
    else:
        await message.reply_text(
            "**🔑 Token Verification**\n\n"
            "To use this bot, you need a valid access token.\n"
            "Please enter your token with the command:\n"
            "/token YOUR_TOKEN_HERE\n\n"
            "If you don't have a token, please contact an administrator."
        )

@Client.on_message(filters.command("gentoken") & filters.user(ADMINS))
async def generate_token_command(client, message):
    """Generate a new verification token."""
    user_id = message.from_user.id
    args = message.command[1:] if len(message.command) > 1 else []
    
    max_uses = 1
    expiry_days = None
    
    # Parse arguments
    if len(args) >= 1:
        try:
            max_uses = int(args[0])
            if max_uses <= 0:
                max_uses = None  # Unlimited uses
        except ValueError:
            return await message.reply_text("Max uses must be a number.")
    
    if len(args) >= 2:
        try:
            expiry_days = int(args[1])
            if expiry_days <= 0:
                return await message.reply_text("Expiry days must be a positive number.")
        except ValueError:
            return await message.reply_text("Expiry days must be a number.")
    
    # Generate the token
    success, token = await generate_token(user_id, max_uses, expiry_days)
    
    if success:
        expiry_info = f"\nExpires in: {expiry_days} days" if expiry_days else ""
        max_uses_info = "Unlimited uses" if max_uses is None else f"{max_uses} use(s)"
        
        await message.reply_text(
            "**🔑 New Token Generated**\n\n"
            f"Token: `{token}`\n"
            f"Max Uses: {max_uses_info}{expiry_info}\n\n"
            "Share this token with users who need access to the bot.",
            quote=True
        )
    else:
        await message.reply_text("Failed to generate token. Please try again.")

@Client.on_message(filters.command("mytokens") & filters.user(ADMINS))
async def list_tokens_command(client, message):
    """List tokens created by the admin."""
    user_id = message.from_user.id
    
    # Get tokens created by this admin
    tokens = await get_all_tokens(admin_id=user_id)
    
    if not tokens:
        return await message.reply_text("You haven't created any tokens yet.")
    
    text = "**🔑 Your Tokens:**\n\n"
    
    for i, token_doc in enumerate(tokens, 1):
        token = token_doc["token"]
        created_on = token_doc["created_on"].strftime("%Y-%m-%d %H:%M")
        uses = f"{token_doc.get('uses', 0)}/{token_doc.get('max_uses', 'Unlimited')}"
        status = "✅ Active" if token_doc.get("is_active", False) else "❌ Inactive"
        
        expiry = ""
        if token_doc.get("expiry"):
            if datetime.now() > token_doc["expiry"]:
                expiry = "Expired"
            else:
                days_left = (token_doc["expiry"] - datetime.now()).days
                expiry = f"Expires in {days_left} days"
        
        text += f"{i}. `{token}` - {uses} - {status}\n   Created: {created_on} {expiry}\n\n"
        
        # Split message if it gets too long
        if i % 10 == 0 and i < len(tokens):
            await message.reply_text(text)
            text = "**🔑 Your Tokens (continued):**\n\n"
    
    if text:
        await message.reply_text(text)

@Client.on_message(filters.command("tokeninfo") & filters.user(ADMINS))
async def token_info_command(client, message):
    """Get detailed information about a token."""
    if len(message.command) < 2:
        return await message.reply_text("Please provide a token code. Usage: /tokeninfo TOKEN")
    
    token = message.command[1].upper()
    token_doc = await get_token_info(token)
    
    if not token_doc:
        return await message.reply_text("Token not found.")
    
    # Format token information
    created_by = token_doc.get("created_by", "Unknown")
    created_on = token_doc["created_on"].strftime("%Y-%m-%d %H:%M")
    max_uses = token_doc.get("max_uses", "Unlimited")
    uses = token_doc.get("uses", 0)
    status = "Active" if token_doc.get("is_active", False) else "Inactive"
    
    expiry = "No expiry"
    if token_doc.get("expiry"):
        if datetime.now() > token_doc["expiry"]:
            expiry = f"Expired on {token_doc['expiry'].strftime('%Y-%m-%d')}"
        else:
            days_left = (token_doc["expiry"] - datetime.now()).days
            expiry = f"Expires in {days_left} days ({token_doc['expiry'].strftime('%Y-%m-%d')})"
    
    users = token_doc.get("users", [])
    users_count = len(users)
    
    text = (
        "**🔑 Token Information**\n\n"
        f"Token: `{token}`\n"
        f"Status: {status}\n"
        f"Created By: {created_by}\n"
        f"Created On: {created_on}\n"
        f"Uses: {uses}/{max_uses}\n"
        f"Expiry: {expiry}\n"
        f"Users: {users_count}\n"
    )
    
    # Add action buttons
    buttons = [
        [
            InlineKeyboardButton("Disable Token", callback_data=f"token_disable_{token}"),
            InlineKeyboardButton("Delete Token", callback_data=f"token_delete_{token}")
        ]
    ]
    
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.command("deltoken") & filters.user(ADMINS))
async def delete_token_command(client, message):
    """Delete a token."""
    if len(message.command) < 2:
        return await message.reply_text("Please provide a token code. Usage: /deltoken TOKEN")
    
    token = message.command[1].upper()
    success = await delete_token(token)
    
    if success:
        await message.reply_text(f"Token `{token}` has been deleted.")
    else:
        await message.reply_text(f"Failed to delete token. Token `{token}` not found.")

@Client.on_message(filters.command("disabletoken") & filters.user(ADMINS))
async def disable_token_command(client, message):
    """Disable a token without deleting it."""
    if len(message.command) < 2:
        return await message.reply_text("Please provide a token code. Usage: /disabletoken TOKEN")
    
    token = message.command[1].upper()
    success = await disable_token(token)
    
    if success:
        await message.reply_text(f"Token `{token}` has been disabled.")
    else:
        await message.reply_text(f"Failed to disable token. Token `{token}` not found or already disabled.")

@Client.on_callback_query(filters.regex(r"^token_"))
async def token_callback(client, callback_query):
    """Handle token-related callbacks."""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if user_id not in ADMINS:
        return await callback_query.answer("You don't have permission to perform this action.", show_alert=True)
    
    action, token = data.split("_", 2)[1:]
    
    if action == "disable":
        success = await disable_token(token)
        if success:
            await callback_query.answer(f"Token {token} has been disabled.", show_alert=True)
            # Update the message
            token_doc = await get_token_info(token)
            if token_doc:
                text = callback_query.message.text.replace("Status: Active", "Status: Inactive")
                await callback_query.message.edit_text(text, reply_markup=callback_query.message.reply_markup)
        else:
            await callback_query.answer("Failed to disable token.", show_alert=True)
    
    elif action == "delete":
        success = await delete_token(token)
        if success:
            await callback_query.answer(f"Token {token} has been deleted.", show_alert=True)
            await callback_query.message.edit_text(f"Token `{token}` has been deleted.")
        else:
            await callback_query.answer("Failed to delete token.", show_alert=True)

@Client.on_message(filters.command(["toggleverification"]) & filters.user(ADMINS))
async def toggle_verification(client, message):
    """Toggle token verification requirement."""
    # This requires modifying the env variable or a config file
    # Here we'll just show a message since we can't easily change env vars
    await message.reply_text(
        "To toggle token verification, you need to change the TOKEN_VERIFICATION_ENABLED setting in your environment variables or config file.\n\n"
        f"Token verification is currently {'enabled' if TOKEN_VERIFICATION_ENABLED else 'disabled'}."
    )

# Add token verification middleware to commands that require it
@Client.on_message(filters.private & ~filters.command(["start", "token", "help"]))
async def check_verification(client, message):
    """Check if the user is verified before allowing other commands."""
    if not TOKEN_VERIFICATION_ENABLED:
        return
        
    user_id = message.from_user.id
    
    # Admins bypass verification
    if user_id in ADMINS:
        return
    
    # Check if user is verified
    if not await is_user_verified(user_id):
        await message.reply_text(
            "⚠️ You need to verify your access token first.\n\n"
            "Please use the command:\n"
            "/token YOUR_TOKEN_HERE\n\n"
            "If you don't have a token, please contact an administrator."
        )
        # Stop further processing of this message
        return True  # Indicate that the message has been handled 