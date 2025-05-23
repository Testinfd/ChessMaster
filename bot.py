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

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

from pyrogram import Client, idle
from database.users_chats_db import db
from info import *
from utils import temp

ppath = "plugins/*.py"
files = glob.glob(ppath)

loop = asyncio.get_event_loop()

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
                
        print("Bot Started!")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped!")

bot = Bot()

async def start():
    await bot.start()
    await idle()

if __name__ == "__main__":
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        print("Bot Stopped!") 