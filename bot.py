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
        temp.BOT = self
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        
        print(f"Bot Started as {me.first_name}")
        
        # Load banned users and chats
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        
        # Send startup message to log channel
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
        start_msg = f"<b>✅ Chess Courses Bot Started!\n\n⏰ Time: {time_str}</b>"
        
        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=start_msg)
        except Exception as e:
            print(f"Error sending startup message: {e}")
            print("Make sure the bot is an admin in the LOG_CHANNEL with send message permission")
        
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

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped!")

bot = Bot()

async def main_start():
    # Start the web server first, or concurrently
    # The PORT variable is imported from info.py
    # Convert PORT to int, as it's read as a string from environ
    web_server_port = int(environ.get("PORT", "8080")) # Ensure PORT is an int
    
    # It's better to run the web server as a background task
    # so it doesn't block the bot's startup or other asyncio tasks.
    # However, for simplicity and to ensure it starts before idle(),
    # we can await its start here if it's quick.
    # For robust applications, consider asyncio.create_task for the web server
    # and manage its lifecycle.
    
    # Start web server
    asyncio.create_task(start_web_server(port=web_server_port)) # Run web server concurrently

    await bot.start() # Start the Pyrogram bot
    print("Pyrogram Bot and Web Server should be running.")
    await idle() # Keep the bot running

if __name__ == "__main__":
    try:
        loop.run_until_complete(main_start())
    except KeyboardInterrupt:
        print("Bot Stopped by KeyboardInterrupt!")
    finally:
        if loop.is_running():
            loop.run_until_complete(bot.stop())
        print("Cleanup finished.") 