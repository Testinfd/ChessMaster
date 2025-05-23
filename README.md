# Chess Courses Bot

A Telegram bot designed to help share and manage chess courses. This bot allows admins to add multi-file chess courses to a private channel and then automatically share them with users through a public announcement channel.

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/yourusername/ChessCoursesBot)
[![Deploy on Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## Features

- **Multi-file Course Management**: Group related chess course files together
- **Admin Workflow**: Simplified process for adding new courses with banner images
- **Public Announcements**: Automatic posts to a public channel with download buttons
- **Inline Search**: Users can search for courses directly within Telegram
- **Deep Linking**: One-click download process for users
- **URL Shortener Integration**: Support for custom URL shorteners
- **Token Verification**: Restrict access with verification tokens
- **Auto-Delete**: Auto-delete files after a specific time
- **Tutorial Button**: Custom tutorial button for course files
- **Premium Features**: Premium user system with referrals
- **Multiple Database Support**: Fallback database for redundancy
- **Force Subscribe**: Require users to join channels before downloading
- **Auto-File Send**: Automatically send files when a user subscribes

## Setup

### Prerequisites

- Python 3.7+
- MongoDB database
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Two Telegram channels:
  - Private channel for uploading course files
  - Public announcement channel for course listings

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ChessCoursesBot.git
   cd ChessCoursesBot
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following configuration:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   DATABASE_URI=your_mongodb_uri
   ADMINS=your_user_id,another_admin_id
   LOG_CHANNEL=your_log_channel_id
   COURSE_CHANNEL=your_private_course_channel_id
   PUBLIC_CHANNEL=your_public_announcement_channel
   ```

4. Start the bot:
   ```
   python bot.py
   ```

### Docker Deployment

You can also run the bot using Docker:

1. Build the Docker image:
   ```
   docker build -t chess-courses-bot .
   ```

2. Run the container:
   ```
   docker run -d --name chess-courses-bot --env-file .env chess-courses-bot
   ```

Or using docker-compose:

```
docker-compose up -d
```

## Advanced Features Configuration

### URL Shortener

Enable URL shortening for deeplinks by adding these to your `.env`:

```
SHORTENER_ENABLED=True
SHORTENER_API=https://api.example.com/shorten
SHORTENER_API_KEY=your_api_key
SHORTENER_DOMAIN=yourdomain.com
```

### Token Verification

Restrict access with verification tokens:

```
TOKEN_VERIFICATION_ENABLED=True
```

Use admin commands:
- `/gentoken` - Generate new verification tokens
- `/mytokens` - List your tokens
- `/revoketoken` - Revoke a token

Users must verify with:
- `/verify TOKEN` - Verify access with a token

### Force Subscribe

Require users to join channels before downloading:

```
FORCE_SUB=True
AUTO_SEND_AFTER_SUBSCRIBE=True
```

### Multiple Database Support

Add database redundancy:

```
MULTI_DB_ENABLED=True
FALLBACK_DATABASE_URI=mongodb://username:password@backup.mongodb.com
```

### Tutorial Button

Add custom tutorial button to files:

```
TUTORIAL_BUTTON_ENABLED=True
TUTORIAL_BUTTON_URL=https://example.com/tutorial
```

### Premium Features

Enable premium features:

```
PREMIUM_ENABLED=True
REFER_SYSTEM_ENABLED=True
```

## Usage

### For Admins

1. **Adding a Course**:
   - Upload all course files to your private channel
   - Forward the last file to the bot (adding course name in caption)
   - The bot will ask you to confirm details and add a banner image
   - After confirmation, the bot will post to the public channel

   Alternatively, use the `/course` command to start the guided process.

2. **Admin Commands**:
   - `/start` - Start the bot
   - `/course` - Start adding a new course
   - `/stats` - View bot statistics
   - `/broadcast` - Send message to all users
   - `/gentoken` - Generate verification tokens
   - `/mytokens` - List your tokens
   - `/revoketoken` - Revoke a token

### For Users

1. **Finding Courses**:
   - Use inline search by typing `@YourBotUsername course_name`
   - Browse the public announcement channel
   - Click "Download Now" on any course to get all files

2. **User Commands**:
   - `/start` - Start the bot
   - `/help` - Show help information
   - `/about` - Show bot information
   - `/verify` - Verify with a token (if enabled)

## Project Structure

- `bot.py` - Main bot file
- `info.py` - Configuration settings
- `Script.py` - Message templates
- `database/` - Database operations
  - `courses_db.py` - Course database operations
  - `users_chats_db.py` - User tracking
  - `token_verification.py` - Token verification system
  - `url_shortener.py` - URL shortener utilities
  - `multi_db.py` - Multiple database support
- `plugins/` - Bot functionality
  - `commands.py` - Command handlers
  - `course_manager.py` - Course upload workflow
  - `inline.py` - Inline search
  - `token_commands.py` - Token verification commands

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributions

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [Pyrogram](https://github.com/pyrogram/pyrogram) - Telegram API framework
- Based on an idea to simplify chess course sharing 