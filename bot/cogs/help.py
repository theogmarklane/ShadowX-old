import discord
from discord.ext import commands
from discord.ui import Select, View, Button
from .embed_utils import make_embed, Colors


class HelpSelect(Select):
    def __init__(self, bot, ctx):
        self.bot_ref = bot
        self.ctx = ctx
        options = []
        for cog_name, cog in bot.cogs.items():
            if cog_name in ('Help', 'Webserver'):
                continue
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if cmds:
                emoji_map = {
                    'General': '\U0001f3e0', 'Moderation': '\U0001f6e1\ufe0f',
                    'Fun': '\U0001f389', 'Games': '\U0001f3b2',
                    'Leveling': '\U0001f4c8', 'Economy': '\U0001f4b0',
                    'Music': '\U0001f3b5', 'User': '\U0001f464',
                    'BotManagement': '\u2699\ufe0f', 'Utility': '\U0001f527',
                }
                emoji = emoji_map.get(cog_name, '\U0001f4c1')
                options.append(discord.SelectOption(
                    label=cog_name, description=f"{len(cmds)} commands",
                    emoji=emoji, value=cog_name
                ))
        super().__init__(placeholder="\U0001f50d Select a category...", options=options or [
            discord.SelectOption(label="No categories", value="none")
        ])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("This isn't your menu.", ephemeral=True)
        cog = self.bot_ref.get_cog(self.values[0])
        if not cog:
            return
        cmds = [c for c in cog.get_commands() if not c.hidden]
        desc_lines = []
        for cmd in cmds:
            aliases = f" `{'`, `'.join(cmd.aliases)}`" if cmd.aliases else ""
            desc_lines.append(f"> `.{cmd.qualified_name}`{aliases}\n> {cmd.help or 'No description.'}\n")
        embed = make_embed(
            title=f"\U0001f4c2 {self.values[0]} Commands",
            description="\n".join(desc_lines) or "No commands.",
            color=Colors.PURPLE, ctx=self.ctx
        )
        embed.set_thumbnail(url=self.bot_ref.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed)


class HelpView(View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot, ctx))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Help(commands.Cog):
    """Custom help command with dropdown navigation."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help")
    async def help_cmd(self, ctx, *, command: str = None):
        """Shows all commands or info about a specific command."""
        if command:
            cmd = self.bot.get_command(command)
            if not cmd:
                return await ctx.send(embed=make_embed(
                    description=f"\u274c Command `{command}` not found.",
                    color=Colors.ERROR, ctx=ctx
                ))
            aliases = ", ".join(f"`.{a}`" for a in cmd.aliases) if cmd.aliases else "None"
            usage = f".{cmd.qualified_name} {cmd.signature}" if cmd.signature else f".{cmd.qualified_name}"
            embed = make_embed(
                title=f"\U0001f4cb Command: .{cmd.qualified_name}",
                color=Colors.INFO, ctx=ctx
            )
            embed.add_field(name="\U0001f4dd Description", value=cmd.help or "No description.", inline=False)
            embed.add_field(name="\U0001f4e6 Usage", value=f"`{usage}`", inline=False)
            embed.add_field(name="\U0001f504 Aliases", value=aliases, inline=False)
            if cmd.cog:
                embed.add_field(name="\U0001f4c1 Category", value=cmd.cog.qualified_name, inline=False)
            return await ctx.send(embed=embed)

        total_cmds = sum(1 for c in self.bot.walk_commands() if not c.hidden)
        embed = make_embed(
            title="\U0001f30c Project SHDW Help Menu",
            description=(
                f"**Total Commands:** `{total_cmds}`\n"
                f"**Prefix:** `.`\n\n"
                f"Select a category from the dropdown below to view its commands.\n"
                f"Use `.help <command>` for detailed info on a command."
            ),
            color=Colors.PURPLE, ctx=ctx
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        categories = []
        for cog_name, cog in self.bot.cogs.items():
            if cog_name in ('Help', 'Webserver'):
                continue
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if cmds:
                emoji_map = {
                    'General': '\U0001f3e0', 'Moderation': '\U0001f6e1\ufe0f',
                    'Fun': '\U0001f389', 'Games': '\U0001f3b2',
                    'Leveling': '\U0001f4c8', 'Economy': '\U0001f4b0',
                    'Music': '\U0001f3b5', 'User': '\U0001f464',
                    'BotManagement': '\u2699\ufe0f', 'Utility': '\U0001f527',
                }
                emoji = emoji_map.get(cog_name, '\U0001f4c1')
                categories.append(f"{emoji} **{cog_name}** \u2014 `{len(cmds)}` commands")
        embed.add_field(name="\U0001f4da Categories", value="\n".join(categories) or "None loaded.", inline=False)
        await ctx.send(embed=embed, view=HelpView(self.bot, ctx))


async def setup(bot):
    await bot.add_cog(Help(bot))
