import discord
from discord.ext import commands
import os
import sqlite3
from .embed_utils import make_embed, error_embed, Colors

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))


class Leveling(commands.Cog):
    """XP and leveling system for servers and globally."""
    def __init__(self, bot):
        self.bot = bot
        self._cooldowns = {}

    def _get_settings(self, guild_id):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT leveling_xp_per_message, leveling_channel_id, leveling_message FROM server_settings WHERE server_id = ?", (guild_id,))
        row = c.fetchone()
        conn.close()
        return row or (10, None, None)

    def _add_xp(self, guild_id, user_id, xp_amount):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Server leveling
        c.execute("INSERT OR IGNORE INTO server_leveling (server_id, user_id, xp, level) VALUES (?, ?, 0, 1)", (guild_id, user_id))
        c.execute("UPDATE server_leveling SET xp = xp + ? WHERE server_id = ? AND user_id = ?", (xp_amount, guild_id, user_id))
        c.execute("SELECT xp, level FROM server_leveling WHERE server_id = ? AND user_id = ?", (guild_id, user_id))
        xp, level = c.fetchone()
        # Global leveling
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        c.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (xp_amount, user_id))

        # Level formula: xp needed = 100 * level^1.5
        xp_needed = int(100 * (level ** 1.5))
        leveled_up = False
        new_level = level
        while xp >= xp_needed:
            new_level += 1
            xp -= xp_needed
            xp_needed = int(100 * (new_level ** 1.5))
            leveled_up = True

        if leveled_up:
            c.execute("UPDATE server_leveling SET level = ?, xp = ? WHERE server_id = ? AND user_id = ?", (new_level, xp, guild_id, user_id))
            # Update global level too
            c.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
            g_xp, g_level = c.fetchone()
            g_needed = int(100 * (g_level ** 1.5))
            while g_xp >= g_needed:
                g_level += 1
                g_xp -= g_needed
                g_needed = int(100 * (g_level ** 1.5))
            c.execute("UPDATE users SET level = ?, xp = ? WHERE user_id = ?", (g_level, g_xp, user_id))

        conn.commit()
        conn.close()
        return new_level if leveled_up else None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        # Simple cooldown: 1 XP event per 5 seconds per user
        import time
        key = (message.guild.id, message.author.id)
        now = time.time()
        if key in self._cooldowns and now - self._cooldowns[key] < 5:
            return
        self._cooldowns[key] = now

        xp_per_msg, level_ch_id, level_msg = self._get_settings(message.guild.id)
        xp_gain = xp_per_msg if xp_per_msg else 10
        new_level = self._add_xp(message.guild.id, message.author.id, xp_gain)

        if new_level:
            channel = message.channel
            if level_ch_id:
                ch = message.guild.get_channel(level_ch_id)
                if ch:
                    channel = ch

            if level_msg:
                text = level_msg.replace("{member}", message.author.mention).replace("{level}", str(new_level))
                try:
                    await channel.send(text)
                except Exception:
                    pass
            else:
                embed = make_embed(
                    title="\U0001f31f Level Up!",
                    description=f"\U0001f389 {message.author.mention} reached **Level {new_level}**!",
                    color=Colors.GOLD,
                    thumbnail=message.author.display_avatar.url
                )
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass

    @commands.hybrid_command(aliases=["xp", "lvl", "rank"])
    async def level(self, ctx, member: discord.Member = None):
        """Check your or someone's level and XP."""
        member = member or ctx.author
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT xp, level FROM server_leveling WHERE server_id = ? AND user_id = ?", (ctx.guild.id, member.id))
        row = c.fetchone()
        # Get rank
        c.execute("SELECT COUNT(*) FROM server_leveling WHERE server_id = ? AND (level > COALESCE((SELECT level FROM server_leveling WHERE server_id = ? AND user_id = ?), 0) OR (level = COALESCE((SELECT level FROM server_leveling WHERE server_id = ? AND user_id = ?), 0) AND xp > COALESCE((SELECT xp FROM server_leveling WHERE server_id = ? AND user_id = ?), 0)))",
                  (ctx.guild.id, ctx.guild.id, member.id, ctx.guild.id, member.id, ctx.guild.id, member.id))
        rank = c.fetchone()[0] + 1
        conn.close()

        if not row:
            return await ctx.send(embed=error_embed(f"{member.display_name} hasn't earned any XP yet.", ctx))

        xp, level = row
        xp_needed = int(100 * (level ** 1.5))
        progress = int((xp / xp_needed) * 20) if xp_needed > 0 else 0
        bar = "\u2588" * progress + "\u2591" * (20 - progress)

        embed = make_embed(
            title=f"\U0001f4ca {member.display_name}'s Level",
            color=Colors.PURPLE, ctx=ctx,
            thumbnail=member.display_avatar.url
        )
        embed.add_field(name="\U0001f3c5 Rank", value=f"`#{rank}`", inline=True)
        embed.add_field(name="\U0001f4c8 Level", value=f"`{level}`", inline=True)
        embed.add_field(name="\u2728 XP", value=f"`{xp}/{xp_needed}`", inline=True)
        embed.add_field(name="Progress", value=f"```\n[{bar}]\n```", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["lb", "top"])
    async def leaderboard(self, ctx):
        """Show the server XP leaderboard."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, xp, level FROM server_leveling WHERE server_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (ctx.guild.id,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=error_embed("No one has earned XP yet.", ctx))

        medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
        desc = ""
        for i, (uid, xp, level) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            desc += f"{medal} <@{uid}> \u2014 Level **{level}** ({xp} XP)\n"

        embed = make_embed(
            title=f"\U0001f3c6 {ctx.guild.name} \u2014 Leaderboard",
            description=desc, color=Colors.GOLD, ctx=ctx,
            thumbnail=ctx.guild.icon.url if ctx.guild.icon else None
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["glevel", "gxp", "glvl"])
    async def globallevel(self, ctx, member: discord.Member = None):
        """Check your global level across all servers."""
        member = member or ctx.author
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT xp, level FROM users WHERE user_id = ?", (member.id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return await ctx.send(embed=error_embed(f"{member.display_name} has no global level data.", ctx))
        xp, level = row
        xp_needed = int(100 * (level ** 1.5))
        embed = make_embed(
            title=f"\U0001f30d {member.display_name}'s Global Level",
            color=Colors.BLURPLE, ctx=ctx,
            thumbnail=member.display_avatar.url
        )
        embed.add_field(name="\U0001f4c8 Level", value=f"`{level}`", inline=True)
        embed.add_field(name="\u2728 XP", value=f"`{xp}/{xp_needed}`", inline=True)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leveling(bot))
