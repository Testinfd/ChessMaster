import asyncio
import logging
import re
import uuid
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQueryResultArticle, InputTextMessageContent,
    InlineQueryResultPhoto, InlineQueryResultCachedDocument
)
from pyrogram.errors import FloodWait, UserIsBlocked

from database.courses_db import search_courses, get_course_by_id, get_course_files
from utils import temp, get_size, extract_course_id, get_shortlink
from info import ADMINS, CUSTOM_FILE_CAPTION, SHORTENER_ENABLED
from Script import script

logger = logging.getLogger(__name__)

@Client.on_inline_query()
async def inline_search(client, query):
    """Handle inline queries for course search."""
    # Get search query
    search_text = query.query.strip()
    
    # If query is empty, suggest how to use inline search
    if not search_text:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="Search for Chess Courses",
                    description="Type a course name to search",
                    input_message_content=InputTextMessageContent(
                        "**How to use inline search:**\n"
                        "Type @yourbotname followed by your search query to find chess courses.\n\n"
                        "Example: @yourbotname opening strategies"
                    ),
                    thumb_url="https://i.imgur.com/ede5DtC.png"
                )
            ],
            cache_time=5
        )
        return
    
    # Search for courses
    courses, _, total = await search_courses(search_text, max_results=20)
    
    if not courses:
        # No results found
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="No courses found",
                    description=f"No chess courses matching '{search_text}'",
                    input_message_content=InputTextMessageContent(
                        f"No chess courses found for query: **{search_text}**"
                    ),
                    thumb_url="https://i.imgur.com/ede5DtC.png"
                )
            ],
            cache_time=5
        )
        return
    
    # Convert courses to inline results
    results = []
    for course in courses:
        course_id = course['course_id']
        course_name = course['course_name']
        file_count = course['file_count']
        total_size = course.get('total_size', 0)
        banner_id = course.get('banner_id')
        
        # Create deep link for course
        bot_username = (await client.get_me()).username
        deep_link = f"https://t.me/{bot_username}?start=course_{course_id}"
        
        # Use URL shortener if enabled
        if SHORTENER_ENABLED:
            deep_link = await get_shortlink(deep_link)
        
        # Create description and message content
        description = f"{file_count} files • {get_size(total_size)}"
        message_content = InputTextMessageContent(
            f"**📚 {course_name}**\n\n"
            f"Files: {file_count}\n"
            f"Total Size: {get_size(total_size)}\n\n"
            f"Use the button below to access this course."
        )
        
        # Create reply markup with download button
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇️ Download Course", url=deep_link)]
        ])
        
        # If course has a banner, use photo result
        if banner_id:
            try:
                # Add as photo result if banner exists
                results.append(
                    InlineQueryResultPhoto(
                        photo_url=f"https://t.me/c/{str(banner_id).split('_')[0]}/{str(banner_id).split('_')[1]}",
                        thumb_url=f"https://t.me/c/{str(banner_id).split('_')[0]}/{str(banner_id).split('_')[1]}",
                        title=course_name,
                        description=description,
                        caption=f"**📚 {course_name}**\n\n"
                                f"Files: {file_count}\n"
                                f"Total Size: {get_size(total_size)}",
                        reply_markup=reply_markup
                    )
                )
            except Exception as e:
                # Fallback to article if there's an issue with the photo
                logger.error(f"Error creating photo result: {e}")
                results.append(
                    InlineQueryResultArticle(
                        title=course_name,
                        description=description,
                        input_message_content=message_content,
                        reply_markup=reply_markup,
                        thumb_url="https://i.imgur.com/ede5DtC.png"
                    )
                )
        else:
            # Use article result for courses without banner
            results.append(
                InlineQueryResultArticle(
                    title=course_name,
                    description=description,
                    input_message_content=message_content,
                    reply_markup=reply_markup,
                    thumb_url="https://i.imgur.com/ede5DtC.png"
                )
            )
    
    # Answer the query with results
    await query.answer(
        results=results,
        cache_time=300  # Cache for 5 minutes
    )

@Client.on_message(filters.command("course") & filters.regex(r"_([0-9a-f-]+)$"))
async def get_course_from_deeplink(client, message):
    """Handle deep links for courses."""
    course_id = message.command[1].split("_")[1]
    
    # Get course details
    course = await get_course_by_id(course_id)
    if not course:
        return await message.reply_text("Course not found or has been removed.")
    
    # Get course files
    files = await get_course_files(course_id)
    if not files:
        return await message.reply_text("No files found for this course.")
    
    # Create file list message
    text = f"**📚 {course['course_name']}**\n\n"
    text += f"Total Files: {len(files)}\n"
    text += f"Total Size: {get_size(course['total_size'])}\n\n"
    text += "Select a file to download:"
    
    # Create buttons for files
    buttons = []
    for file in files:
        buttons.append([
            InlineKeyboardButton(
                text=f"{file['file_name']} ({get_size(file['file_size'])})",
                callback_data=f"file_{file['file_id']}"
            )
        ])
    
    # Add a button to send all files
    buttons.append([
        InlineKeyboardButton(
            text="📦 Download All Files",
            callback_data=f"sendall_{course_id}"
        )
    ])
    
    # If course has banner, send as photo
    if course.get('banner_id'):
        try:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=course['banner_id'],
                caption=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            # Fallback to text message if photo fails
            await message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    else:
        # Send as text message
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

@Client.on_callback_query(filters.regex(r"^file_"))
async def send_file_callback(client, callback_query):
    """Send a specific file from a course."""
    file_id = callback_query.data.split("_")[1]
    
    try:
        # Send the file using cached media
        await callback_query.answer("Sending file...")
        await client.send_cached_media(
            chat_id=callback_query.message.chat.id,
            file_id=file_id,
            caption=CUSTOM_FILE_CAPTION
        )
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await callback_query.answer("Failed to send file. Please try again later.", show_alert=True) 