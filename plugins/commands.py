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

from info import ADMINS, LOG_CHANNEL, SUPPORT_CHAT_ID, CUSTOM_FILE_CAPTION, OWNER_USERNAME, DEVELOPER_LINK, OWNER_LINK
from database.users_chats_db import db
from database.courses_db import (
    save_course, 
    save_course_file, 
    get_course_by_id, 
    get_course_files, 
    search_courses, 
    get_all_courses
)
from utils import temp, get_size, extract_user_id, extract_course_id, send_all_files
from Script import script

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
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
                
            # Add the user to database
            if not await db.is_user_exist(message.from_user.id):
                await db.add_user(message.from_user.id, message.from_user.first_name)
                # Add timestamp to log message
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.datetime.now(tz)
                time_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
                await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention, time_str))
            
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
    
    # Regular start command
    buttons = [[
        InlineKeyboardButton('➕ Add to Group', url=f'http://t.me/{temp.U_NAME}?startgroup=true'),
        InlineKeyboardButton('🔍 Search', switch_inline_query_current_chat='')
    ], [
        InlineKeyboardButton('ℹ️ Help', callback_data='help'),
        InlineKeyboardButton('📜 About', callback_data='about')
    ]]
    
    # Choose a random banner image from PICS
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_photo(
        photo=random.choice(PICS),
        caption=script.START_TXT.format(message.from_user.mention),
        reply_markup=reply_markup
    )
    
    # Add user to database if not exists
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        # Add timestamp to log message
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(tz)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention, time_str))

@Client.on_message(filters.command("help"))
async def help(client, message):
    buttons = [[
        InlineKeyboardButton('Course Help', callback_data='course_help'),
        InlineKeyboardButton('Search Help', callback_data='search_help')
    ]]
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
    
    # Calculate storage stats
    from database.db_helpers import calculate_used_storage
    from database.courses_db import files_col
    
    used_storage = calculate_used_storage(files_col)
    free_storage = "Unlimited"  # MongoDB Atlas handles storage limits differently
    
    await message.reply_text(
        script.STATUS_TXT.format(
            total_courses, 
            user_count, 
            chat_count, 
            get_size(used_storage), 
            free_storage
        ),
        parse_mode='html'
    )

@Client.on_message(filters.command("course") & filters.user(ADMINS))
async def course_command(client, message):
    """Command to manually start the course creation process."""
    await message.reply_text(
        script.COURSE_HELP + # Prepend the detailed help text
        "\n\nAlright, let's get started!\n\n<b>What's the name of the chess course you want to add?</b>\n(Please send the full name as your next message)",
        reply_markup=ForceReply(True),
        disable_web_page_preview=True # In case COURSE_HELP has links
    )
    # The actual course creation will be handled by a conversation handler

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
            current_time = datetime.datetime.now()
            if (current_time - last_update_time).total_seconds() >= update_interval:
                await status_msg.edit_text(
                    text=f"Broadcasting in progress...\n\nSuccess: {success}\nFailed: {failed}"
                )
                last_update_time = current_time
                
            # Add small delay to avoid flooding
            await asyncio.sleep(0.1)
            
        # Final status
        end_time = datetime.datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        
        await status_msg.edit_text(
            text=f"Broadcast completed in {time_taken:.2f} seconds.\n\nSuccess: {success}\nFailed: {failed}"
        )

@Client.on_callback_query()
async def cb_handler(client, query):
    """Handle callback queries for various buttons."""
    data = query.data
    user_id = query.from_user.id

    if data == "close_data":
        await query.message.delete()
        return
    
    # Handling help in group, to avoid editing a message that might be old or not targeted at this user    
    if data == "help_group":
        buttons = [[
            InlineKeyboardButton('Course Help', callback_data=f'course_help_u_{user_id}'), # Add user_id to ensure only user can click
            InlineKeyboardButton('Search Help', callback_data=f'search_help_u_{user_id}')
        ]]
        try:
            await query.answer() # Answer callback quickly
            await client.send_message(
                chat_id=user_id, # Send help to user's PM
                text=script.HELP_TXT.format(query.from_user.mention if query.from_user else "Dear user"),
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True
            )
            await query.message.reply_text(f"@{query.from_user.username} I've sent the help message to your private chat.")
        except Exception as e:
            logger.error(f"Error sending help to PM for user {user_id}: {e}")
            await query.answer("Could not send help to your PM. Please start a chat with me and type /help.", show_alert=True)
        return
        
    if data == "help":
        buttons = [[
            InlineKeyboardButton('Course Help', callback_data=f'course_help_u_{user_id}'),
            InlineKeyboardButton('Search Help', callback_data=f'search_help_u_{user_id}')
        ]]
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention if query.from_user else "Dear user"),
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        return
        
    if data == "about":
        # temp.U_NAME and temp.B_NAME are bot's username and first name
        # OWNER_LINK is used for the developer URL
        buttons = [[
            InlineKeyboardButton('🔙 Back to Help', callback_data=f'help_u_{user_id}'),
            InlineKeyboardButton('🔄 Close', callback_data='close_data')
        ]]
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.U_NAME, temp.B_NAME, OWNER_LINK), # Use OWNER_LINK here
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        return
        
    # Add _u_{user_id} to callback data to make buttons user-specific if they lead to further interactions
    # or if the response should only be seen by the original querier.
    if data.startswith("course_help_u_") and str(user_id) == data.split("_")[-1]:
        buttons = [[
            InlineKeyboardButton('🔙 Back to Help', callback_data=f'help_u_{user_id}'),
            InlineKeyboardButton('🔄 Close', callback_data='close_data')
        ]]
        await query.message.edit_text(
            text=script.COURSE_HELP,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        return
        
    if data.startswith("search_help_u_") and str(user_id) == data.split("_")[-1]:
        buttons = [[
            InlineKeyboardButton('🔙 Back to Help', callback_data=f'help_u_{user_id}'),
            InlineKeyboardButton('🔄 Close', callback_data='close_data')
        ]]
        await query.message.edit_text(
            text=script.SEARCH_HELP,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        return
        
    # Handle course download callback
    if data.startswith("course_download_"):
        course_id = data.split("_")[2]
        course = await get_course_by_id(course_id)
        
        if not course:
            await query.answer(script.COURSE_NOT_FOUND, show_alert=True) # Use script text
            return
            
        course_files = await get_course_files(course_id)
        
        if not course_files:
            await query.answer("No files found for this course. It might be empty or under maintenance.", show_alert=True)
            return
            
        # Inform user that files will be sent
        await query.answer("Roger that! Sending the course files your way... ⏳", show_alert=False) # Less intrusive alert
        
        welcome_text = f"<b>Get ready! 🚀 The files for {course['course_name']} are on their way to you now!</b>\n\nMake sure to check your chat for all the materials."
        try:
            await query.edit_message_text(welcome_text) # Edit the original message if possible
        except MessageNotModified:
            pass # If message is the same, no need to edit
        except Exception as e:
            logger.info(f"Couldn't edit message for course download, sending new one: {e}")
            await client.send_message(query.from_user.id, welcome_text)

        # Send all course files
        await send_all_files(client, query.from_user.id, course_id, course_files)
        
        # Send a message after all files are sent
        complete_text = f"<b>✅ All done! All files for {course['course_name']} have been successfully sent.</b>\n\nHope you enjoy the course and pick up some new chess skills!\n\nLooking for more?" # Using the new script text
        buttons = [[
            InlineKeyboardButton('🔍 Browse More Courses', switch_inline_query_current_chat=''),
            InlineKeyboardButton('📢 Updates Channel', url=f"https://t.me/{PUBLIC_CHANNEL}")
        ]]
        await client.send_message(query.from_user.id, complete_text, reply_markup=InlineKeyboardMarkup(buttons))
        return 