import sys
import glob
import importlib
import importlib.util
import logging
import logging.config
import pytz
import asyncio
from pathlib import Path
from datetime import datetime
from os import environ

from aiohttp import web

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

from pyrogram import Client, idle
from database.users_chats_db import db
from info import *
from utils import temp

ppath = "plugins/*.py"
files = glob.glob(ppath)

loop = asyncio.get_event_loop()

# --- AIOHTTP Web Server Setup ---
async def handle_hello(request):
    """A simple handler to respond with Hello, World!."""
    logging.info("HTTP GET request received on /")
    return web.Response(text="Hello, World!")

async def start_web_server(port):
    app = web.Application()
    app.router.add_get("/", handle_hello)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    try:
        await site.start()
        logging.info(f"Web server started successfully on port {port}")
    except Exception as e:
        logging.error(f"Error starting web server: {e}")
        # Depending on the error, you might want to raise it or handle it
        # For now, just logging it.
# --- End AIOHTTP Web Server Setup ---

class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        if me:
            logging.info(f"Pyrogram client initialized. Bot ID: {me.id}, Username: @{me.username}")
            temp.BOT = self
            temp.ME = me.id
            temp.U_NAME = me.username
            temp.B_NAME = me.first_name
        else:
            logging.error("Failed to get bot details (self.get_me() returned None). Check API_ID, API_HASH, BOT_TOKEN.")
            # You might want to stop the bot here or handle this more gracefully
            return # Prevent further execution if bot details are not fetched
        
        print(f"Bot Started as {me.first_name}")
        
        # Load banned users and chats
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        
        # Load premium users if premium feature is enabled
        if PREMIUM_ENABLED:
            premium_users = await db.get_premium_users()
            temp.PREMIUM_USERS = [user["_id"] for user in premium_users]
            logging.info(f"Loaded {len(temp.PREMIUM_USERS)} premium users")
        
        # Send startup message to log channel
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        start_msg = f"<b>✅ Chess Courses Bot Started!\n\n⏰ Time: {time_str}</b>"
        
        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=start_msg)
            logging.info(f"Startup message sent to LOG_CHANNEL: {LOG_CHANNEL}")
        except Exception as e:
            # Log the error but continue bot operation
            logging.error(f"Failed to send startup message to LOG_CHANNEL ({LOG_CHANNEL}): {e}. The bot will continue to run.")
            # Optionally, print a less alarming message to console as well
            print(f"[Startup Log Error] Could not send message to LOG_CHANNEL {LOG_CHANNEL}. Check Render logs for details. Bot is continuing.")
        
        print("Loading plugins...")
        for name in files:
            with open(name) as a:
                patt = Path(a.name)
                plugin_name = patt.stem.replace(".py", "")
                plugins_dir = Path(f"plugins/{plugin_name}.py")
                import_path = f"plugins.{plugin_name}"
                
                spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
                load = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(load)
                
                sys.modules[f"plugins.{plugin_name}"] = load
                print(f"Successfully Imported {plugin_name}")
                
        print("Bot plugins loaded!")

    async def stop_custom(self, *args):
        logging.info("Executing custom stop actions...")
        await super().stop()
        logging.info("Pyrogram client stopped.")
        print("Bot Stopped Gracefully!")

bot = Bot()

async def main_start():
    web_server_port = int(environ.get("PORT", "8080"))
    # Start the web server as a background task
    web_task = asyncio.create_task(start_web_server(port=web_server_port))

    logging.info("Attempting to connect and start Pyrogram bot client...")
    try:
        await bot.start() # This starts the client and loads plugins as per __init__
        logging.info("Pyrogram bot client has started.")
        print("Pyrogram Bot and Web Server should be running.")
        await idle() # This keeps the bot running and processing updates
    except Exception as e:
        logging.error(f"An error occurred during bot startup or idle: {e}", exc_info=True)
    finally:
        logging.info("Bot idle() has been exited or an error occurred. Stopping bot...")
        await bot.stop_custom()
        if not web_task.done():
            web_task.cancel()
            try:
                await web_task
            except asyncio.CancelledError:
                logging.info("Web server task cancelled.")
        logging.info("Application shutdown complete.")

if __name__ == "__main__":
    try:
        loop.run_until_complete(main_start())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, initiating graceful shutdown...")
    # The finally block in main_start() will handle the shutdown
    print("Application has been shut down from __main__.") 