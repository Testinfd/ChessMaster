import logging
import random
import asyncio
import datetime
import aiofiles
import aiofiles.os
import re
import uuid
import pytz
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply, Message, CallbackQuery
from pyrogram.errors import ChatAdminRequired, FloodWait, UserIsBlocked, InputUserDeactivated, MessageNotModified

from info import ADMINS, LOG_CHANNEL, SUPPORT_CHAT_ID, CUSTOM_FILE_CAPTION, OWNER_USERNAME, DEVELOPER_LINK, OWNER_LINK, PUBLIC_CHANNEL, TOKEN_VERIFICATION_ENABLED, PREMIUM_ENABLED
from database.users_chats_db import db
from database.courses_db import (
    save_course, 
    save_course_file, 
    get_course_by_id, 
    get_course_files, 
    search_courses, 
    get_all_courses
)
from utils import temp, get_size, extract_user_id, extract_course_id, send_all_files, check_premium_user, check_token_required, get_shortlink
from Script import script

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    logger.info(f"/start command received from user {message.from_user.id} in chat {message.chat.id}")
    if message.chat.type in ['group', 'supergroup']:
        # If command is used in a group
        buttons = [[
            InlineKeyboardButton('🚀 Start a Chat with Me', url=f'https://t.me/{temp.U_NAME}?start=group_start'),
            InlineKeyboardButton('🔍 Search Courses Here', switch_inline_query_current_chat='')
        ],[
            InlineKeyboardButton('💬 Support', url=f'https://t.me/{SUPPORT_CHAT_ID}'),
            InlineKeyboardButton('ℹ️ Help', callback_data='help_group') # Differentiate help for groups if needed
        ]]
        await message.reply_photo(
            photo=random.choice(PICS), # Use a random picture here too for consistency
            caption=script.START_TXT.format(message.from_user.mention if message.from_user else "Hey there"), # Use the main start text
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        return

    # Add user to database if not exists
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        # Add timestamp to log message
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(tz)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention, time_str))

    # Command used in private chat
    if len(message.command) > 1:
        # Process deep link parameters
        param = message.command[1]
        
        if param.startswith('course_'):
            # Handle course download links
            course_id = param.split('_')[1]
            course = await get_course_by_id(course_id)
            
            if not course:
                await message.reply_text(script.COURSE_NOT_FOUND)
                return
            
            # Check token verification
            if TOKEN_VERIFICATION_ENABLED:
                needs_verification = await check_token_required(message.from_user.id)
                if needs_verification and message.from_user.id not in ADMINS:
                    verification_text = (
                        "⚠️ **Token Verification Required** ⚠️\n\n"
                        "To access this course, you need to verify your token first.\n\n"
                        "Please use the command:\n"
                        "/token YOUR_TOKEN_HERE\n\n"
                        "If you don't have a token, please contact an administrator."
                    )
                    verification_buttons = [[
                        InlineKeyboardButton("Contact Admin", url=f"https://t.me/{OWNER_USERNAME}")
                    ]]
                    await message.reply_text(
                        verification_text,
                        reply_markup=InlineKeyboardMarkup(verification_buttons)
                    )
                    return
            
            # Check premium requirements if applicable
            if PREMIUM_ENABLED and course.get('premium_only', False):
                is_premium = await check_premium_user(message.from_user.id)
                if not is_premium and message.from_user.id not in ADMINS:
                    premium_text = (
                        "💎 **Premium Content** 💎\n\n"
                        f"The course '{course['course_name']}' is available exclusively for premium users.\n\n"
                        "Upgrade to premium to access this and other premium courses!\n\n"
                        "Use /premium to learn more about premium benefits."
                    )
                    premium_buttons = [[
                        InlineKeyboardButton("Get Premium", callback_data="premium_info")
                    ]]
                    await message.reply_text(
                        premium_text,
                        reply_markup=InlineKeyboardMarkup(premium_buttons)
                    )
                    return
                
            course_files = await get_course_files(course_id)
            
            if not course_files:
                await message.reply_text("No files found for this course.")
                return
                
            # Send welcome message with course info
            welcome_text = f"<b>Fantastic! You're about to dive into the {course['course_name']} course!</b>\n\nI'll send over all the course materials in just a moment. Get ready to learn! 🚀"
            await message.reply_text(welcome_text)
            
            # Send all course files
            await send_all_files(client, message.chat.id, course_id, course_files)
            
            # Send a message after all files are sent
            complete_text = f"<b>✅ All files for {course['course_name']} have been sent!</b>\n\nI hope you find it valuable. Happy learning!\n\nReady for more? You can always browse other courses or check out our updates channel."
            buttons = [[
                InlineKeyboardButton('🔍 Browse More Courses', switch_inline_query_current_chat=''),
                InlineKeyboardButton('📢 Updates Channel', url=f"https://t.me/{PUBLIC_CHANNEL}")
            ]]
            await message.reply_text(complete_text, reply_markup=InlineKeyboardMarkup(buttons))
            return
        
        elif param == 'premium':
            # Handle premium information
            if PREMIUM_ENABLED:
                await message.reply_text(
                    "💎 **Premium Access** 💎\n\n"
                    "Upgrade to Premium to unlock these exclusive benefits:\n\n"
                    "• Access to premium-only courses\n"
                    "• Priority customer support\n"
                    "• Faster downloads\n"
                    "• No daily download limits\n\n"
                    "Use the /premium command to check your current status or learn more about our premium plans."
                )
                return
    
    # Regular start command
    buttons = [[
        InlineKeyboardButton('➕ Add to Group', url=f'http://t.me/{temp.U_NAME}?startgroup=true'),
        InlineKeyboardButton('🔍 Search', switch_inline_query_current_chat='')
    ]]
    
    # Add premium button if enabled
    if PREMIUM_ENABLED:
        buttons.append([InlineKeyboardButton('💎 Premium', callback_data='premium_info')])
        
    buttons.append([
        InlineKeyboardButton('ℹ️ Help', callback_data='help'),
        InlineKeyboardButton('📜 About', callback_data='about')
    ])
    
    # Choose a random banner image from PICS
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_photo(
        photo=random.choice(PICS),
        caption=script.START_TXT.format(message.from_user.mention),
        reply_markup=reply_markup
    )

@Client.on_message(filters.command("help"))
async def help(client, message):
    buttons = [[
        InlineKeyboardButton('Course Help', callback_data='course_help'),
        InlineKeyboardButton('Search Help', callback_data='search_help')
    ]]
    
    # Add premium help if enabled
    if PREMIUM_ENABLED:
        buttons.append([InlineKeyboardButton('Premium Help', callback_data='premium_help')])
        
    # Add token verification help if enabled
    if TOKEN_VERIFICATION_ENABLED:
        buttons.append([InlineKeyboardButton('Token Help', callback_data='token_help')])
        
    buttons.append([
        InlineKeyboardButton('🔙 Back', callback_data='start'),
        InlineKeyboardButton('🔄 Close', callback_data='close_data')
    ])
    
    await message.reply_text(
        text=script.HELP_TXT.format(message.from_user.mention if message.from_user else "Dear user"),
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

@Client.on_message(filters.command("about"))
async def about(client, message):
    buttons = [[
        InlineKeyboardButton('🔙 Back', callback_data='help'),
        InlineKeyboardButton('🔄 Close', callback_data='close_data')
    ]]
    await message.reply_text(
        text=script.ABOUT_TXT.format(temp.U_NAME, temp.B_NAME, temp.U_NAME),
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(client, message):
    """Show bot statistics including file, user, and chat counts."""
    
    # Get user and chat counts
    user_count = await db.get_user_count()
    chat_count = await db.get_chat_count()
    
    # Get course and file counts
    courses, _, total_courses = await get_all_courses(max_results=1)
    
    # Get premium user count if enabled
    premium_count = 0
    if PREMIUM_ENABLED:
        premium_users = await db.get_premium_users()
        premium_count = len(premium_users)
    
    # Calculate storage stats
    from database.db_helpers import calculate_used_storage
    from database.courses_db import files_col
    
    used_storage = calculate_used_storage(files_col)
    free_storage = "Unlimited"  # MongoDB Atlas handles storage limits differently
    
    # Create stats message
    stats_text = script.STATUS_TXT.format(
        total_courses, 
        user_count, 
        chat_count, 
        get_size(used_storage), 
        free_storage
    )
    
    # Add premium stats if enabled
    if PREMIUM_ENABLED:
        stats_text += f"\n\n<b>Premium Users:</b> {premium_count}"
    
    await message.reply_text(
        stats_text,
        parse_mode='html'
    )

@Client.on_message(filters.command("course") & filters.user(ADMINS))
async def old_course_command_alias(client, message):
    """Alias for /addcourse. Guides admin to use the new link-based system."""
    logger.info(f"User {message.from_user.id} used /course, redirecting to /addcourse info.")
    await message.reply_text(
        "Hi Admin! 👋\n\n" 
        "To add a new course, please use the `/addcourse` command. "
        "This will start the process of adding a course using **message links**.\n\n" 
        "Just type /addcourse and I'll guide you through it!"
    )

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast(client, message):
    """Broadcast a message to all users."""
    if len(message.command) < 2:
        return await message.reply_text("Please provide a message to broadcast.")
        
    # Get broadcast message
    broadcast_msg = message.text.split(None, 1)[1]
    
    # Send confirmation
    confirmation = await message.reply_text(
        text="📢 **Confirm Broadcast** 📢\n\nYou are about to send the following message to ALL users. This action cannot be undone.\n\n`{}`\n\nAre you absolutely sure you want to proceed?".format(broadcast_msg),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Send Now!", callback_data="broadcast_confirm"),
                InlineKeyboardButton("❌ No, Cancel", callback_data="broadcast_cancel")
            ]
        ])
    )
    
    # Store broadcast message for later use
    temp.BROADCAST_MSG = broadcast_msg

@Client.on_callback_query(filters.regex("^broadcast_"))
async def broadcast_callback(client, callback_query):
    """Handle broadcast confirmation callback."""
    action = callback_query.data.split("_")[1]
    
    if action == "cancel":
        await callback_query.message.edit_text("Broadcast cancelled.")
        return
        
    if action == "confirm":
        # Start broadcasting
        broadcast_msg = temp.BROADCAST_MSG
        await callback_query.message.edit_text("Broadcasting message...")
        
        async def send_msg(user_id):
            try:
                await client.send_message(user_id, broadcast_msg)
                return True
            except UserIsBlocked:
                await db.ban_user(user_id, "User blocked the bot")
                return False
            except InputUserDeactivated:
                await db.ban_user(user_id, "User account deleted")
                return False
            except Exception as e:
                logger.error(f"Error in broadcast: {e}")
                return False
        
        # Get all users
        users = await db.get_all_users()
        success = 0
        failed = 0
        
        # Progress updates
        start_time = datetime.datetime.now()
        status_msg = await callback_query.message.edit_text(
            text=f"Broadcasting in progress...\n\nSuccess: {success}\nFailed: {failed}"
        )
        update_interval = 5  # Update status message every 5 seconds
        last_update_time = start_time
        
        async for user in users:
            result = await send_msg(user["_id"])
            if result:
                success += 1
            else:
                failed += 1
                
            # Update status message periodically
            now = datetime.datetime.now()
            if (now - last_update_time).total_seconds() >= update_interval:
                await status_msg.edit_text(
                    text=f"Broadcasting in progress...\n\nSuccess: {success}\nFailed: {failed}"
                )
                last_update_time = now
                
        # Final update
        end_time = datetime.datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        await status_msg.edit_text(
            text=f"✅ Broadcast Completed!\n\nSuccess: {success}\nFailed: {failed}\nTime taken: {time_taken:.2f} seconds"
        )

@Client.on_callback_query()
async def cb_handler(client, query):
    """Handle all callback queries."""
    data = query.data
    
    if data == "help":
        buttons = [[
            InlineKeyboardButton('Course Help', callback_data='course_help'),
            InlineKeyboardButton('Search Help', callback_data='search_help')
        ]]
        
        # Add premium help if enabled
        if PREMIUM_ENABLED:
            buttons.append([InlineKeyboardButton('Premium Help', callback_data='premium_help')])
            
        # Add token verification help if enabled
        if TOKEN_VERIFICATION_ENABLED:
            buttons.append([InlineKeyboardButton('Token Help', callback_data='token_help')])
            
        buttons.append([
            InlineKeyboardButton('🔙 Back', callback_data='start'),
            InlineKeyboardButton('🔄 Close', callback_data='close_data')
        ])
        
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    elif data == "about":
        buttons = [[
            InlineKeyboardButton('🔙 Back', callback_data='help'),
            InlineKeyboardButton('🔄 Close', callback_data='close_data')
        ]]
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.U_NAME, temp.B_NAME, temp.U_NAME),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    elif data == "start":
        buttons = [[
            InlineKeyboardButton('➕ Add to Group', url=f'http://t.me/{temp.U_NAME}?startgroup=true'),
            InlineKeyboardButton('🔍 Search', switch_inline_query_current_chat='')
        ]]
        
        # Add premium button if enabled
        if PREMIUM_ENABLED:
            buttons.append([InlineKeyboardButton('💎 Premium', callback_data='premium_info')])
            
        buttons.append([
            InlineKeyboardButton('ℹ️ Help', callback_data='help'),
            InlineKeyboardButton('📜 About', callback_data='about')
        ])
        
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    elif data == "course_help":
        buttons = [[InlineKeyboardButton('🔙 Back', callback_data='help')]]
        await query.message.edit_text(
            text=script.COURSE_HELP,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    elif data == "search_help":
        buttons = [[InlineKeyboardButton('🔙 Back', callback_data='help')]]
        await query.message.edit_text(
            text=script.SEARCH_HELP,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
    
    elif data == "premium_help":
        buttons = [[InlineKeyboardButton('🔙 Back', callback_data='help')]]
        await query.message.edit_text(
            text=script.PREMIUM_HELP,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    elif data == "token_help":
        buttons = [[InlineKeyboardButton('🔙 Back', callback_data='help')]]
        await query.message.edit_text(
            text=script.TOKEN_HELP,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
    elif data == "premium_info":
        # Show premium information
        if PREMIUM_ENABLED:
            user_id = query.from_user.id
            user = await db.get_user(user_id)
            is_premium = user and user.get("is_premium", False)
            
            if is_premium:
                expiry = user.get("premium_expiry")
                if expiry:
                    now = datetime.datetime.now()
                    if expiry > now:
                        time_left = expiry - now
                        days = time_left.days
                        hours, remainder = divmod(time_left.seconds, 3600)
                        minutes, _ = divmod(remainder, 60)
                        
                        premium_text = (
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
                        premium_text = (
                            "**❌ Your Premium subscription has expired.**\n\n"
                            "Would you like to renew it?\n\n"
                            "Contact the administrator to renew your premium subscription."
                        )
                else:
                    premium_text = (
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
                premium_text = (
                    "**💎 Premium Features**\n\n"
                    "Upgrade to Premium to unlock these benefits:\n\n"
                    "• Priority access to all courses\n"
                    "• Faster downloads\n"
                    "• No download limitations\n"
                    "• Advanced search options\n"
                    "• Premium support\n\n"
                    "Contact the administrator to purchase a premium subscription."
                )
            
            buttons = [[
                InlineKeyboardButton("Contact Admin", url=f"https://t.me/{OWNER_USERNAME}"),
                InlineKeyboardButton("🔙 Back", callback_data="start")
            ]]
            
            await query.message.edit_text(
                premium_text,
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )
        else:
            # Premium is disabled
            await query.answer("Premium features are currently disabled.", show_alert=True)
            
    elif data == "close_data":
        await query.message.delete()
        
    else:
        await query.answer("Feature not implemented yet.", show_alert=True) 