import discord
from discord.ext import commands
from datetime import datetime
from .embed_utils import make_embed, error_embed, Colors


class General(commands.Cog):
    """General information and utility commands."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.hybrid_command()
    async def ping(self, ctx):
        """Check the bot's latency."""
        ws = round(self.bot.latency * 1000)
        embed = make_embed(
            title="\U0001f3d3 Pong!",
            color=Colors.SUCCESS if ws < 200 else Colors.WARNING, ctx=ctx
        )
        embed.add_field(name="WebSocket", value=f"`{ws}ms`", inline=True)
        embed.add_field(name="Status", value="\U0001f7e2 Good" if ws < 200 else "\U0001f7e1 Slow", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["botinfo", "about"])
    async def info(self, ctx):
        """Show detailed bot information."""
        owner_ids = self.config.get('BOT_OWNERS', [])
        dev_ids = self.config.get('BOT_DEVELOPERS', [])
        owners = ", ".join(f"<@{i}>" for i in owner_ids) or "N/A"
        devs = ", ".join(f"<@{i}>" for i in dev_ids) or "N/A"
        uptime = datetime.utcnow() - self.bot.start_time
        hours, rem = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)

        total_cmds = sum(1 for _ in self.bot.walk_commands())
        embed = make_embed(
            title=f"\U0001f30c {self.bot.user.name}",
            description="A powerful, feature-rich Discord bot built for your community.",
            color=Colors.PURPLE, ctx=ctx,
            thumbnail=self.bot.user.display_avatar.url
        )
        embed.add_field(name="\U0001f4e1 Latency", value=f"`{round(self.bot.latency * 1000)}ms`", inline=True)
        embed.add_field(name="\U0001f5c2\ufe0f Servers", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="\U0001f465 Users", value=f"`{len(self.bot.users)}`", inline=True)
        embed.add_field(name="\u2699\ufe0f Commands", value=f"`{total_cmds}`", inline=True)
        embed.add_field(name="\u23f1\ufe0f Uptime", value=f"`{hours}h {minutes}m {seconds}s`", inline=True)
        embed.add_field(name="\U0001f4e6 Library", value=f"`discord.py {discord.__version__}`", inline=True)
        embed.add_field(name="\U0001f451 Owners", value=owners, inline=False)
        embed.add_field(name="\U0001f6e0\ufe0f Developers", value=devs, inline=False)

        links = []
        if self.config.get('BOT_WEBSITE'):
            links.append(f"[\U0001f310 Website]({self.config['BOT_WEBSITE']})")
        if self.config.get('BOT_SUPPORT_SERVER'):
            links.append(f"[\U0001f4ac Support]({self.config['BOT_SUPPORT_SERVER']})")
        if self.config.get('BOT_INVITE_URL'):
            links.append(f"[\U0001f517 Invite]({self.config['BOT_INVITE_URL']})")
        if links:
            embed.add_field(name="\U0001f517 Links", value=" \u2022 ".join(links), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def avatar(self, ctx, user: discord.User = None):
        """Get a user's avatar in full resolution."""
        user = user or ctx.author
        embed = make_embed(
            title=f"\U0001f5bc\ufe0f {user.display_name}'s Avatar",
            color=Colors.PURPLE, ctx=ctx,
            image=user.display_avatar.with_size(4096).url
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Open in Browser", style=discord.ButtonStyle.link,
            url=user.display_avatar.with_size(4096).url
        ))
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command()
    async def banner(self, ctx, user: discord.User = None):
        """Get a user's profile banner."""
        user = user or ctx.author
        user = await self.bot.fetch_user(user.id)
        if not user.banner:
            return await ctx.send(embed=error_embed(f"{user.display_name} doesn't have a banner.", ctx))
        embed = make_embed(
            title=f"\U0001f5bc\ufe0f {user.display_name}'s Banner",
            color=Colors.PURPLE, ctx=ctx,
            image=user.banner.with_size(4096).url
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["si", "server"])
    async def serverinfo(self, ctx):
        """Show detailed information about this server."""
        g = ctx.guild
        if not g:
            return await ctx.send(embed=error_embed("This command can only be used in a server.", ctx))
        owner = g.owner or await self.bot.fetch_user(g.owner_id)
        text_channels = len(g.text_channels)
        voice_channels = len(g.voice_channels)
        categories = len(g.categories)
        roles = len(g.roles) - 1
        emojis = len(g.emojis)
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots

        embed = make_embed(
            title=f"\U0001f3e0 {g.name}",
            color=Colors.PURPLE, ctx=ctx,
            thumbnail=g.icon.url if g.icon else None
        )
        embed.add_field(name="\U0001f194 Server ID", value=f"`{g.id}`", inline=True)
        embed.add_field(name="\U0001f451 Owner", value=f"{owner.mention}", inline=True)
        embed.add_field(name="\U0001f4c5 Created", value=f"<t:{int(g.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="\U0001f465 Members", value=f"`{g.member_count}` ({humans} humans, {bots} bots)", inline=False)
        embed.add_field(name="\U0001f4ac Channels", value=f"`{text_channels}` text \u2022 `{voice_channels}` voice \u2022 `{categories}` categories", inline=False)
        embed.add_field(name="\U0001f3ad Roles", value=f"`{roles}`", inline=True)
        embed.add_field(name="\U0001f60e Emojis", value=f"`{emojis}`", inline=True)
        embed.add_field(name="\U0001f4a0 Boost Level", value=f"Level `{g.premium_tier}` ({g.premium_subscription_count} boosts)", inline=True)
        if g.banner:
            embed.set_image(url=g.banner.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["mc"])
    async def membercount(self, ctx):
        """Show the server's member count."""
        g = ctx.guild
        bots = sum(1 for m in g.members if m.bot)
        humans = g.member_count - bots
        embed = make_embed(
            title=f"\U0001f465 {g.name} \u2014 Member Count",
            color=Colors.INFO, ctx=ctx
        )
        embed.add_field(name="\U0001f464 Humans", value=f"`{humans}`", inline=True)
        embed.add_field(name="\U0001f916 Bots", value=f"`{bots}`", inline=True)
        embed.add_field(name="\U0001f4ca Total", value=f"`{g.member_count}`", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def invite(self, ctx):
        """Get the bot's invite link."""
        url = self.config.get('BOT_INVITE_URL', f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands")
        embed = make_embed(
            title="\U0001f517 Invite Project SHDW",
            description=f"Click the button below to add me to your server!",
            color=Colors.BLURPLE, ctx=ctx
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite Me", style=discord.ButtonStyle.link, url=url))
        if self.config.get('BOT_SUPPORT_SERVER'):
            view.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=self.config['BOT_SUPPORT_SERVER']))
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command()
    async def uptime(self, ctx):
        """Show how long the bot has been online."""
        delta = datetime.utcnow() - self.bot.start_time
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        embed = make_embed(
            title="\u23f1\ufe0f Uptime",
            description=f"```\n{days}d {hours}h {minutes}m {seconds}s\n```",
            color=Colors.SUCCESS, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["ri"])
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Get info about a specific role."""
        perms = ", ".join(p[0].replace('_', ' ').title() for p in role.permissions if p[1]) or "None"
        embed = make_embed(
            title=f"\U0001f3ad Role: {role.name}",
            color=role.color if role.color.value else Colors.PURPLE, ctx=ctx
        )
        embed.add_field(name="\U0001f194 ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="\U0001f3a8 Color", value=f"`{role.color}`", inline=True)
        embed.add_field(name="\U0001f465 Members", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name="\U0001f4c5 Created", value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="\U0001f53c Position", value=f"`{role.position}`", inline=True)
        embed.add_field(name="\U0001f4cc Mentionable", value=f"`{role.mentionable}`", inline=True)
        embed.add_field(name="\U0001f512 Permissions", value=f"```\n{perms[:1000]}\n```", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["ci"])
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        """Get info about a text channel."""
        channel = channel or ctx.channel
        embed = make_embed(
            title=f"\U0001f4ac Channel: #{channel.name}",
            color=Colors.INFO, ctx=ctx
        )
        embed.add_field(name="\U0001f194 ID", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="\U0001f4c1 Category", value=f"`{channel.category or 'None'}`", inline=True)
        embed.add_field(name="\U0001f4c5 Created", value=f"<t:{int(channel.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="\U0001f4cc Topic", value=channel.topic or "No topic set.", inline=False)
        embed.add_field(name="\U0001f40c Slowmode", value=f"`{channel.slowmode_delay}s`", inline=True)
        embed.add_field(name="\U0001f512 NSFW", value=f"`{channel.is_nsfw()}`", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["emotes"])
    async def emojis(self, ctx):
        """List all custom emojis in the server."""
        if not ctx.guild.emojis:
            return await ctx.send(embed=error_embed("This server has no custom emojis.", ctx))
        emoji_list = " ".join(str(e) for e in ctx.guild.emojis[:50])
        embed = make_embed(
            title=f"\U0001f60e {ctx.guild.name} \u2014 Emojis ({len(ctx.guild.emojis)})",
            description=emoji_list,
            color=Colors.GOLD, ctx=ctx
        )
        if len(ctx.guild.emojis) > 50:
            embed.set_footer(text=f"Showing 50/{len(ctx.guild.emojis)} emojis")
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["roles"])
    async def rolelist(self, ctx):
        """List all roles in the server."""
        roles = [r.mention for r in reversed(ctx.guild.roles) if r.name != "@everyone"][:25]
        embed = make_embed(
            title=f"\U0001f3ad {ctx.guild.name} \u2014 Roles ({len(ctx.guild.roles) - 1})",
            description="\n".join(roles) or "No roles.",
            color=Colors.PURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["sicon"])
    async def servericon(self, ctx):
        """Get the server's icon in full resolution."""
        if not ctx.guild.icon:
            return await ctx.send(embed=error_embed("This server has no icon.", ctx))
        embed = make_embed(
            title=f"\U0001f5bc\ufe0f {ctx.guild.name}'s Icon",
            color=Colors.PURPLE, ctx=ctx,
            image=ctx.guild.icon.with_size(4096).url
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["sbanner"])
    async def serverbanner(self, ctx):
        """Get the server's banner."""
        if not ctx.guild.banner:
            return await ctx.send(embed=error_embed("This server has no banner.", ctx))
        embed = make_embed(
            title=f"\U0001f5bc\ufe0f {ctx.guild.name}'s Banner",
            color=Colors.PURPLE, ctx=ctx,
            image=ctx.guild.banner.with_size(4096).url
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def firstmessage(self, ctx):
        """Get the first message ever sent in this channel."""
        async for msg in ctx.channel.history(limit=1, oldest_first=True):
            embed = make_embed(
                title="\U0001f4dc First Message",
                description=msg.content or "*No text content*",
                color=Colors.GOLD, ctx=ctx
            )
            embed.add_field(name="Author", value=msg.author.mention, inline=True)
            embed.add_field(name="Sent", value=f"<t:{int(msg.created_at.timestamp())}:R>", inline=True)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to Message", style=discord.ButtonStyle.link, url=msg.jump_url))
            return await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(General(bot))
