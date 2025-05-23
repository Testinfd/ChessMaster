import re
from os import environ

id_pattern = re.compile(r'^.\d+$')

# Bot information
SESSION = environ.get('SESSION', 'ChessCoursesBot')
API_ID = int(environ.get('API_ID', ''))
API_HASH = environ.get('API_HASH', '')
BOT_TOKEN = environ.get('BOT_TOKEN', "")

# Start message images - add your banner images URLs here
PICS = (environ.get('PICS', 'https://example.com/chess_banner.jpg')).split()

# Admins & Users
ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '').split()]
auth_users = [int(user) if id_pattern.search(user) else user for user in environ.get('AUTH_USERS', '').split()]
AUTH_USERS = (auth_users + ADMINS) if auth_users else []
OWNER_USERNAME = environ.get('OWNER_USERNAME', 'your_username') # Placeholder for owner's Telegram username

# Bot activity logger
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', ''))

# Private channel where admin uploads courses
COURSE_CHANNEL = [int(ch) if id_pattern.search(ch) else ch for ch in environ.get('COURSE_CHANNEL', '').split()]

# Public announcement channel
PUBLIC_CHANNEL = environ.get('PUBLIC_CHANNEL', '')
AUTH_CHANNEL = int(PUBLIC_CHANNEL) if PUBLIC_CHANNEL and id_pattern.search(PUBLIC_CHANNEL) else None

# Support group where users can ask questions
SUPPORT_CHAT_ID = environ.get('SUPPORT_CHAT_ID', '')
SUPPORT_CHAT_ID = int(SUPPORT_CHAT_ID) if SUPPORT_CHAT_ID and id_pattern.search(SUPPORT_CHAT_ID) else None

# MongoDB information
DATABASE_URI = environ.get('DATABASE_URI', "")
DATABASE_NAME = environ.get('DATABASE_NAME', "chess_courses_bot")
COURSES_COLLECTION = environ.get('COURSES_COLLECTION', 'courses')
FILES_COLLECTION = environ.get('FILES_COLLECTION', 'course_files')

# Multiple database support
MULTI_DB_ENABLED = environ.get('MULTI_DB_ENABLED', 'False').lower() == 'true'
FALLBACK_DATABASE_URI = environ.get('FALLBACK_DATABASE_URI', '')

# URL Shortener
SHORTENER_ENABLED = environ.get('SHORTENER_ENABLED', 'False').lower() == 'true'
SHORTENER_API = environ.get('SHORTENER_API', '')
SHORTENER_DOMAIN = environ.get('SHORTENER_DOMAIN', '')
SHORTENER_API_KEY = environ.get('SHORTENER_API_KEY', '')

# Token Verification
TOKEN_VERIFICATION_ENABLED = environ.get('TOKEN_VERIFICATION_ENABLED', 'False').lower() == 'true'
TOKEN_COLLECTION = environ.get('TOKEN_COLLECTION', 'verification_tokens')

# Premium Features
PREMIUM_ENABLED = environ.get('PREMIUM_ENABLED', 'False').lower() == 'true'
REFER_SYSTEM_ENABLED = environ.get('REFER_SYSTEM_ENABLED', 'False').lower() == 'true'

# Tutorial Button
TUTORIAL_BUTTON_ENABLED = environ.get('TUTORIAL_BUTTON_ENABLED', 'True').lower() == 'true'
TUTORIAL_BUTTON_URL = environ.get('TUTORIAL_BUTTON_URL', '')

# Bot settings
AUTO_DELETE = environ.get('AUTO_DELETE_ENABLED', 'True').lower() == 'true'
PROTECT_CONTENT = environ.get('PROTECT_CONTENT', 'False').lower() == 'true'
PORT = environ.get("PORT", "8080")
CUSTOM_FILE_CAPTION = environ.get("CUSTOM_FILE_CAPTION", "{file_name}")

# Force subscribe settings - if you want users to subscribe before downloading
FORCE_SUB = environ.get('FORCE_SUB', 'False').lower() == 'true'
AUTO_SEND_AFTER_SUBSCRIBE = environ.get('AUTO_SEND_AFTER_SUBSCRIBE', 'True').lower() == 'true'

# Links
SUPPORT_LINK = environ.get('SUPPORT_LINK', 'https://t.me/your_support_group')
UPDATES_LINK = environ.get('UPDATES_LINK', 'https://t.me/your_updates_channel')
OWNER_LINK = environ.get('OWNER_LINK', 'https://t.me/your_username')

# Heroku settings
if 'DYNO' in environ:
    ON_HEROKU = True
    URL = environ.get("URL", "")
else:
    ON_HEROKU = False 