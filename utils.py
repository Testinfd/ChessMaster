import re
import os
import math
import time
import asyncio
import logging
import requests
import aiohttp
from pyrogram.errors import UserNotParticipant
from info import FORCE_SUB, PUBLIC_CHANNEL, AUTO_DELETE, AUTO_SEND_AFTER_SUBSCRIBE, TUTORIAL_BUTTON_ENABLED, TUTORIAL_BUTTON_URL, SHORTENER_API, SHORTENER_DOMAIN, SHORTENER_API_KEY, SHORTENER_ENABLED

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN = {}

class temp:
    """Temporary storage for various data used by the bot."""
    BOT = None
    ME = None
    U_NAME = None
    B_NAME = None
    BANNED_USERS = []
    BANNED_CHATS = []
    
    # For storing course data during the course creation process
    CURRENT_COURSES = {}
    COURSE_FILES = {}
    COURSE_BANNERS = {}
    
    # For storing search results
    SEARCH_DATA = {}
    
    # For storing temporary verification data
    VERIFICATION_DATA = {}
    
    # For storing user's pending downloads (for force subscribe)
    PENDING_DOWNLOADS = {}
    
    # For storing premium user data
    PREMIUM_USERS = []
    
    # For broadcast message
    BROADCAST_MSG = ""

def get_size(size_in_bytes):
    """Convert bytes to human-readable sizes."""
    if not size_in_bytes:
        return "0B"
    
    size_units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_in_bytes)
    i = 0
    
    while size >= 1024.0 and i < len(size_units) - 1:
        size /= 1024.0
        i += 1
        
    return "{:.2f} {}".format(size, size_units[i])

async def is_subscribed(bot, user_id, force_sub=None):
    """Check if user is subscribed to the force_sub channel."""
    if not FORCE_SUB:
        return True
        
    channel = force_sub or PUBLIC_CHANNEL
    
    if not channel:
        return True
        
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
    except UserNotParticipant:
        return False
    
    return member.status in ["creator", "administrator", "member"]

def extract_course_id(data):
    """Extract course_id from callback data."""
    return data.split("_")[1] if len(data.split("_")) > 1 else None

def extract_user_id(data):
    """Extract user_id from callback data."""
    return int(data.split("#")[1]) if len(data.split("#")) > 1 else None

def get_file_id(msg):
    """Extract file_id from a message."""
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                return obj, obj.file_id

def clean_text(text):
    """Clean text of any special characters and extra whitespace."""
    if not text:
        return ""
    return re.sub(r'[^\w\s]', '', text).strip()

def human_to_bytes(size_str):
    """Convert human-readable size to bytes."""
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 ** 2,
        "GB": 1024 ** 3,
        "TB": 1024 ** 4,
    }
    
    size_str = size_str.upper()
    if not re.match(r' ', size_str):
        size_str = re.sub(r'([KMGT]?B)', r' \1', size_str)
    
    number, unit = [string.strip() for string in size_str.split()]
    return int(float(number) * units[unit])

async def delete_message_after_delay(bot, message, delay=300):
    """Delete a message after a specified delay."""
    if not AUTO_DELETE:
        return
        
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

async def send_all_files(bot, chat_id, course_id, files):
    """Send all files related to a course to a user."""
    from database.courses_db import get_course_by_id
    
    # Get course details for logging
    course = await get_course_by_id(course_id)
    course_name = course.get('course_name', 'Unknown') if course else 'Unknown'
    
    logger.info(f"Sending {len(files)} files for course '{course_name}' to user {chat_id}")
    
    # Add tutorial button if enabled
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    tutorial_buttons = None
    
    if TUTORIAL_BUTTON_ENABLED and TUTORIAL_BUTTON_URL:
        tutorial_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 Tutorial", url=TUTORIAL_BUTTON_URL)]
        ])
    
    # Send files
    sent_files = 0
    for file in files:
        try:
            if 'caption' in file and file['caption']:
                caption = file['caption']
            else:
                caption = f"📚 {file['file_name'] if 'file_name' in file else 'Course file'}"
                
            await bot.send_cached_media(
                chat_id=chat_id,
                file_id=file['file_id'],
                caption=caption,
                protect_content=PROTECT_CONTENT,
                reply_markup=tutorial_buttons
            )
            sent_files += 1
            # Small delay to prevent flooding
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            continue
    
    logger.info(f"Successfully sent {sent_files} files for course '{course_name}' to user {chat_id}")
    return sent_files == len(files)

async def check_premium_user(user_id):
    """Check if a user has premium access."""
    from database.users_chats_db import db
    if not user_id:
        return False
        
    # Admins always have premium access
    from info import ADMINS
    if user_id in ADMINS:
        return True
        
    # Check if user ID is in the premium users list
    if user_id in temp.PREMIUM_USERS:
        return True
        
    # Check database for premium status
    user = await db.get_user(user_id)
    if user and user.get('is_premium', False):
        # Cache the result
        if user_id not in temp.PREMIUM_USERS:
            temp.PREMIUM_USERS.append(user_id)
        return True
        
    return False

async def store_pending_download(user_id, course_id):
    """Store a pending download for a user who needs to subscribe."""
    if user_id not in temp.PENDING_DOWNLOADS:
        temp.PENDING_DOWNLOADS[user_id] = []
        
    if course_id not in temp.PENDING_DOWNLOADS[user_id]:
        temp.PENDING_DOWNLOADS[user_id].append(course_id)
        
    return True

async def process_pending_downloads(bot, user_id):
    """Process any pending downloads for a user who just subscribed."""
    if not AUTO_SEND_AFTER_SUBSCRIBE:
        return False
        
    if user_id not in temp.PENDING_DOWNLOADS:
        return False
        
    from database.courses_db import get_course_by_id, get_course_files
    
    success = True
    for course_id in temp.PENDING_DOWNLOADS[user_id]:
        course = await get_course_by_id(course_id)
        if not course:
            continue
            
        files = await get_course_files(course_id)
        if not files:
            continue
            
        # Send welcome message
        welcome_text = f"<b>Welcome to the {course['course_name']} course!</b>\n\nNow that you've subscribed, I'll send you all files related to this course."
        await bot.send_message(chat_id=user_id, text=welcome_text)
        
        # Send all files
        result = await send_all_files(bot, user_id, course_id, files)
        if not result:
            success = False
            
        # Send completion message
        complete_text = "<b>✅ All course files have been sent!\n\nEnjoy learning chess. If you need more courses, just search or browse our collection.</b>"
        await bot.send_message(chat_id=user_id, text=complete_text)
    
    # Clear pending downloads
    temp.PENDING_DOWNLOADS[user_id] = []
    
    return success

def get_readable_time(seconds):
    """Get human-readable time from seconds."""
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d'
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h'
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m'
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def is_valid_token(token):
    """Check if token is valid (implement your own logic)."""
    # This is a placeholder - implement your actual validation logic
    if not token:
        return False
    # Simple validation - should be enhanced with database validation
    return len(token) == 8 and token.isalnum()

async def verify_token(token, user_id):
    """Verify a token for a user."""
    from database.token_db import verify_user_token
    return await verify_user_token(token, user_id)

async def check_token_required(user_id):
    """Check if a user needs token verification."""
    from info import TOKEN_VERIFICATION_ENABLED
    if not TOKEN_VERIFICATION_ENABLED:
        return False
    
    # Check if user is already verified
    from database.token_db import is_user_verified
    return not await is_user_verified(user_id)

# URL Shortener Functions
async def get_shortlink(link):
    """Get shortened URL for a link if shortener is enabled."""
    if not SHORTENER_ENABLED or not SHORTENER_API_KEY or not SHORTENER_DOMAIN:
        return link
    
    try:
        # Different shorteners use different APIs - this is an example for a common format
        async with aiohttp.ClientSession() as session:
            if SHORTENER_API:
                # For APIs like shorte.st, bit.ly, etc.
                url = SHORTENER_API.replace('{link}', link).replace('{api}', SHORTENER_API_KEY)
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'shortenedUrl' in data:
                            return data['shortenedUrl']
                        elif 'shortlink' in data:
                            return data['shortlink']
                        elif 'result_url' in data:
                            return data['result_url']
            else:
                # Default implementation (could be replaced with specific provider API)
                url = f"https://{SHORTENER_DOMAIN}/api"
                params = {
                    'api': SHORTENER_API_KEY,
                    'url': link
                }
                async with session.post(url, json=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            return data.get('shortenedUrl', link)
    except Exception as e:
        logger.error(f"Error in shortening URL: {e}")
    
    return link

def is_subscribed(bot, user_id, chat_id):
    """Check if a user is subscribed to a channel."""
    try:
        member = bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if member.status not in ["left", "kicked"]:
            return True
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
    return False 