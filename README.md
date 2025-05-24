# Chess Courses Bot

A Telegram bot designed to help share and manage chess courses. This bot allows admins to add multi-file chess courses to a private channel and then automatically share them with users through a public announcement channel.

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/yourusername/ChessCoursesBot)
[![Deploy on Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## Features

- **Multi-file Course Management**: Group related chess course files together
- **Admin Workflow**: Simplified process for adding new courses with banner images using **Telegram Message Links**
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
- **Message Link Based Course Creation**: Add courses using message links instead of forwarding files (Now the primary method)

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

## Command Reference

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and see welcome message |
| `/help` | Show help information with available commands |
| `/about` | Show information about the bot |
| `/search [query]` | Search for courses by name |
| `/token [code]` | Verify access using a verification token |
| `/premium` | Show premium status or premium plan information |

### Admin Commands

#### Basic Administration
| Command | Description |
|---------|-------------|
| `/stats` | View bot statistics including user count and storage usage |
| `/broadcast [message]` | Send a message to all bot users |

#### Course Management
| Command | Description |
|---------|-------------|
| `/addcourse` | Start guided process to add a new course using Telegram message links. This is the primary method. |
| `/done` | (Used during `/addcourse`) Complete link collection when adding a course via message links. |
| `/skip` | (Used during `/addcourse`) Skip adding a banner image during course creation. |
| `/deletecourse [course_id]` | Delete an entire course and its associated files (use with caution!). |

#### Token System
| Command | Description |
|---------|-------------|
| `/gentoken [max_uses] [days]` | Generate a new verification token with optional max uses and expiry |
| `/mytokens` | List all tokens created by you |
| `/tokeninfo [code]` | Get detailed information about a specific token |
| `/deltoken [code]` | Delete a verification token |
| `/disabletoken [code]` | Disable a token without deleting it |
| `/toggleverification` | Toggle whether token verification is required |

#### Premium User Management
| Command | Description |
|---------|-------------|
| `/setpremium [user_id/username] [days]` | Grant premium status to a user for specified days |
| `/removepremium [user_id/username]` | Remove premium status from a user |
| `/premiumusers` | List all users with premium status |
| `/checkpremium [user_id/username]` | Check premium status of a specific user |

## Usage

### For Admins

1. **Adding a Course (Recommended Method: Message Links)**:
   - Use the `/addcourse` command to start the process.
   - The bot will prompt you for the **course name**.
   - Then, send the **Telegram message links** for all files belonging to the course. 
     - You can send one link per message, or multiple links in a single message (each on a new line).
     - **Link Format:** `https://t.me/c/CHANNEL_ID/MESSAGE_ID` (for private/supergroup channels) or `https://t.me/USERNAME/MESSAGE_ID` (for public channels).
     - Ensure the bot has permission to access messages from the source channel(s).
   - Type `/done` when you have finished sending all the message links.
   - The bot will then ask if you want to add a **banner image**. You can send an image or type `/skip`.
   - Finally, review the course details and confirm to publish it. The bot will announce it if configured.

2. **Managing Tokens**:
   - Generate tokens with: `/gentoken [max_uses] [days]`
   - View your tokens with: `/mytokens`
   - Check token details with: `/tokeninfo [code]`
   - Delete or disable tokens with: `/deltoken [code]` or `/disabletoken [code]`

3. **Managing Premium Users**:
   - Set premium status: `/setpremium [user_id] 30` (for 30 days)
   - Remove premium: `/removepremium [user_id]`
   - View all premium users: `/premiumusers`
   - Check a specific user: `/checkpremium [user_id]`

### For Users

1. **Finding Courses**:
   - Use inline search by typing `@YourBotUsername course_name`
   - Use `/search [query]` to find courses by name
   - Browse the public announcement channel
   - Click "Download Now" on any course to get all files

2. **Using Token Verification**:
   - Receive a token from an admin
   - Verify access with: `/token YOUR_TOKEN_HERE`

3. **Premium Features**:
   - Check your premium status with `/premium`
   - Contact an admin to purchase premium access
   - Premium users get access to exclusive courses and features

## Project Structure

- `bot.py` - Main bot file
- `info.py` - Configuration settings
- `Script.py` - Message templates
- `database/` - Database operations
  - `courses_db.py` - Course database operations
  - `users_chats_db.py` - User tracking
  - `token_db.py` - Token verification system
  - `url_shortener.py` - URL shortener utilities
  - `multi_db.py` - Multiple database support
- `plugins/` - Bot functionality
  - `commands.py` - Command handlers
  - `course_manager.py` - Course upload workflow
  - `inline.py` - Inline search
  - `token_commands.py` - Token verification commands
  - `premium.py` - Premium user management

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributions

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [Pyrogram](https://github.com/pyrogram/pyrogram) - Telegram API framework
- Based on an idea to simplify chess course sharing 