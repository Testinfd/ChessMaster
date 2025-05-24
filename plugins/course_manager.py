import logging
import asyncio
import time
import random
import uuid
import re
from datetime import datetime
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified

from info import ADMINS, CUSTOM_FILE_CAPTION, PUBLIC_CHANNEL
from database.courses_db import save_course, save_course_file, get_course_by_id, update_course, get_course_files
from utils import temp, get_size, get_file_id, clean_text
from Script import script

logger = logging.getLogger(__name__)

# States for course creation conversation
WAITING_COURSE_NAME = 1
WAITING_COURSE_LINKS = 2 # Changed from 3 to 2, as WAITING_COURSE_FILES is removed
WAITING_BANNER = 3       # Changed from 4 to 3
CONFIRM_COURSE = 4       # Changed from 5 to 4

# Store conversation states for users
user_states = {}

@Client.on_message(filters.command(["addcourse", "addcourselinks"]) & filters.private & filters.user(ADMINS))
async def add_course_command(client, message):
    """Start course creation process using message links."""
    await message.reply_text(
        "Okay, let's add a new course! 📚\n\n"
        "**First, what is the name of this course?**\n"
        "Please send the full course name as your next message.",
        reply_markup=ForceReply(True)
    )
    user_states[message.from_user.id] = WAITING_COURSE_NAME
    # Initialize course data, ensuring it's clean for a new course
    temp.CURRENT_COURSES[message.from_user.id] = {
        "course_name": None, # Will be set in the next step
        "files": [],
        "links": [],
        "banner": None,
        "using_links": True # Default to new method
    }

@Client.on_message(filters.private & filters.reply & filters.user(ADMINS))
async def handle_course_replies(client, message):
    """Handle replies during course creation conversation."""
    user_id = message.from_user.id
    
    if user_id not in user_states or user_id not in temp.CURRENT_COURSES:
        # If user is not in a state or no course data, ignore or guide them
        # For now, just returning to avoid errors if user replies randomly
        return
        
    state = user_states[user_id]
    
    if state == WAITING_COURSE_NAME:
        course_name = clean_text(message.text)
        if not course_name:
            return await message.reply_text("Hmm, that doesn't look like a valid course name. Please try again.")
            
        temp.CURRENT_COURSES[user_id]["course_name"] = course_name
        
        await message.reply_text(
            f"Great! The course will be named: **'{course_name}'**.\n\n"
            "Now, please send me the **Telegram message links** for all the files in this course. "
            "You can send one link per message, or multiple links in a single message (each on a new line).\n\n"
            "**Format:** `https://t.me/c/channel_id/message_id` or `https://t.me/channel_username/message_id`\n\n"
            "Type /done when you've sent all the links.",
            disable_web_page_preview=True
        )
        user_states[user_id] = WAITING_COURSE_LINKS
            
    elif state == WAITING_COURSE_LINKS:
        if not message.text:
            return await message.reply_text("That doesn't look like a message link. Please send valid links or type /done.")

        # Regex to find all Telegram message links in the message text
        link_pattern = r"https?://t\.me/(?:c/)?(\S+)/(\d+)" # Made channel part more general
        found_links = re.findall(link_pattern, message.text)
        
        if not found_links:
            return await message.reply_text(
                "I couldn't find any valid Telegram message links in your message. Please use the correct format:\n"
                "`https://t.me/c/channel_id/message_id` or `https://t.me/channel_username/message_id`\n\n"
                "Or type /done if you've finished adding links.",
                disable_web_page_preview=True
            )
            
        added_count = 0
        for channel_identifier, message_id_str in found_links:
            try:
                message_id = int(message_id_str)
                # If channel_identifier is numeric (private channel ID) and doesn't start with -100, add it
                # Otherwise, it's a public channel username or already formatted private ID
                if channel_identifier.isdigit() and not channel_identifier.startswith("-100"):
                    actual_channel_id = f"-100{channel_identifier}"
                else:
                    actual_channel_id = channel_identifier
                    
                if "links" not in temp.CURRENT_COURSES[user_id]: # Should have been initialized
                    temp.CURRENT_COURSES[user_id]["links"] = []
                    
                temp.CURRENT_COURSES[user_id]["links"].append({
                    "channel_id": actual_channel_id,
                    "message_id": message_id
                })
                added_count += 1
            except ValueError:
                await message.reply_text(f"Warning: Skipping invalid message ID format in link: .../{channel_identifier}/{message_id_str}")
                continue
        
        if added_count > 0:
            total_links = len(temp.CURRENT_COURSES[user_id].get("links", []))
            await message.reply_text(
                f"Added {added_count} new message link(s). ✅\n"
                f"Total links for this course so far: **{total_links}**\n\n"
                "Keep sending links or type /done when finished."
            )
        # If no valid links were added from this message, but some were found by regex, user might be confused.
        # The earlier message "I couldn't find any valid Telegram message links..." handles the case where regex finds nothing.
        
    elif state == WAITING_BANNER:
        if message.photo:
            photo_id = message.photo.file_id
            temp.CURRENT_COURSES[user_id]["banner"] = photo_id
            await message.reply_text("Banner image received! 👍")
            await confirm_course(client, message, user_id) # Proceed to confirmation
            user_states[user_id] = CONFIRM_COURSE
        else:
            await message.reply_text("That's not a photo. Please send a photo for the banner, or type /skip to use a default.")
            
    elif state == CONFIRM_COURSE:
        response = message.text.lower()
        
        if response in ["yes", "y", "confirm", "3", "confirm and publish"]:
            await publish_course(client, message, user_id)
            if user_id in temp.CURRENT_COURSES: del temp.CURRENT_COURSES[user_id]
            if user_id in user_states: del user_states[user_id]
        elif response in ["no", "n", "cancel", "4"]:
            await message.reply_text("Course creation cancelled. ❌")
            if user_id in temp.CURRENT_COURSES: del temp.CURRENT_COURSES[user_id]
            if user_id in user_states: del user_states[user_id]
        elif response in ["1", "add banner", "banner"]:
            await message.reply_text(
                "Okay, please send a photo to use as the course banner.",
                reply_markup=ForceReply(True)
            )
            user_states[user_id] = WAITING_BANNER
        elif response in ["2", "modify name", "edit name"]:
            await message.reply_text(
                "What should the new course name be?",
                reply_markup=ForceReply(True)
            )
            # Revert to WAITING_COURSE_NAME but keep current data
            # The 'using_links': True flag will be preserved.
            temp.CURRENT_COURSES[user_id]['course_name'] = None # Clear to allow re-entry
            user_states[user_id] = WAITING_COURSE_NAME
        else:
            await message.reply_text(
                "Please choose one of the options from the confirmation message (e.g., type 'yes' or '1')."
            )

@Client.on_message(filters.command("done") & filters.private & filters.user(ADMINS))
async def done_collecting_links(client, message):
    user_id = message.from_user.id
    
    if user_id not in user_states or user_states[user_id] != WAITING_COURSE_LINKS:
        return await message.reply_text("It seems you're not currently adding course links. Use /addcourse to start.")
        
    if user_id not in temp.CURRENT_COURSES or not temp.CURRENT_COURSES[user_id].get("links"):
        return await message.reply_text("You haven't added any message links yet. Please send some links or use /cancel if you wish to stop.")
        
    course_data = temp.CURRENT_COURSES[user_id]
    
    processing_msg = await message.reply_text("Processing message links... This might take a moment. ⏳")
    
    fetched_files_info = []
    success_count = 0
    failed_count = 0
    
    for link_data in course_data["links"]:
        try:
            # Ensure channel_id is correctly formatted (integer for private, string for public)
            chat_id_to_fetch = link_data["channel_id"]
            if isinstance(chat_id_to_fetch, str) and chat_id_to_fetch.startswith("-100") and chat_id_to_fetch[4:].isdigit():
                 chat_id_to_fetch = int(chat_id_to_fetch)
            elif isinstance(chat_id_to_fetch, str) and chat_id_to_fetch.isdigit(): # A public channel ID as string
                 chat_id_to_fetch = int(chat_id_to_fetch)


            fetched_message = await client.get_messages(
                chat_id=chat_id_to_fetch, 
                message_ids=link_data["message_id"]
            )
            
            if fetched_message and fetched_message.media:
                file_obj, file_id = get_file_id(fetched_message)
                if file_id:
                    fetched_files_info.append({
                        "file_id": file_id,
                        "file_name": getattr(file_obj, "file_name", f"File from {link_data['message_id']}"),
                        "file_size": getattr(file_obj, "file_size", 0),
                        "caption": fetched_message.caption, # Or use CUSTOM_FILE_CAPTION later
                        "message_id": fetched_message.id # Original message_id from source channel
                    })
                    success_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Could not get file_id from fetched message: chat={chat_id_to_fetch}, msg_id={link_data['message_id']}")
            else:
                failed_count += 1
                logger.warning(f"Fetched message has no media or message not found: chat={chat_id_to_fetch}, msg_id={link_data['message_id']}")
        except FloodWait as e:
            logger.warning(f"FloodWait: Sleeping for {e.x} seconds while fetching links.")
            await processing_msg.edit_text(f"Hit a small delay, waiting for {e.x}s. Processing will resume...")
            await asyncio.sleep(e.x)
            # Optionally, retry this specific link or just count as failed for now
            failed_count +=1 # Count as failed for now
        except Exception as e:
            logger.error(f"Error fetching message (chat_id: {link_data['channel_id']}, message_id: {link_data['message_id']}): {e}")
            failed_count += 1
            continue
            
    await processing_msg.delete() # Delete the "Processing..." message

    if success_count == 0:
        return await message.reply_text(
            "Oh no! I couldn't fetch any valid files from the links you provided. 🙁\n"
            "Please check the links and ensure the bot has access to the channel(s).\n"
            "You can try adding links again or /cancel."
        )
        
    temp.CURRENT_COURSES[user_id]["files"] = fetched_files_info # Store successfully fetched file details
    
    await message.reply_text(
        f"Great! I successfully processed **{success_count}** file(s) from the links. 🎉"
        + (f" ({failed_count} link(s) could not be processed.)" if failed_count > 0 else "")
        + "\n\nNext, would you like to add a **banner image** for this course? This image will be shown in announcements.\n\n"
        "Please send the image now, or type /skip to use a default banner.",
        disable_web_page_preview=True
    )
    user_states[user_id] = WAITING_BANNER

@Client.on_message(filters.command("skip") & filters.private & filters.user(ADMINS))
async def skip_banner(client, message):
    user_id = message.from_user.id
    
    if user_id not in user_states or user_states[user_id] != WAITING_BANNER:
        # User is not in the correct state to skip a banner
        return await message.reply_text("It doesn't look like you're at the banner step. Use /addcourse to start a new course.")
        
    if user_id in temp.CURRENT_COURSES:
        temp.CURRENT_COURSES[user_id]["banner"] = None
        await message.reply_text("Okay, we'll use a default banner. 👍")
        await confirm_course(client, message, user_id)
        user_states[user_id] = CONFIRM_COURSE
    else:
        # This case should ideally not be reached if state is WAITING_BANNER
        await message.reply_text("Something went wrong, no course data found. Please start over with /addcourse.")

@Client.on_callback_query(filters.regex(r"^course_action_"))
async def course_action_callback(client, callback_query):
    action = callback_query.data.split("_")[2] # e.g. "confirm", "cancel"
    user_id = callback_query.from_user.id
    message = callback_query.message # The message where the inline keyboard is

    if user_id not in temp.CURRENT_COURSES or user_id not in user_states:
        return await callback_query.answer("This action is no longer valid or has expired.", show_alert=True)

    if action == "cancel":
        if user_id in temp.CURRENT_COURSES: del temp.CURRENT_COURSES[user_id]
        if user_id in user_states: del user_states[user_id]
        await message.edit_text("Course creation cancelled. ❌")
        
    elif action == "confirm":
        await message.edit_text("Publishing course, please wait... 🚀")
        await publish_course(client, message, user_id) # Pass message for replies
        if user_id in temp.CURRENT_COURSES: del temp.CURRENT_COURSES[user_id]
        if user_id in user_states: del user_states[user_id]
            
    elif action == "banner":
        await message.reply_text( # Reply to the original message, not edit
            "Okay, please send a photo to use as the course banner.",
            reply_markup=ForceReply(True)
        )
        user_states[user_id] = WAITING_BANNER
        await callback_query.answer() # Answer the callback
        
    elif action == "edit_name":
        await message.reply_text( # Reply to the original message
            "What should the new course name be?",
            reply_markup=ForceReply(True)
        )
        temp.CURRENT_COURSES[user_id]['course_name'] = None # Clear to allow re-entry
        user_states[user_id] = WAITING_COURSE_NAME
        await callback_query.answer() # Answer the callback

async def confirm_course(client, message_or_callback_query, user_id):
    """Show course summary and ask for confirmation."""
    if user_id not in temp.CURRENT_COURSES:
        reply_target = message_or_callback_query.message if isinstance(message_or_callback_query, CallbackQuery) else message_or_callback_query
        return await reply_target.reply_text("No course data found. Please start over with /addcourse.")
        
    course_data = temp.CURRENT_COURSES[user_id]
    
    course_name = course_data.get("course_name", "Not Set Yet")
    # Files are now fetched info, not raw links
    file_count = len(course_data.get("files", [])) 
    total_size = sum(file_info.get("file_size", 0) for file_info in course_data.get("files", []))
    
    has_banner = course_data.get("banner") is not None
    
    text = script.CHECK_COURSE.format(
        course_name=course_name,
        file_count=file_count
    )
    text += f"\n<b>Total Size:</b> {get_size(total_size)}"
    text += f"\n<b>Banner Image:</b> {'✅ Added' if has_banner else '❌ Not Added (will use default)'}"
    text += "\n\n**Is this correct?**"
    
    buttons = [
        [
            InlineKeyboardButton("🖼️ Change Banner" if has_banner else "🖼️ Add Banner", callback_data="course_action_banner"),
            InlineKeyboardButton("✏️ Edit Name", callback_data="course_action_edit_name")
        ],
        [
            InlineKeyboardButton("✅ Confirm & Publish", callback_data="course_action_confirm"),
            InlineKeyboardButton("❌ Cancel Process", callback_data="course_action_cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    reply_target = message_or_callback_query.message if isinstance(message_or_callback_query, CallbackQuery) else message_or_callback_query
    if isinstance(message_or_callback_query, CallbackQuery) and message_or_callback_query.message.text != text : # Avoid MessageNotModified
         await reply_target.edit_text(text, reply_markup=reply_markup)
    else:
         await reply_target.reply_text(text, reply_markup=reply_markup)


async def publish_course(client, message_or_callback_query, user_id):
    """Publish the course to the database and announcement channel."""
    reply_target = message_or_callback_query.message if isinstance(message_or_callback_query, CallbackQuery) else message_or_callback_query

    if user_id not in temp.CURRENT_COURSES or not temp.CURRENT_COURSES[user_id].get("files"):
        return await reply_target.reply_text("Course data is incomplete (no files found). Please start over with /addcourse.")
        
    course_data = temp.CURRENT_COURSES[user_id]
    course_id = str(uuid.uuid4()) # Generate unique course ID
    
    course_doc = {
        "course_id": course_id,
        "course_name": course_data.get("course_name", "Untitled Course"),
        "added_by": user_id,
        "added_on": datetime.now(),
        "file_count": len(course_data.get("files", [])),
        "banner_id": course_data.get("banner"), # This is a file_id
        "total_size": sum(file_info.get("file_size", 0) for file_info in course_data.get("files", []))
    }
    
    success_db, _ = await save_course(course_doc)
    if not success_db:
        return await reply_target.reply_text("Failed to save course to database. Please try again or contact support. ⚠️")
    
    for i, file_info in enumerate(course_data.get("files", [])):
        file_doc = {
            "course_id": course_id,
            "file_id": file_info["file_id"], # The actual file_id from the source message
            "file_name": file_info["file_name"],
            "file_size": file_info["file_size"],
            # Use original caption if available, else generate one
            "caption": file_info.get("caption") or CUSTOM_FILE_CAPTION.format(file_name=file_info["file_name"], course_name=course_doc["course_name"]),
            "file_order": i + 1 
        }
        await save_course_file(file_doc)
    
    await reply_target.reply_text(script.COURSE_CONFIRM.format(course_name=course_doc["course_name"]))
    await announce_course(client, course_id, course_data) # Pass client object
    
async def announce_course(client, course_id, course_data): # Added client here
    if not PUBLIC_CHANNEL:
        logger.warning("PUBLIC_CHANNEL not set. Cannot announce course.")
        return
        
    course_name = course_data.get("course_name", "Untitled Course")
    banner_id = course_data.get("banner") # This is a file_id
    
    caption = script.COURSE_ADDED.format(course_name=course_name)
    buttons = [[
        InlineKeyboardButton("⬇️ Download Now", url=f"https://t.me/{temp.U_NAME}?start=course_{course_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    try:
        if banner_id:
            await client.send_photo(
                chat_id=PUBLIC_CHANNEL,
                photo=banner_id, # Send the photo using its file_id
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            # Consider a default placeholder image if no banner is provided
            # For now, just sending text
            await client.send_message(
                chat_id=PUBLIC_CHANNEL,
                text=caption,
                reply_markup=reply_markup,
                disable_web_page_preview=True # Good for messages without explicit images
            )
        logger.info(f"Course '{course_name}' announced successfully to {PUBLIC_CHANNEL}.")
    except Exception as e:
        logger.error(f"Error announcing course '{course_name}' to {PUBLIC_CHANNEL}: {e}")
        # Notify admins about the failure
        for admin_id in ADMINS:
            try:
                await client.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ **Announcement Failed** ⚠️\nCould not announce course '{course_name}' to public channel {PUBLIC_CHANNEL}.\nError: {e}"
                )
            except Exception as admin_notify_err:
                logger.error(f"Failed to notify admin {admin_id} about announcement error: {admin_notify_err}")

@Client.on_message(filters.command("search") & filters.text & filters.incoming)
async def search_courses_command(client, message):
    """Search for courses using text query."""
    if len(message.command) < 2:
        return await message.reply_text("Please provide a search query. Example: /search chess openings")
    
    query = " ".join(message.command[1:])
    
    # Call the database search function
    from database.courses_db import search_courses
    courses, next_offset, total = await search_courses(query)
    
    if not courses:
        return await message.reply_text(f"No courses found for '{query}'")
    
    text = f"**🔍 Search Results for '{query}'**\n\n"
    
    for i, course in enumerate(courses, 1):
        course_id = course['course_id']
        course_name = course['course_name']
        file_count = course['file_count']
        text += f"{i}. **{course_name}** - {file_count} files\n"
        
        # Add inline button for this course
        if i == len(courses): # Only add total at the end
            text += f"\nFound {total} results."
    
    # Create buttons for each course
    buttons = []
    for course in courses:
        buttons.append([
            InlineKeyboardButton(
                text=f"📚 {course['course_name']}",
                callback_data=f"course_{course['course_id']}"
            )
        ])
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r"^course_([0-9a-f-]+)$")) # Ensure this regex is specific enough
async def course_callback(client, callback_query):
    """Handle course selection callback from search or other lists."""
    course_id = callback_query.data.split("_")[1]
    
    course = await get_course_by_id(course_id)
    if not course:
        return await callback_query.answer("Sorry, this course could not be found. It might have been removed.", show_alert=True)
    
    files = await get_course_files(course_id)
    if not files:
        return await callback_query.answer("This course currently has no files. Please check back later.", show_alert=True)
    
    text = f"**📚 {course['course_name']}**\n\n"
    text += f"Total Files: {len(files)}\n"
    text += f"Total Size: {get_size(course['total_size'])}\n\n"
    text += "You can download individual files or all at once:"
    
    buttons = []
    # Limited to 5 individual files to prevent overly long messages, can be paginated later if needed
    for file_doc in files[:5]: 
        buttons.append([
            InlineKeyboardButton(
                text=f"{file_doc['file_name']} ({get_size(file_doc['file_size'])})",
                callback_data=f"sendfile_{file_doc['file_id']}" # Changed prefix to avoid conflict
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(
            text="📦 Download All Files",
            callback_data=f"sendall_{course_id}"
        )
    ])
    buttons.append([InlineKeyboardButton("🔙 Back to Search (Not Impl.)", callback_data="search_again_placeholder")])


    try:
        await callback_query.message.edit_text( # Edit if possible
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except MessageNotModified:
        pass
    except Exception as e: # Fallback to reply if edit fails for some reason
        logger.error(f"Error editing message for course callback: {e}")
        await callback_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    await callback_query.answer()

@Client.on_callback_query(filters.regex(r"^sendfile_")) # New callback for single file
async def send_single_file_callback(client, callback_query):
    file_id_to_send = callback_query.data.split("_", 1)[1]
    try:
        await callback_query.answer("Sending file...", show_alert=False)
        # Here, we assume the file_id is a direct, usable file_id.
        # If it's a reference to a DB document, you'd fetch that first.
        # For now, let's assume CUSTOM_FILE_CAPTION can be simple or needs formatting.
        # We need the file's actual caption or a generated one.
        # This part needs careful implementation based on how `file_id` is stored.
        # For now, sending directly.
        await client.send_cached_media(
            chat_id=callback_query.message.chat.id,
            file_id=file_id_to_send,
            # caption=CUSTOM_FILE_CAPTION # This might need more context like file_name
        )
    except Exception as e:
        logger.error(f"Error sending single file ({file_id_to_send}): {e}")
        await callback_query.answer(f"Could not send the file: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^sendall_([0-9a-f-]+)$"))
async def send_all_files_callback(client, callback_query):
    course_id = callback_query.data.split("_")[1]
    
    course = await get_course_by_id(course_id)
    if not course:
        return await callback_query.answer("Course not found.", show_alert=True)
    
    files = await get_course_files(course_id)
    if not files:
        return await callback_query.answer("No files found for this course.", show_alert=True)
    
    await callback_query.answer("Sending all files. This might take a moment...", show_alert=False)
    status_message = await callback_query.message.reply_text(f"Preparing to send {len(files)} files for '{course['course_name']}'...")
    
    sent_count = 0
    failed_send_count = 0
    for file_doc in files:
        try:
            # Use the caption stored in the database for each file
            caption_to_use = file_doc.get("caption", CUSTOM_FILE_CAPTION.format(file_name=file_doc["file_name"], course_name=course["course_name"]))
            await client.send_cached_media(
                chat_id=callback_query.message.chat.id,
                file_id=file_doc['file_id'],
                caption=caption_to_use 
            )
            sent_count += 1
            if sent_count % 5 == 0 and sent_count < len(files): # Avoid final update here
                try:
                    await status_message.edit_text(f"Sent {sent_count}/{len(files)} files for '{course['course_name']}'...")
                except MessageNotModified:
                    pass
            await asyncio.sleep(1) # Small delay
        except FloodWait as e:
            logger.warning(f"FloodWait: Sleeping for {e.x} seconds during send_all for course {course_id}.")
            await status_message.edit_text(f"Delay encountered, waiting {e.x}s. Will resume sending...")
            await asyncio.sleep(e.x)
            # Retry sending this file? For now, we'll just count it as failed and continue.
            failed_send_count += 1
        except Exception as e:
            logger.error(f"Error sending file {file_doc['file_name']} for course {course_id}: {e}")
            failed_send_count += 1
    
    final_status_text = f"✅ Successfully sent {sent_count} files for '{course['course_name']}'."
    if failed_send_count > 0:
        final_status_text += f" ({failed_send_count} file(s) failed to send.)"
    
    await status_message.edit_text(final_status_text) 