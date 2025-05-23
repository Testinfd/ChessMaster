class script(object):
    START_TXT = """<b>Hello {} 👋! Welcome to the Chess Courses Bot!</b>

I'm here to help you discover and share amazing chess educational content.

📚 **Looking for courses?** Just use the search or browse our collection.
👑 **Want to contribute?** Admins can easily add new courses.

Let's get started! What would you like to do?"""

    HELP_TXT = """<b>Hi {}! I'm here to help.</b>

Here's what I can do:

**For Everyone:**
*   `/start` - Get a friendly welcome and quick options.
*   `/help` - See this helpful message again.
*   `/about` - Learn more about me and my creators.
*   **Search Inline:** Type my name in any chat followed by your search query to find courses instantly! (e.g., `@YourBotName Beginner Openings`)

**For Admins:**
*   Manage courses (add, delete).
*   View bot statistics.
*   Broadcast messages to users.
*   And more! (Type `/adminhelp` for a full list of admin commands)

Got a question? Feel free to ask!"""

    ABOUT_TXT = """<b>⍟───[ ABOUT ME ]───⍟</b>

Hi, I'm <b><a href="https://t.me/{}">{}</a></b>!

I'm built to make finding and sharing chess courses super easy.

**Tech Specs:**
‣ Developer: <a href={}>My Awesome Owner</a>
‣ Powered by: <a href='https://docs.pyrogram.org/'>Pyrogram</a> & <a href='https://www.python.org/'>Python 3</a>
‣ Data Stored With: <a href='https://www.mongodb.com/'>MongoDB</a>
‣ Currently Chilling On: <a href='https://render.com'>Render</a> (or maybe Heroku, I get around!)
‣ Version: v1.0.1 [Always Improving!]

Got ideas to make me better? Let my developer know!"""

    MANUELFILTER_TXT = """<b>🔎 MANUAL FILTERS: A Quick Guide</b>

Manual filters help you quickly find specific courses within a group.

**How to Use:**
1.  Make sure I'm an admin in your group with all permissions.
2.  Use the `/filter` command followed by the course name and what it should point to (e.g., `/filter "Sicilian Defense Guide" course_link_or_id`).
3.  Only admins can add filters.

**Available Commands:**
*   `/filter <keyword> <replacement>` - Add a new filter.
*   `/filters` - Show all active filters in this chat.
*   `/del <keyword>` - Remove a specific filter.
*   `/delall` - Remove ALL filters in this chat (admin only).

Keep your group organized and courses easy to find!"""

    BUTTON_TXT = """<b>INTERACTIVE BUTTONS!</b>

I use buttons to make things easier for you! You'll see them pop up with options.
Some buttons will take you to a link (URL buttons), and others might show you a quick message (alert buttons). Just tap what you need!"""

    CONNECTIONM_TXT = """<b>🔗 CONNECT TO PRIVATE CHAT (PM)</b>

Connecting your group to your PM helps manage filters without cluttering the group chat.

**Why Connect?**
*   Manage filters privately.
*   Keep group chats focused on chess!

**Commands:**
*   `/connect` - Link this group to your PM.
*   `/disconnect` - Unlink this group from your PM.
*   `/connections` - See all your currently linked chats.

Easy peasy!"""

    ADMIN_TXT = """<b>👑 ADMIN COMMANDS: Full Control!</b>

Here are the commands you can use to manage the bot and content:

**Content Management:**
*   `/course` - Start the guided process to add a new chess course.
*   `/delete <file_id_or_message_link>` - Delete a specific file from a course.
*   *(More content commands might be available in specific modules, like course_manager)*

**User & Chat Management:**
*   `/users` - Get a list of all users who've interacted with the bot.
*   `/chats` - Get a list of all chats where the bot is a member.
*   `/leave <chat_id>` - Make the bot leave a specific chat.
*   `/disable <chat_id>` - Disable the bot's functions in a specific chat.
*   `/ban <user_id_or_username>` - Ban a user from using the bot.
*   `/unban <user_id_or_username>` - Unban a previously banned user.

**Bot Operations:**
*   `/logs` - View recent activity logs (e.g., errors, important events).
*   `/stats` - Show current bot statistics (users, courses, etc.).
*   `/broadcast <your_message>` - Send a message to ALL users of the bot. (Use with care!)

Remember, with great power comes great responsibility! 😉"""

    STATUS_TXT = """<b>📊 BOT STATUS AT A GLANCE:</b>

📚 Total Courses: <code>{}</code>
👥 Total Users: <code>{}</code>
💬 Total Chats: <code>{}</code>
💾 Used Storage: <code>{}</code>
💽 Free Storage: <code>{}</code>"""
    
    LOG_TEXT_G = """#NewGroupJoined
Group Name: {}(<code>{}</code>)
Total Members: <code>{}</code>
Added By: {}
Timestamp: {} (UTC)"""

    LOG_TEXT_P = """#NewUserRegistered
User ID: <code>{}</code>
User Name: {}
Timestamp: {} (UTC)"""

    ALRT_TXT = """⚠️ Oops, {}!

This course request wasn't started by you. To get your own courses, please start a new request or search directly. Thanks!"""

    OLD_ALRT_TXT = """⚠️ Hi {}!

It looks like you're trying to use an old message or button. Please try your request again from a newer message, or start over with `/start`."""

    CUDNT_FND = """🤔 Hmm, I couldn't find anything for "{}".

**Here are a few tips:**
*   Double-check your spelling.
*   Try using broader keywords (e.g., "openings" instead of "specific opening variation").
*   Browse all courses using the inline search feature (type `@YourBotName` in any chat).

Still no luck? The course might not be in my database yet!"""

    I_CUDNT = """<b>😥 Sorry, I couldn't find any courses matching: "{}"</b>

**Please try these suggestions:**
*   **Refine your search:** Use different keywords or be less specific. For example, instead of "Advanced Grunfeld Defense for 1800+ Elo", try "Grunfeld Defense" or "Advanced Openings".
*   **Check for typos:** A small typo can make a big difference!
*   **Browse all available courses:** Use the inline search (type `@YourBotName` in any chat) to see everything I have.

If you're looking for a specific course and can't find it, it might not have been added yet. You can always suggest new courses to the admin!"""

    NO_RESULTS = """🤷 No courses found matching your search criteria.

Try simplifying your search terms or browse all available courses using inline search (type `@YourBotName` in any chat)."""

    TOP_ALRT_MSG = """⏳ Searching for courses... please wait a moment!"""

    MELCOW = """<b>Hey {} 🎉, welcome to the {} group! Get ready for some great chess discussions and content. ♟️</b>"""

    SHORTLINK_INFO = """🔒 To access this course, please join our main channel first. This helps us share exclusive content with our community!"""

    REQINFO = """⚠️ **Quick Info!** ⚠️

This message will disappear in 5 minutes.

If the course you wanted isn't listed, try the next page or use more specific search terms. Happy learning!"""

    SELECT = """👇 Please choose the course you're looking for from the list below:"""

    COURSE_NOT_FOUND = """🙁 Sorry, I couldn't find that specific course.

It might have been removed, or the ID could be incorrect. Please try searching for the course by name."""
    
    CAPTION = """<b>📚 Course:</b> {course_name}
    
💾 **Size:** {file_size}"""

    CHECK_COURSE = """⏳ **Reviewing Your Course Upload...**

Please check these details carefully:

**Course Name:** {course_name}
**Number of Files:** {file_count}

What would you like to do next?
1.  🖼️ Add/Change Banner Image
2.  ✏️ Edit Course Name
3.  ✅ Confirm and Publish
4.  ❌ Cancel Upload"""

    COURSE_CONFIRM = """✅ **Success! Your chess course has been added to the database!**

It's now available for users to find and download. Great job!"""
    
    COURSE_ADDED = """<b>🎉 NEW CHESS COURSE AVAILABLE! 🎉</b>

📚 **{course_name}**

Click the button below to get all the files for this course. Happy learning!"""

    COURSE_HELP = """<b>📖 HOW TO ADD A NEW CHESS COURSE (Admin Guide):</b>

Here are two ways to add courses:

**Method 1: Forwarding Files (Quick Add)**
1.  Upload ALL course files to a private channel or chat with me.
2.  Forward the VERY LAST file from the course to me.
3.  In the caption of that forwarded message, type the **Course Name**.
4.  I'll then ask you to confirm the details and optionally add a banner image.
5.  Once confirmed, I'll make it available and announce it (if configured).

**Method 2: Guided Command**
*   Use the `/course` command.
*   I will then guide you step-by-step: asking for the name, then the files, then a banner.

Choose the method that works best for you!"""

    SEARCH_HELP = """<b>🔍 HOW TO FIND CHESS COURSES:</b>

Finding courses is easy! Here are a few ways:

*   **Direct Search:** Just send me a message with the name or keywords of the course you're looking for (e.g., "Sicilian Defense", "Endgame Strategy").
*   **Inline Search (Recommended!):**
    1.  Go to any chat (even this one!).
    2.  Type my username: `@YourBotName` (replace `YourBotName` with my actual username).
    3.  Type a space, then your search query (e.g., `@YourBotName King's Indian Attack`).
    4.  You'll see a list of matching courses appear directly in the chat input area. Tap to send!

**Search Tips:**
*   Keep it simple: "beginner tactics" is better than "chess tactics for beginners under 1200 elo".
*   Try variations: If "Queen's Gambit" doesn't work, try "QGD" or "Gambit Queen".
*   Use broader terms if you're not sure of the exact title.

Happy searching!""" 