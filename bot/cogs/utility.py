import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from .embed_utils import make_embed, success_embed, error_embed, Colors


class Utility(commands.Cog):
    """Utility and productivity commands."""
    def __init__(self, bot):
        self.bot = bot
        self._reminders = []

    # ── AFK ──────────────────────────────────────────────────

    @commands.hybrid_command()
    async def afk(self, ctx, *, reason: str = "AFK"):
        """Set yourself as AFK. People who ping you will be notified."""
        self.bot.afk_users[ctx.author.id] = {
            'reason': reason,
            'time': datetime.utcnow()
        }
        embed = make_embed(
            title="\U0001f4a4 AFK Set",
            description=f"{ctx.author.mention} is now AFK: **{reason}**",
            color=Colors.INFO, ctx=ctx
        )
        await ctx.send(embed=embed)

    # ── Snipe ────────────────────────────────────────────────

    @commands.hybrid_command()
    async def snipe(self, ctx):
        """Show the last deleted message in this channel."""
        data = self.bot.snipes.get(ctx.channel.id)
        if not data:
            return await ctx.send(embed=error_embed("Nothing to snipe.", ctx))
        embed = make_embed(
            title="\U0001f4a8 Sniped Message",
            description=data['content'] or "*No text content*",
            color=Colors.DARK, ctx=ctx
        )
        embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
        embed.add_field(name="Deleted", value=f"<t:{int(data['time'].timestamp())}:R>", inline=True)
        if data.get('attachments'):
            embed.add_field(name="Attachments", value="\n".join(data['attachments'][:3]), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["esnipe"])
    async def editsnipe(self, ctx):
        """Show the last edited message in this channel."""
        data = self.bot.edit_snipes.get(ctx.channel.id)
        if not data:
            return await ctx.send(embed=error_embed("Nothing to snipe.", ctx))
        embed = make_embed(
            title="\u270f\ufe0f Edit Sniped",
            color=Colors.DARK, ctx=ctx
        )
        embed.set_author(name=str(data['author']), icon_url=data['author'].display_avatar.url)
        embed.add_field(name="Before", value=data['before'][:1024] or "*empty*", inline=False)
        embed.add_field(name="After", value=data['after'][:1024] or "*empty*", inline=False)
        embed.add_field(name="Edited", value=f"<t:{int(data['time'].timestamp())}:R>", inline=True)
        await ctx.send(embed=embed)

    # ── Poll ─────────────────────────────────────────────────

    @commands.hybrid_command()
    async def poll(self, ctx, question: str, *, options: str = None):
        """Create a poll. Separate options with | (max 10). If no options, creates yes/no poll."""
        if options:
            opts = [o.strip() for o in options.split('|') if o.strip()][:10]
            if len(opts) < 2:
                return await ctx.send(embed=error_embed("Provide at least 2 options separated by `|`.", ctx))
            number_emojis = ["\u0031\ufe0f\u20e3", "\u0032\ufe0f\u20e3", "\u0033\ufe0f\u20e3", "\u0034\ufe0f\u20e3",
                            "\u0035\ufe0f\u20e3", "\u0036\ufe0f\u20e3", "\u0037\ufe0f\u20e3", "\u0038\ufe0f\u20e3",
                            "\u0039\ufe0f\u20e3", "\U0001f51f"]
            desc = "\n".join(f"{number_emojis[i]} {opt}" for i, opt in enumerate(opts))
            embed = make_embed(
                title=f"\U0001f4ca {question}",
                description=desc,
                color=Colors.BLURPLE, ctx=ctx
            )
            if ctx.interaction is None:
                try:
                    await ctx.message.delete()
                except Exception:
                    pass
            msg = await ctx.send(embed=embed)
            for i in range(len(opts)):
                await msg.add_reaction(number_emojis[i])
        else:
            embed = make_embed(
                title=f"\U0001f4ca {question}",
                description="\u2705 Yes \u2003\u2003\u274c No",
                color=Colors.BLURPLE, ctx=ctx
            )
            if ctx.interaction is None:
                try:
                    await ctx.message.delete()
                except Exception:
                    pass
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("\u2705")
            await msg.add_reaction("\u274c")

    # ── Remind ───────────────────────────────────────────────

    @commands.hybrid_command(aliases=["reminder", "remindme"])
    async def remind(self, ctx, time_str: str, *, message: str):
        """Set a reminder. Time format: 10s, 5m, 1h, 1d."""
        units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        if not time_str[-1] in units or not time_str[:-1].isdigit():
            return await ctx.send(embed=error_embed("Invalid time format. Use `10s`, `5m`, `1h`, `1d`.", ctx))
        seconds = int(time_str[:-1]) * units[time_str[-1]]
        if seconds > 604800:
            return await ctx.send(embed=error_embed("Max reminder time is 7 days.", ctx))

        await ctx.send(embed=success_embed(f"I'll remind you in **{time_str}**!", ctx))
        await asyncio.sleep(seconds)
        embed = make_embed(
            title="\u23f0 Reminder!",
            description=f"{ctx.author.mention}, you asked me to remind you:\n\n**{message}**",
            color=Colors.WARNING
        )
        try:
            await ctx.channel.send(content=ctx.author.mention, embed=embed)
        except Exception:
            pass

    # ── Timer ────────────────────────────────────────────────

    @commands.hybrid_command()
    async def timer(self, ctx, time_str: str):
        """Set a countdown timer. Format: 10s, 5m, 1h."""
        units = {'s': 1, 'm': 60, 'h': 3600}
        if not time_str[-1] in units or not time_str[:-1].isdigit():
            return await ctx.send(embed=error_embed("Invalid format. Use `10s`, `5m`, `1h`.", ctx))
        seconds = int(time_str[:-1]) * units[time_str[-1]]
        if seconds > 3600:
            return await ctx.send(embed=error_embed("Max timer is 1 hour.", ctx))

        await ctx.send(embed=make_embed(
            title="\u23f2\ufe0f Timer Started",
            description=f"Timer set for **{time_str}**!",
            color=Colors.INFO, ctx=ctx
        ))
        await asyncio.sleep(seconds)
        await ctx.send(
            content=ctx.author.mention,
            embed=make_embed(
                title="\u23f0 Time's Up!",
                description=f"Your **{time_str}** timer is done!",
                color=Colors.WARNING
            )
        )

    # ── Calculator ───────────────────────────────────────────

    @commands.hybrid_command(aliases=["calc", "math"])
    async def calculate(self, ctx, *, expression: str):
        """Evaluate a math expression. Supports +, -, *, /, **, (), etc."""
        import re
        # Only allow safe math characters
        if not re.match(r'^[\d\s\+\-\*/\(\)\.\*\%\^]+$', expression):
            return await ctx.send(embed=error_embed("Invalid expression. Only numbers and math operators allowed.", ctx))
        try:
            # Replace ^ with ** for power
            safe_expr = expression.replace('^', '**')
            result = eval(safe_expr, {"__builtins__": {}}, {})
            embed = make_embed(
                title="\U0001f9ee Calculator",
                color=Colors.INFO, ctx=ctx
            )
            embed.add_field(name="Expression", value=f"```\n{expression}\n```", inline=False)
            embed.add_field(name="Result", value=f"```\n{result}\n```", inline=False)
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send(embed=error_embed("Failed to evaluate expression.", ctx))

    # ── Who Is ───────────────────────────────────────────────

    @commands.hybrid_command(aliases=["userinfo", "ui", "whois"])
    async def who(self, ctx, member: discord.Member = None):
        """Get detailed info about a server member."""
        member = member or ctx.author
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"][:15]
        perms = [p[0].replace('_', ' ').title() for p in member.guild_permissions if p[1]]
        key_perms = [p for p in perms if p in ['Administrator', 'Manage Server', 'Manage Roles',
                     'Manage Channels', 'Ban Members', 'Kick Members', 'Manage Messages']]

        status_icon = {
            discord.Status.online: "\U0001f7e2",
            discord.Status.idle: "\U0001f7e1",
            discord.Status.dnd: "\U0001f534",
            discord.Status.offline: "\u26ab",
        }
        embed = make_embed(
            title=f"\U0001f464 {member.display_name}",
            description=f"{status_icon.get(member.status, '\u26ab')} {str(member.status).title()} \u2022 {member.mention}",
            color=member.color if member.color.value else Colors.PURPLE, ctx=ctx,
            thumbnail=member.display_avatar.url
        )
        embed.add_field(name="\U0001f194 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="\U0001f4c5 Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="\U0001f4e5 Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        if roles:
            embed.add_field(name=f"\U0001f3ad Roles ({len(roles)})", value=" ".join(roles[:10]), inline=False)
        if key_perms:
            embed.add_field(name="\U0001f512 Key Permissions", value=", ".join(key_perms), inline=False)
        if member.premium_since:
            embed.add_field(name="\U0001f48e Boosting Since", value=f"<t:{int(member.premium_since.timestamp())}:R>", inline=True)
        await ctx.send(embed=embed)

    # ── Embed Creator ────────────────────────────────────────

    @commands.hybrid_command(name="embed")
    @commands.has_permissions(manage_messages=True)
    async def create_embed(self, ctx, title: str, *, description: str):
        """Create a custom embed. Usage: .embed "Title" Description text."""
        embed = make_embed(
            title=title,
            description=description,
            color=Colors.BLURPLE,
            footer=f"Created by {ctx.author.display_name}"
        )
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    # ── Steal Emoji ──────────────────────────────────────────

    @commands.hybrid_command(aliases=["stealemoji"])
    @commands.has_permissions(manage_emojis=True)
    async def stealemoji(self, ctx, emoji: discord.PartialEmoji, *, name: str = None):
        """Steal an emoji and add it to this server."""
        name = name or emoji.name
        try:
            emoji_bytes = await emoji.read()
            new_emoji = await ctx.guild.create_custom_emoji(name=name, image=emoji_bytes, reason=f"Stolen by {ctx.author}")
            await ctx.send(embed=success_embed(f"Added emoji {new_emoji} as `:{name}:`!", ctx))
        except Exception as e:
            await ctx.send(embed=error_embed(f"Failed to add emoji: {e}", ctx))

    # ── Role All ─────────────────────────────────────────────

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def roleall(self, ctx, *, role: discord.Role):
        """Give a role to all members in the server."""
        if role >= ctx.author.top_role:
            return await ctx.send(embed=error_embed("You can't assign a role higher than yours.", ctx))
        msg = await ctx.send(embed=make_embed(description=f"\u23f3 Assigning {role.mention} to all members...", color=Colors.INFO, ctx=ctx))
        count = 0
        for member in ctx.guild.members:
            if role not in member.roles and not member.bot:
                try:
                    await member.add_roles(role, reason=f"Roleall by {ctx.author}")
                    count += 1
                except Exception:
                    pass
        await msg.edit(embed=success_embed(f"Added {role.mention} to **{count}** members.", ctx))

    # ── Enlarge Emoji ────────────────────────────────────────

    @commands.hybrid_command(aliases=["big", "jumbo"])
    async def enlarge(self, ctx, emoji: discord.PartialEmoji):
        """Enlarge a custom emoji."""
        embed = make_embed(
            title=f":{emoji.name}:",
            color=Colors.PURPLE, ctx=ctx,
            image=emoji.url
        )
        await ctx.send(embed=embed)

    # ── Message Count ────────────────────────────────────────

    @commands.hybrid_command()
    @commands.has_permissions(manage_messages=True)
    async def msgcount(self, ctx, member: discord.Member = None, limit: int = 500):
        """Count messages by a user in this channel (last N messages)."""
        member = member or ctx.author
        if limit > 5000:
            limit = 5000
        msg = await ctx.send(embed=make_embed(description="\u23f3 Counting messages...", color=Colors.INFO, ctx=ctx))
        count = 0
        async for message in ctx.channel.history(limit=limit):
            if message.author.id == member.id:
                count += 1
        embed = make_embed(
            title="\U0001f4ac Message Count",
            description=f"{member.mention} sent **{count}** messages in the last **{limit}** messages.",
            color=Colors.INFO, ctx=ctx
        )
        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))
