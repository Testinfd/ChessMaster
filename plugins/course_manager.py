import logging
import asyncio
import time
import random
import uuid
from datetime import datetime
import pyrogram
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from pyrogram.errors import FloodWait, UserIsBlocked

from info import ADMINS, COURSE_CHANNEL, PUBLIC_CHANNEL, CUSTOM_FILE_CAPTION
from database.courses_db import save_course, save_course_file, get_course_by_id, update_course
from utils import temp, get_size, get_file_id, clean_text
from Script import script

logger = logging.getLogger(__name__)

# States for course creation conversation
WAITING_COURSE_NAME = 1
WAITING_COURSE_FILES = 2
WAITING_BANNER = 3
CONFIRM_COURSE = 4

# Store conversation states for users
user_states = {}

@Client.on_message(filters.chat(COURSE_CHANNEL) & filters.forwarded & filters.user(ADMINS))
async def handle_channel_forward(client, message):
    """Process forwarded messages from the course channel."""
    if message.from_user.id not in ADMINS:
        return
        
    # Check if this is a media file
    file_type = message.media
    if not file_type:
        return
        
    # Extract file details
    file_obj, file_id = get_file_id(message)
    if not file_id:
        return await message.reply_text("Unable to extract file ID.")
        
    # Get the course name from caption or ask the admin
    caption = message.caption
    file_name = getattr(file_obj, "file_name", "Unknown")
    
    if caption:
        # If caption is present, consider it as course name
        course_name = caption
        await initiate_course_creation(client, message, course_name, file_id, file_obj)
    else:
        # No caption, ask for course name
        await message.reply_text(
            "This appears to be a course file. What's the name of this course?",
            reply_markup=ForceReply(True)
        )
        # Store the file_id temporarily
        temp.CURRENT_COURSES[message.from_user.id] = {
            "message_id": message.id,
            "file_id": file_id,
            "file_obj": file_obj
        }
        user_states[message.from_user.id] = WAITING_COURSE_NAME

@Client.on_message(filters.private & filters.reply & filters.user(ADMINS))
async def handle_course_replies(client, message):
    """Handle replies during course creation conversation."""
    user_id = message.from_user.id
    
    # Check if user is in conversation
    if user_id not in user_states:
        return
        
    state = user_states[user_id]
    replied_message = message.reply_to_message
    
    if state == WAITING_COURSE_NAME:
        # Processing course name
        course_name = clean_text(message.text)
        
        if not course_name:
            return await message.reply_text("Please provide a valid course name.")
            
        if user_id in temp.CURRENT_COURSES:
            # We have a file already
            file_data = temp.CURRENT_COURSES[user_id]
            await initiate_course_creation(
                client, 
                message, 
                course_name,
                file_data["file_id"],
                file_data["file_obj"]
            )
        else:
            # No file yet, ask for files
            await message.reply_text(
                f"Great! Now please forward all files for the course '{course_name}' from the private channel.\n\n"
                "When you've finished sending all files, type /done"
            )
            temp.CURRENT_COURSES[user_id] = {
                "course_name": course_name,
                "files": []
            }
            user_states[user_id] = WAITING_COURSE_FILES
    
    elif state == WAITING_COURSE_FILES:
        # This should be handled by the forwarded messages handler
        pass
        
    elif state == WAITING_BANNER:
        # Process banner image
        if not message.photo:
            return await message.reply_text("Please send a photo for the banner, or type /skip to skip this step.")
            
        photo = message.photo
        photo_id = photo.file_id
        
        # Store banner
        if user_id in temp.CURRENT_COURSES:
            temp.CURRENT_COURSES[user_id]["banner"] = photo_id
            
            # Move to confirmation
            await confirm_course(client, message, user_id)
            user_states[user_id] = CONFIRM_COURSE
            
    elif state == CONFIRM_COURSE:
        # Process confirmation
        response = message.text.lower()
        
        if response in ["yes", "y", "confirm", "3", "confirm and publish"]:
            # Publish the course
            await publish_course(client, message, user_id)
            # Clean up
            if user_id in temp.CURRENT_COURSES:
                del temp.CURRENT_COURSES[user_id]
            if user_id in user_states:
                del user_states[user_id]
        elif response in ["no", "n", "cancel", "4"]:
            # Cancel the process
            await message.reply_text("Course creation cancelled.")
            # Clean up
            if user_id in temp.CURRENT_COURSES:
                del temp.CURRENT_COURSES[user_id]
            if user_id in user_states:
                del user_states[user_id]
        elif response in ["1", "add banner", "banner"]:
            # Add banner
            await message.reply_text(
                "Please send a photo to use as the course banner.",
                reply_markup=ForceReply(True)
            )
            user_states[user_id] = WAITING_BANNER
        elif response in ["2", "modify name", "edit name"]:
            # Edit course name
            await message.reply_text(
                "Please enter the new course name:",
                reply_markup=ForceReply(True)
            )
            user_states[user_id] = WAITING_COURSE_NAME
        else:
            await message.reply_text(
                "Please choose one of the options:\n"
                "1. Add a banner image\n"
                "2. Modify the course name\n"
                "3. Confirm and publish\n"
                "4. Cancel"
            )

@Client.on_message(filters.command("done") & filters.private & filters.user(ADMINS))
async def done_collecting_files(client, message):
    """Handle completion of file collection."""
    user_id = message.from_user.id
    
    if user_id not in user_states or user_states[user_id] != WAITING_COURSE_FILES:
        return await message.reply_text("You're not currently adding course files.")
        
    if user_id not in temp.CURRENT_COURSES:
        return await message.reply_text("No course data found. Please start over with /course.")
        
    course_data = temp.CURRENT_COURSES[user_id]
    
    if "files" not in course_data or not course_data["files"]:
        return await message.reply_text("You haven't added any files yet. Please forward files from the private channel.")
        
    await message.reply_text(
        "Now, please send a banner image for the course. This will be displayed in the announcement.\n\n"
        "Or type /skip to use a default image."
    )
    user_states[user_id] = WAITING_BANNER

@Client.on_message(filters.command("skip") & filters.private & filters.user(ADMINS))
async def skip_banner(client, message):
    """Skip banner image for the course."""
    user_id = message.from_user.id
    
    if user_id not in user_states or user_states[user_id] != WAITING_BANNER:
        return
        
    # Use a default banner (None)
    if user_id in temp.CURRENT_COURSES:
        temp.CURRENT_COURSES[user_id]["banner"] = None
        
    # Move to confirmation
    await confirm_course(client, message, user_id)
    user_states[user_id] = CONFIRM_COURSE

@Client.on_message(filters.chat(COURSE_CHANNEL) & filters.forwarded & ~filters.command("done") & filters.user(ADMINS))
async def collect_course_files(client, message):
    """Collect files from forwarded messages."""
    user_id = message.from_user.id
    
    # Check if user is in the right state
    if user_id not in user_states or user_states[user_id] != WAITING_COURSE_FILES:
        return
        
    # Check if this is a media file
    file_type = message.media
    if not file_type:
        return
        
    # Extract file details
    file_obj, file_id = get_file_id(message)
    if not file_id:
        return await message.reply_text("Unable to extract file ID.")
        
    # Get file metadata
    file_name = getattr(file_obj, "file_name", "Unknown")
    file_size = getattr(file_obj, "file_size", 0)
    
    # Store the file
    if user_id in temp.CURRENT_COURSES:
        if "files" not in temp.CURRENT_COURSES[user_id]:
            temp.CURRENT_COURSES[user_id]["files"] = []
            
        temp.CURRENT_COURSES[user_id]["files"].append({
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "caption": message.caption,
            "message_id": message.id
        })
        
        # Acknowledge receipt
        await message.reply_text(
            f"Added file: {file_name}\nSize: {get_size(file_size)}\n\n"
            f"Total files so far: {len(temp.CURRENT_COURSES[user_id]['files'])}\n\n"
            "Continue forwarding files or type /done when finished."
        )

@Client.on_callback_query(filters.regex(r"^course_action_"))
async def course_action_callback(client, callback_query):
    """Handle course action callbacks."""
    action = callback_query.data.split("_")[2]
    user_id = callback_query.from_user.id
    
    if action == "cancel":
        # Cancel course creation
        if user_id in temp.CURRENT_COURSES:
            del temp.CURRENT_COURSES[user_id]
        if user_id in user_states:
            del user_states[user_id]
        await callback_query.message.edit_text("Course creation cancelled.")
        
    elif action == "confirm":
        # Publish the course
        await callback_query.message.edit_text("Publishing course...")
        await publish_course(client, callback_query.message, user_id)
        # Clean up
        if user_id in temp.CURRENT_COURSES:
            del temp.CURRENT_COURSES[user_id]
        if user_id in user_states:
            del user_states[user_id]
            
    elif action == "banner":
        # Add banner
        await callback_query.message.reply_text(
            "Please send a photo to use as the course banner.",
            reply_markup=ForceReply(True)
        )
        user_states[user_id] = WAITING_BANNER
        
    elif action == "edit_name":
        # Edit course name
        await callback_query.message.reply_text(
            "Please enter the new course name:",
            reply_markup=ForceReply(True)
        )
        user_states[user_id] = WAITING_COURSE_NAME

async def initiate_course_creation(client, message, course_name, file_id, file_obj):
    """Start the course creation process with initial file."""
    user_id = message.from_user.id
    
    # Initialize course data
    temp.CURRENT_COURSES[user_id] = {
        "course_name": course_name,
        "files": [{
            "file_id": file_id,
            "file_name": getattr(file_obj, "file_name", "Unknown"),
            "file_size": getattr(file_obj, "file_size", 0),
            "caption": message.caption,
            "message_id": message.id
        }]
    }
    
    # Ask for more files
    await message.reply_text(
        f"Started creating course '{course_name}'.\n\n"
        f"Added first file: {getattr(file_obj, 'file_name', 'Unknown')}\n"
        f"Size: {get_size(getattr(file_obj, 'file_size', 0))}\n\n"
        "Please forward all additional files for this course from the private channel.\n\n"
        "When you've finished sending all files, type /done"
    )
    
    user_states[user_id] = WAITING_COURSE_FILES

async def confirm_course(client, message, user_id):
    """Show course summary and ask for confirmation."""
    if user_id not in temp.CURRENT_COURSES:
        return await message.reply_text("No course data found. Please start over with /course.")
        
    course_data = temp.CURRENT_COURSES[user_id]
    
    # Generate course summary
    course_name = course_data.get("course_name", "Unknown")
    file_count = len(course_data.get("files", []))
    total_size = sum(file.get("file_size", 0) for file in course_data.get("files", []))
    
    has_banner = "banner" in course_data and course_data["banner"] is not None
    
    # Show confirmation message
    text = script.CHECK_COURSE.format(
        course_name=course_name,
        file_count=file_count
    )
    
    # Add file size information
    text += f"\n<b>Total Size:</b> {get_size(total_size)}"
    text += f"\n<b>Banner Image:</b> {'✅ Added' if has_banner else '❌ Not added'}"
    
    # Create reply buttons
    buttons = [
        [
            InlineKeyboardButton("1️⃣ Add Banner", callback_data="course_action_banner"),
            InlineKeyboardButton("2️⃣ Edit Name", callback_data="course_action_edit_name")
        ],
        [
            InlineKeyboardButton("3️⃣ Confirm & Publish", callback_data="course_action_confirm"),
            InlineKeyboardButton("4️⃣ Cancel", callback_data="course_action_cancel")
        ]
    ]
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def publish_course(client, message, user_id):
    """Publish the course to the database and announcement channel."""
    if user_id not in temp.CURRENT_COURSES:
        return await message.reply_text("No course data found. Please start over with /course.")
        
    course_data = temp.CURRENT_COURSES[user_id]
    
    # Generate a unique course ID
    course_id = str(uuid.uuid4())
    
    # Prepare course data for database
    course_doc = {
        "course_id": course_id,
        "course_name": course_data.get("course_name", "Unknown Course"),
        "added_by": user_id,
        "added_on": datetime.now(),
        "file_count": len(course_data.get("files", [])),
        "banner_id": course_data.get("banner"),
        "total_size": sum(file.get("file_size", 0) for file in course_data.get("files", []))
    }
    
    # Save course to database
    success, _ = await save_course(course_doc)
    
    if not success:
        return await message.reply_text("Failed to save course to database. Please try again.")
    
    # Save each file with association to this course
    for i, file in enumerate(course_data.get("files", [])):
        file_doc = {
            "course_id": course_id,
            "file_id": file["file_id"],
            "file_name": file["file_name"],
            "file_size": file["file_size"],
            "caption": file["caption"] or CUSTOM_FILE_CAPTION.format(file_name=file["file_name"]),
            "file_order": i + 1  # 1-based ordering
        }
        await save_course_file(file_doc)
    
    # Notify admin
    await message.reply_text(script.COURSE_CONFIRM)
    
    # Post to announcement channel
    await announce_course(client, course_id, course_data)
    
async def announce_course(client, course_id, course_data):
    """Announce the new course on the public channel."""
    if not PUBLIC_CHANNEL:
        return
        
    course_name = course_data.get("course_name", "Unknown Course")
    banner_id = course_data.get("banner")
    
    # Create the announcement message
    caption = script.COURSE_ADDED.format(course_name=course_name)
    
    # Create the Download button with deep link
    buttons = [[
        InlineKeyboardButton("⬇️ Download Now", url=f"https://t.me/{temp.U_NAME}?start=course_{course_id}")
    ]]
    
    # Send to public channel
    try:
        if banner_id:
            # Use the provided banner
            await client.send_photo(
                chat_id=PUBLIC_CHANNEL,
                photo=banner_id,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            # Default announcement without image
            await client.send_message(
                chat_id=PUBLIC_CHANNEL,
                text=caption,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    except Exception as e:
        logger.error(f"Error announcing course: {e}")
        # Try to update the admin
        try:
            for admin in ADMINS:
                await client.send_message(
                    chat_id=admin,
                    text=f"Error announcing course '{course_name}' to public channel: {e}"
                )
        except:
            pass 