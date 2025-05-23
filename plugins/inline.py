import asyncio
import logging
import re
import uuid
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, InlineQuery

from database.courses_db import search_courses, get_course_files
from utils import temp, get_size, extract_course_id

logger = logging.getLogger(__name__)

@Client.on_inline_query()
async def inline_search(client, query: InlineQuery):
    """Handle inline queries to search for courses."""
    # Get query text
    search_text = query.query.strip()
    
    # Default response when no query or very short query
    if len(search_text) < 2:
        # Show some example courses or instructions
        results = [
            InlineQueryResultArticle(
                title="Search for Chess Courses",
                description="Type at least 2 characters to search for chess courses",
                input_message_content=InputTextMessageContent(
                    "💻 **How to Search for Chess Courses**\n\n"
                    "Use the inline search feature by typing @YourBotUsername followed by the course name or keywords.\n\n"
                    "Examples:\n"
                    "- Beginner tactics\n"
                    "- Openings\n"
                    "- Magnus Carlsen\n"
                    "- Endgames"
                ),
                thumb_url="https://example.com/search_icon.jpg"  # Replace with your search icon URL
            )
        ]
        await query.answer(
            results=results,
            cache_time=10,
            is_personal=True
        )
        return
    
    # Search for courses
    courses, next_offset, total = await search_courses(search_text, max_results=10)
    
    if not courses:
        # No results
        results = [
            InlineQueryResultArticle(
                title="No courses found",
                description="Try a different search term",
                input_message_content=InputTextMessageContent(
                    f"❌ No chess courses found for '{search_text}'\n\nTry different keywords or browse our channel."
                ),
                thumb_url="https://example.com/not_found.jpg"  # Replace with your not found icon URL
            )
        ]
        await query.answer(
            results=results,
            cache_time=60,
            is_personal=True
        )
        return
    
    results = []
    
    # Format each course as an inline result
    for course in courses:
        course_id = course.get("course_id")
        course_name = course.get("course_name", "Unknown Course")
        file_count = course.get("file_count", 0)
        total_size = course.get("total_size", 0)
        
        # Create a unique ID for this result
        result_id = str(uuid.uuid4())
        
        # Get a thumbnail if available (banner ID)
        banner_id = course.get("banner_id")
        
        # Create keyboard for the course
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "⬇️ Download Course",
                url=f"https://t.me/{temp.U_NAME}?start=course_{course_id}"
            )]
        ])
        
        # Create the article result
        result = InlineQueryResultArticle(
            id=result_id,
            title=course_name,
            description=f"Files: {file_count} | Size: {get_size(total_size)}",
            input_message_content=InputTextMessageContent(
                f"📚 **Chess Course Found: {course_name}**\n\n"
                f"• Number of Files: {file_count}\n"
                f"• Total Size: {get_size(total_size)}\n\n"
                f"Click the button below to download all files for this course."
            ),
            reply_markup=keyboard,
            thumb_url="https://example.com/course_icon.jpg"  # Replace with your course icon URL
        )
        
        results.append(result)
    
    # Answer the inline query with the results
    await query.answer(
        results=results,
        cache_time=300,  # Cache for 5 minutes
        is_personal=True
    ) 