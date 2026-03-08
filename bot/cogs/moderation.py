import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
import os
import sqlite3
from datetime import timedelta
from .embed_utils import make_embed, success_embed, error_embed, warning_embed, Colors


def is_dev_or_owner():
    async def predicate(ctx):
        config = getattr(ctx.bot, 'config', {})
        ids = set(config.get('BOT_OWNERS', []) + config.get('BOT_DEVELOPERS', []))
        return ctx.author.id in ids or await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, server_id INTEGER, user_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp TEXT)")
    return conn


class Moderation(commands.Cog):
    """Server moderation and management commands."""
    def __init__(self, bot):
        self.bot = bot

    # ── Kick / Ban / Unban ──────────────────────────────────

    @commands.hybrid_command()
    @has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server."""
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("You can't kick someone with an equal or higher role.", ctx))
        await member.kick(reason=f"{ctx.author}: {reason}")
        embed = make_embed(
            title="\U0001f462 Member Kicked",
            color=Colors.WARNING, ctx=ctx
        )
        embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member from the server."""
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("You can't ban someone with an equal or higher role.", ctx))
        await member.ban(reason=f"{ctx.author}: {reason}")
        embed = make_embed(
            title="\U0001f528 Member Banned",
            color=Colors.ERROR, ctx=ctx
        )
        embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)", inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason: str = "No reason provided"):
        """Unban a user by their ID."""
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
        await ctx.send(embed=success_embed(f"**{user}** has been unbanned.", ctx))

    @commands.hybrid_command()
    @has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban and immediately unban a member to delete their messages."""
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("You can't softban someone with an equal or higher role.", ctx))
        await member.ban(reason=f"Softban by {ctx.author}: {reason}", delete_message_days=7)
        await ctx.guild.unban(member, reason="Softban unban")
        embed = make_embed(
            title="\U0001f4a8 Member Softbanned",
            description=f"{member.mention} was softbanned (messages deleted).",
            color=Colors.WARNING, ctx=ctx
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)

    # ── Message Management ──────────────────────────────────

    @commands.hybrid_command(aliases=["purge", "prune"])
    @has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10):
        """Delete a number of messages from the channel."""
        if amount < 1 or amount > 500:
            return await ctx.send(embed=error_embed("Amount must be between 1 and 500.", ctx))
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(
            embed=success_embed(f"Deleted **{len(deleted) - 1}** messages.", ctx),
            delete_after=4
        )

    @commands.hybrid_command()
    @has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        """Clone the channel and delete the original (clears all messages)."""
        confirm_embed = make_embed(
            title="\u26a0\ufe0f Nuke Channel?",
            description=f"This will **delete** {ctx.channel.mention} and create a clone. All messages will be lost.\n\nReact with \u2705 to confirm.",
            color=Colors.ERROR, ctx=ctx
        )
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("\u2705")

        def check(r, u):
            return u == ctx.author and str(r.emoji) == "\u2705" and r.message.id == msg.id

        try:
            await self.bot.wait_for("reaction_add", check=check, timeout=15)
        except Exception:
            return await ctx.send(embed=warning_embed("Nuke cancelled.", ctx))

        new_channel = await ctx.channel.clone(reason=f"Nuked by {ctx.author}")
        await ctx.channel.delete()
        await new_channel.send(embed=make_embed(
            title="\U0001f4a5 Channel Nuked",
            description="This channel has been nuked and recreated.",
            color=Colors.ERROR
        ))

    # ── Channel Management ──────────────────────────────────

    @commands.hybrid_command(aliases=["slow"])
    @has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        """Set channel slowmode (0 to disable, max 21600)."""
        if seconds < 0 or seconds > 21600:
            return await ctx.send(embed=error_embed("Slowmode must be between 0 and 21600 seconds.", ctx))
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send(embed=success_embed("Slowmode disabled.", ctx))
        else:
            await ctx.send(embed=success_embed(f"Slowmode set to **{seconds}s**.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Lock a channel so members can't send messages."""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        embed = make_embed(
            title="\U0001f510 Channel Locked",
            description=f"{channel.mention} has been locked.",
            color=Colors.ERROR, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Unlock a channel so members can send messages."""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        embed = make_embed(
            title="\U0001f513 Channel Unlocked",
            description=f"{channel.mention} has been unlocked.",
            color=Colors.SUCCESS, ctx=ctx
        )
        await ctx.send(embed=embed)

    # ── Member Management ───────────────────────────────────

    @commands.hybrid_command()
    @has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: int, *, reason: str = "No reason provided"):
        """Timeout a member (duration in minutes)."""
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("Can't timeout someone with an equal or higher role.", ctx))
        await member.timeout(timedelta(minutes=duration), reason=f"{ctx.author}: {reason}")
        embed = make_embed(
            title="\u23f3 Member Timed Out",
            color=Colors.WARNING, ctx=ctx
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        """Remove a member's timeout."""
        await member.timeout(None, reason=f"Removed by {ctx.author}")
        await ctx.send(embed=success_embed(f"Removed timeout from {member.mention}.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Mute a member by giving them a Muted role."""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted", reason="Mute role created")
            for ch in ctx.guild.channels:
                await ch.set_permissions(mute_role, send_messages=False, speak=False, add_reactions=False)
        await member.add_roles(mute_role, reason=f"{ctx.author}: {reason}")
        embed = make_embed(title="\U0001f507 Member Muted", color=Colors.WARNING, ctx=ctx)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member by removing the Muted role."""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role or mute_role not in member.roles:
            return await ctx.send(embed=error_embed("That member isn't muted.", ctx))
        await member.remove_roles(mute_role, reason=f"Unmuted by {ctx.author}")
        await ctx.send(embed=success_embed(f"{member.mention} has been unmuted.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nickname: str = None):
        """Change a member's nickname (leave empty to reset)."""
        await member.edit(nick=nickname)
        if nickname:
            await ctx.send(embed=success_embed(f"Changed {member.mention}'s nickname to **{nickname}**.", ctx))
        else:
            await ctx.send(embed=success_embed(f"Reset {member.mention}'s nickname.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Add a role to a member."""
        if role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("You can't add a role higher than or equal to yours.", ctx))
        await member.add_roles(role, reason=f"Added by {ctx.author}")
        await ctx.send(embed=success_embed(f"Added {role.mention} to {member.mention}.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_roles=True)
    async def removerole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Remove a role from a member."""
        if role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("You can't remove a role higher than or equal to yours.", ctx))
        await member.remove_roles(role, reason=f"Removed by {ctx.author}")
        await ctx.send(embed=success_embed(f"Removed {role.mention} from {member.mention}.", ctx))

    # ── Warning System ──────────────────────────────────────

    @commands.hybrid_command()
    @has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member."""
        from datetime import datetime
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO warnings (server_id, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (ctx.guild.id, member.id, ctx.author.id, reason, datetime.utcnow().isoformat())
        )
        warn_id = c.lastrowid
        c.execute("SELECT COUNT(*) FROM warnings WHERE server_id = ? AND user_id = ?", (ctx.guild.id, member.id))
        total = c.fetchone()[0]
        conn.commit()
        conn.close()
        embed = make_embed(title="\u26a0\ufe0f Member Warned", color=Colors.WARNING, ctx=ctx)
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Warn ID", value=f"`#{warn_id}`", inline=True)
        embed.add_field(name="Total Warnings", value=f"`{total}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["warns", "infractions"])
    async def warnings(self, ctx, member: discord.Member = None):
        """View warnings for a member."""
        member = member or ctx.author
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, moderator_id, reason, timestamp FROM warnings WHERE server_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10", (ctx.guild.id, member.id))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return await ctx.send(embed=make_embed(description=f"{member.mention} has no warnings. \U0001f389", color=Colors.SUCCESS, ctx=ctx))
        desc = ""
        for warn_id, mod_id, reason, ts in rows:
            desc += f"**#{warn_id}** \u2014 <@{mod_id}>\n> {reason}\n> <t:{int(datetime.fromisoformat(ts).timestamp())}:R>\n\n"
        embed = make_embed(
            title=f"\u26a0\ufe0f Warnings for {member.display_name}",
            description=desc, color=Colors.WARNING, ctx=ctx,
            thumbnail=member.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["clearwarns", "delwarns"])
    @has_permissions(manage_messages=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member."""
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM warnings WHERE server_id = ? AND user_id = ?", (ctx.guild.id, member.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Cleared all warnings for {member.mention}.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_messages=True)
    async def delwarn(self, ctx, warn_id: int):
        """Delete a specific warning by ID."""
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM warnings WHERE id = ? AND server_id = ?", (warn_id, ctx.guild.id))
        if c.rowcount == 0:
            conn.close()
            return await ctx.send(embed=error_embed(f"Warning `#{warn_id}` not found.", ctx))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Deleted warning `#{warn_id}`.", ctx))

    # ── Server Settings ─────────────────────────────────────

    @commands.hybrid_command(aliases=["prefix"])
    @has_permissions(manage_guild=True)
    async def setprefix(self, ctx, prefix: str):
        """Set the server's command prefix."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET prefix = ? WHERE server_id = ?", (prefix, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Server prefix set to `{prefix}`.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_guild=True)
    async def setwelcomechannel(self, ctx, channel: discord.TextChannel):
        """Set the welcome channel."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET welcome_channel_id = ? WHERE server_id = ?", (channel.id, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Welcome channel set to {channel.mention}.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_guild=True)
    async def setwelcomemsg(self, ctx, *, message: str):
        """Set the welcome message. Use {member} for mention, {server} for server name."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET welcome_message = ? WHERE server_id = ?", (message, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed("Welcome message updated.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_guild=True)
    async def setlevelchannel(self, ctx, channel: discord.TextChannel):
        """Set the level-up announcement channel."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET leveling_channel_id = ? WHERE server_id = ?", (channel.id, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Level-up channel set to {channel.mention}.", ctx))

    @commands.hybrid_command()
    @has_permissions(manage_guild=True)
    async def setlevelmsg(self, ctx, *, message: str):
        """Set the level-up message. Use {member} and {level}."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET leveling_message = ? WHERE server_id = ?", (message, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed("Level-up message updated.", ctx))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
