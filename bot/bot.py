import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime

# Load config
with open(os.path.join(os.path.dirname(__file__), 'config.json')) as f:
    config = json.load(f)

# Cog loading config
COG_BLACKLIST = config.get('COG_BLACKLIST', [])
LOAD_ALL_COGS = config.get('LOAD_ALL_COGS', True)
COG_WHITELIST = config.get('COG_WHITELIST', [])
CUSTOM_COGS_AUTOMATICALLY_LOADED = config.get('CUSTOM_COGS_AUTOMATICALLY_LOADED', True)
CUSTOM_COGS_BLACKLIST = config.get('CUSTOM_COGS_BLACKLIST', [])


async def load_cogs(bot):
    cogs_dir = Path(__file__).parent / 'cogs'
    loaded = []
    for file in sorted(cogs_dir.glob('*.py')):
        if file.name.startswith('_') or file.stem == 'embed_utils':
            continue
        if file.stem in COG_BLACKLIST:
            continue
        cog_name = f"cogs.{file.stem}"
        if LOAD_ALL_COGS or file.stem in COG_WHITELIST:
            try:
                await bot.load_extension(cog_name)
                loaded.append(file.stem)
            except Exception as e:
                print(f'  \u274c Failed to load {cog_name}: {e}')
    print(f'  \u2705 Loaded {len(loaded)} cogs: {", ".join(loaded)}')

    # Custom cogs
    if CUSTOM_COGS_AUTOMATICALLY_LOADED:
        custom_dir = Path(__file__).parent / 'custom cogs'
        if custom_dir.exists():
            for file in custom_dir.glob('*.py'):
                if file.name.startswith('_') or file.stem in CUSTOM_COGS_BLACKLIST:
                    continue
                try:
                    await bot.load_extension(f"custom cogs.{file.stem}")
                except Exception as e:
                    print(f'  \u274c Failed to load custom cog {file.stem}: {e}')


def get_prefix(bot, message):
    prefix = config.get('BOT_PREFIX', '.').strip()
    if message.guild:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'database.db')
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            # Check user personal prefix
            c.execute("SELECT personal_prefix FROM users WHERE user_id = ?", (message.author.id,))
            row = c.fetchone()
            if row and row[0]:
                prefix = row[0]
            else:
                # Check server prefix
                c.execute("SELECT prefix FROM server_settings WHERE server_id = ?", (message.guild.id,))
                row = c.fetchone()
                if row and row[0]:
                    prefix = row[0]
            conn.close()
        except Exception:
            pass
    return commands.when_mentioned_or(prefix)(bot, message)


def get_presence():
    activity_type = config.get('BOT_ACTIVITY_TYPE', 'playing').lower()
    activity_name = config.get('BOT_ACTIVITY', 'with shadows')
    status_str = config.get('BOT_STATUS', 'dnd').lower()

    activity_map = {
        'playing': lambda: discord.Game(name=activity_name),
        'streaming': lambda: discord.Streaming(name=activity_name, url=config.get('BOT_STREAMING_URL', 'https://twitch.tv/')),
        'listening': lambda: discord.Activity(type=discord.ActivityType.listening, name=activity_name),
        'watching': lambda: discord.Activity(type=discord.ActivityType.watching, name=activity_name),
        'competing': lambda: discord.Activity(type=discord.ActivityType.competing, name=activity_name),
        'custom': lambda: discord.CustomActivity(name=activity_name),
        'none': lambda: None,
    }
    activity = activity_map.get(activity_type, activity_map['playing'])()

    status_map = {
        'online': discord.Status.online,
        'idle': discord.Status.idle,
        'dnd': discord.Status.dnd,
        'invisible': discord.Status.invisible,
    }
    status = status_map.get(status_str, discord.Status.online)
    return activity, status


intents = discord.Intents.all()


async def start_bot(token):
    bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)
    bot.config = config
    bot.start_time = datetime.utcnow()
    bot.snipes = {}
    bot.edit_snipes = {}
    bot.afk_users = {}

    @bot.event
    async def on_ready():
        print(f'\n\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510')
        print(f'\u2502  Project SHDW v2.0                     \u2502')
        print(f'\u2502  Logged in as {bot.user}')
        print(f'\u2502  Servers: {len(bot.guilds)} | Users: {len(bot.users)}')
        print(f'\u2502  Prefix: {config.get("BOT_PREFIX", ".")}')
        print(f'\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518\n')
        await load_cogs(bot)
        activity, status = get_presence()
        await bot.change_presence(activity=activity, status=status)

    @bot.event
    async def on_message_delete(message):
        if message.author.bot:
            return
        bot.snipes[message.channel.id] = {
            'author': message.author,
            'content': message.content,
            'time': datetime.utcnow(),
            'attachments': [a.url for a in message.attachments]
        }

    @bot.event
    async def on_message_edit(before, after):
        if before.author.bot:
            return
        bot.edit_snipes[before.channel.id] = {
            'author': before.author,
            'before': before.content,
            'after': after.content,
            'time': datetime.utcnow()
        }

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        # AFK check
        if message.author.id in bot.afk_users:
            del bot.afk_users[message.author.id]
            try:
                await message.channel.send(
                    f"Welcome back {message.author.mention}, I removed your AFK.",
                    delete_after=5
                )
            except Exception:
                pass
        # Check if mentioned users are AFK
        for user in message.mentions:
            if user.id in bot.afk_users:
                afk_data = bot.afk_users[user.id]
                try:
                    await message.channel.send(
                        f"{user.display_name} is AFK: **{afk_data['reason']}** \u2014 <t:{int(afk_data['time'].timestamp())}:R>",
                        delete_after=8
                    )
                except Exception:
                    pass
        await bot.process_commands(message)

    await bot.start(token)


async def main():
    tokens = config.get('DISCORD_BOT_TOKEN')
    if isinstance(tokens, str):
        tokens = [tokens] if tokens else []
    if not tokens:
        raise ValueError("No bot token in config.json")
    await asyncio.gather(*(start_bot(t) for t in tokens))


if __name__ == "__main__":
    asyncio.run(main())
