import discord
from discord.ext import commands
import sys
import os
import asyncio
import sqlite3
from .embed_utils import make_embed, success_embed, error_embed, Colors

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))


def is_dev_or_owner():
    async def predicate(ctx):
        config = getattr(ctx.bot, 'config', {})
        ids = set(config.get('BOT_OWNERS', []) + config.get('BOT_DEVELOPERS', []))
        return ctx.author.id in ids or await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


class BotManagement(commands.Cog):
    """Bot management commands for owners and developers."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["die", "exit", "quit"])
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Shut down the bot."""
        embed = make_embed(
            title="\U0001f6d1 Shutting Down",
            description="The bot is going offline...",
            color=Colors.ERROR, ctx=ctx
        )
        await ctx.send(embed=embed)
        await self.bot.close()

    @commands.command(aliases=["reboot"])
    @is_dev_or_owner()
    async def restart(self, ctx):
        """Restart the bot."""
        embed = make_embed(
            title="\U0001f504 Restarting",
            description=f"Restart initiated by {ctx.author.mention}...",
            color=Colors.WARNING, ctx=ctx
        )
        await ctx.send(embed=embed)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.command(aliases=["syncslash"])
    @is_dev_or_owner()
    async def sync(self, ctx):
        """Sync slash commands globally."""
        msg = await ctx.send(embed=make_embed(description="\u23f3 Syncing commands...", color=Colors.INFO, ctx=ctx))
        try:
            synced = await self.bot.tree.sync()
            await msg.edit(embed=success_embed(f"Synced **{len(synced)}** commands globally.", ctx))
        except Exception as e:
            await msg.edit(embed=error_embed(f"Sync failed: {e}", ctx))

    @commands.command(aliases=["syncguild"])
    @is_dev_or_owner()
    async def synchere(self, ctx):
        """Sync slash commands to this server only."""
        self.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await self.bot.tree.sync(guild=ctx.guild)
        await ctx.send(embed=success_embed(f"Synced **{len(synced)}** commands to this server.", ctx))

    @commands.command()
    @is_dev_or_owner()
    async def load(self, ctx, extension: str):
        """Load a cog."""
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            await ctx.send(embed=success_embed(f"Loaded `{extension}`.", ctx))
        except Exception as e:
            await ctx.send(embed=error_embed(f"Failed: {e}", ctx))

    @commands.command()
    @is_dev_or_owner()
    async def unload(self, ctx, extension: str):
        """Unload a cog."""
        try:
            await self.bot.unload_extension(f"cogs.{extension}")
            await ctx.send(embed=success_embed(f"Unloaded `{extension}`.", ctx))
        except Exception as e:
            await ctx.send(embed=error_embed(f"Failed: {e}", ctx))

    @commands.command()
    @is_dev_or_owner()
    async def reload(self, ctx, extension: str):
        """Reload a cog."""
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await ctx.send(embed=success_embed(f"Reloaded `{extension}`.", ctx))
        except Exception as e:
            await ctx.send(embed=error_embed(f"Failed: {e}", ctx))

    @commands.command(aliases=["reloadall"])
    @is_dev_or_owner()
    async def reloadcogs(self, ctx):
        """Reload all loaded cogs."""
        reloaded = []
        failed = []
        for ext in list(self.bot.extensions):
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(ext.split('.')[-1])
            except Exception as e:
                failed.append(f"{ext}: {e}")
        embed = make_embed(title="\U0001f504 Cogs Reloaded", color=Colors.SUCCESS, ctx=ctx)
        embed.add_field(name="\u2705 Reloaded", value=", ".join(reloaded) or "None", inline=False)
        if failed:
            embed.add_field(name="\u274c Failed", value="\n".join(failed), inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["servers", "guilds"])
    @is_dev_or_owner()
    async def serverlist(self, ctx):
        """Show all servers the bot is in."""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        desc = ""
        for i, g in enumerate(guilds[:20]):
            desc += f"`{i+1}.` **{g.name}** \u2014 `{g.member_count}` members (`{g.id}`)\n"
        embed = make_embed(
            title=f"\U0001f5c2\ufe0f Servers ({len(self.bot.guilds)})",
            description=desc or "No servers.",
            color=Colors.INFO, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.command()
    @is_dev_or_owner()
    async def serverdetails(self, ctx, server_id: int):
        """Show details about a specific server."""
        guild = self.bot.get_guild(server_id)
        if not guild:
            return await ctx.send(embed=error_embed(f"Not in a server with ID `{server_id}`.", ctx))
        owner = guild.owner or await self.bot.fetch_user(guild.owner_id)
        embed = make_embed(
            title=f"\U0001f3e0 {guild.name}",
            color=Colors.INFO, ctx=ctx,
            thumbnail=guild.icon.url if guild.icon else None
        )
        embed.add_field(name="ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Owner", value=f"{owner}", inline=True)
        embed.add_field(name="Members", value=f"`{guild.member_count}`", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Boosts", value=f"`{guild.premium_subscription_count}`", inline=True)
        embed.add_field(name="Channels", value=f"`{len(guild.channels)}`", inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    @is_dev_or_owner()
    async def forceremove(self, ctx, server_id: int):
        """Force the bot to leave a server."""
        guild = self.bot.get_guild(server_id)
        if not guild:
            return await ctx.send(embed=error_embed(f"Not in server `{server_id}`.", ctx))
        name = guild.name
        await guild.leave()
        await ctx.send(embed=success_embed(f"Left **{name}**.", ctx))

    @commands.command()
    @is_dev_or_owner()
    async def setstatus(self, ctx, status_type: str, *, text: str):
        """Change the bot's status. Types: playing, watching, listening, streaming, competing."""
        types = {
            'playing': discord.ActivityType.playing,
            'watching': discord.ActivityType.watching,
            'listening': discord.ActivityType.listening,
            'streaming': discord.ActivityType.streaming,
            'competing': discord.ActivityType.competing,
        }
        atype = types.get(status_type.lower())
        if not atype:
            return await ctx.send(embed=error_embed(f"Invalid type. Use: {', '.join(types.keys())}", ctx))
        activity = discord.Activity(type=atype, name=text)
        await self.bot.change_presence(activity=activity)
        await ctx.send(embed=success_embed(f"Status set to **{status_type}** `{text}`.", ctx))

    @commands.command()
    @is_dev_or_owner()
    async def announce(self, ctx, *, message: str):
        """Send an announcement to the current channel as the bot."""
        embed = make_embed(
            title="\U0001f4e2 Announcement",
            description=message,
            color=Colors.BLURPLE,
            footer=f"From {ctx.author.display_name}"
        )
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    @commands.command()
    @is_dev_or_owner()
    async def dm(self, ctx, user: discord.User, *, message: str):
        """DM a user as the bot."""
        try:
            embed = make_embed(
                title="\U0001f4ec Message from Project SHDW",
                description=message,
                color=Colors.PURPLE,
                footer=f"Sent by {ctx.author.display_name}"
            )
            await user.send(embed=embed)
            await ctx.send(embed=success_embed(f"DM sent to **{user}**.", ctx))
        except Exception as e:
            await ctx.send(embed=error_embed(f"Failed to DM: {e}", ctx))

    @commands.command()
    @is_dev_or_owner()
    async def cogs(self, ctx):
        """List all loaded cogs."""
        cog_list = "\n".join(f"\u2022 `{name}`" for name in self.bot.cogs)
        embed = make_embed(
            title=f"\U0001f9e9 Loaded Cogs ({len(self.bot.cogs)})",
            description=cog_list or "No cogs loaded.",
            color=Colors.INFO, ctx=ctx
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(BotManagement(bot))
