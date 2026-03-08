import discord
from discord.ext import commands, tasks
import sqlite3
import os
from .embed_utils import make_embed, success_embed, error_embed, Colors

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))


class User(commands.Cog):
    """User profile and settings management."""
    def __init__(self, bot):
        self.bot = bot
        self.update_usernames.start()

    def cog_unload(self):
        self.update_usernames.cancel()

    @tasks.loop(minutes=30)
    async def update_usernames(self):
        await self.bot.wait_until_ready()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        for (uid,) in c.fetchall():
            user = self.bot.get_user(uid)
            if not user:
                continue
            c.execute("UPDATE users SET username = ?, display_name = ? WHERE user_id = ?",
                      (user.name, user.display_name, uid))
        conn.commit()
        conn.close()

    @commands.hybrid_command(aliases=["user", "p"])
    async def profile(self, ctx, user: discord.User = None):
        """Show your or someone's profile card."""
        user = user or ctx.author
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
        c.execute("""
            SELECT personal_prefix, bio, profile_picture, dm_enabled, show_status,
                   show_dabloons, dabloons, karma, xp, level
            FROM users WHERE user_id = ?
        """, (user.id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return await ctx.send(embed=error_embed("User not found.", ctx))

        prefix, bio, pfp, dm_on, show_status, show_dab, dabloons, karma, xp, level = row
        member = ctx.guild.get_member(user.id) if ctx.guild else None

        embed = make_embed(
            title=f"\U0001f464 {user.display_name}",
            color=Colors.PURPLE, ctx=ctx,
            thumbnail=pfp or user.display_avatar.url
        )

        # Status bar
        if member and show_status:
            status_icon = {
                discord.Status.online: "\U0001f7e2",
                discord.Status.idle: "\U0001f7e1",
                discord.Status.dnd: "\U0001f534",
                discord.Status.offline: "\u26ab",
            }
            status_text = status_icon.get(member.status, "\u26ab") + " " + str(member.status).replace("dnd", "Do Not Disturb").title()
            activities = []
            for a in member.activities:
                if isinstance(a, discord.CustomActivity) and a.name:
                    activities.append(f"\U0001f4ac {a.name}")
                elif isinstance(a, discord.Game):
                    activities.append(f"\U0001f3ae Playing {a.name}")
                elif isinstance(a, discord.Streaming):
                    activities.append(f"\U0001f534 Streaming {a.name}")
                elif isinstance(a, discord.Activity):
                    activities.append(f"\U0001f3b5 {a.name}")
            status_text += ("\n" + "\n".join(activities)) if activities else ""
            embed.add_field(name="Status", value=status_text, inline=False)

        embed.add_field(name="\U0001f4dd Bio", value=bio or "*No bio set.*", inline=False)

        # Stats row
        embed.add_field(name="\U0001f4c8 Level", value=f"`{level}`", inline=True)
        embed.add_field(name="\u2728 XP", value=f"`{int(xp)}`", inline=True)
        embed.add_field(name="\u2b50 Karma", value=f"`{karma}`", inline=True)

        if show_dab:
            embed.add_field(name="\U0001f4b0 Dabloons", value=f"`{dabloons:,.2f}`", inline=True)
        embed.add_field(name="\U0001f4ec DMs Open", value="\U0001f7e2 Yes" if dm_on else "\U0001f534 No", inline=True)

        if prefix:
            embed.add_field(name="\u2699\ufe0f Custom Prefix", value=f"`{prefix}`", inline=True)

        # Account age
        embed.add_field(
            name="\U0001f4c5 Account Created",
            value=f"<t:{int(user.created_at.timestamp())}:R>",
            inline=True
        )
        if member and member.joined_at:
            embed.add_field(
                name="\U0001f4e5 Joined Server",
                value=f"<t:{int(member.joined_at.timestamp())}:R>",
                inline=True
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def bio(self, ctx, *, text: str):
        """Set your bio."""
        if len(text) > 200:
            return await ctx.send(embed=error_embed("Bio must be 200 characters or less.", ctx))
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (ctx.author.id,))
        c.execute("UPDATE users SET bio = ? WHERE user_id = ?", (text, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Bio updated!", ctx))

    @commands.hybrid_command()
    async def settings(self, ctx):
        """View and toggle your profile settings."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (ctx.author.id,))
        c.execute("""
            SELECT personal_prefix, bio, dm_enabled, show_status, show_dabloons
            FROM users WHERE user_id = ?
        """, (ctx.author.id,))
        row = c.fetchone()
        conn.close()

        prefix, bio, dm_on, show_status, show_dab = row

        def status_icon(val):
            return "\U0001f7e2 Enabled" if val else "\U0001f534 Disabled"

        embed = make_embed(
            title=f"\u2699\ufe0f {ctx.author.display_name}'s Settings",
            color=Colors.INFO, ctx=ctx,
            thumbnail=ctx.author.display_avatar.url
        )
        embed.add_field(name="\U0001f4dd Prefix", value=f"`{prefix or 'Default (.)'}`", inline=True)
        embed.add_field(name="\U0001f4ec DMs", value=status_icon(dm_on), inline=True)
        embed.add_field(name="\U0001f4f1 Show Status", value=status_icon(show_status), inline=True)
        embed.add_field(name="\U0001f4b0 Show Dabloons", value=status_icon(show_dab), inline=True)
        embed.add_field(name="\U0001f4dd Bio", value=bio or "*Not set*", inline=False)

        class SettingsView(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=120)
                self.cog = cog

            async def _toggle(self, interaction, field):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Not your settings!", ephemeral=True)
                conn2 = sqlite3.connect(DB_PATH)
                c2 = conn2.cursor()
                c2.execute(f"SELECT {field} FROM users WHERE user_id = ?", (ctx.author.id,))
                current = c2.fetchone()[0]
                new_val = 0 if current else 1
                c2.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (new_val, ctx.author.id))
                conn2.commit()

                c2.execute("SELECT personal_prefix, bio, dm_enabled, show_status, show_dabloons FROM users WHERE user_id = ?", (ctx.author.id,))
                updated = c2.fetchone()
                conn2.close()

                embed2 = make_embed(
                    title=f"\u2699\ufe0f {ctx.author.display_name}'s Settings",
                    color=Colors.INFO, ctx=ctx,
                    thumbnail=ctx.author.display_avatar.url
                )
                embed2.add_field(name="\U0001f4dd Prefix", value=f"`{updated[0] or 'Default (.)'}`", inline=True)
                embed2.add_field(name="\U0001f4ec DMs", value=status_icon(updated[2]), inline=True)
                embed2.add_field(name="\U0001f4f1 Show Status", value=status_icon(updated[3]), inline=True)
                embed2.add_field(name="\U0001f4b0 Show Dabloons", value=status_icon(updated[4]), inline=True)
                embed2.add_field(name="\U0001f4dd Bio", value=updated[1] or "*Not set*", inline=False)
                await interaction.response.edit_message(embed=embed2, view=self)

            @discord.ui.button(label="Toggle DMs", style=discord.ButtonStyle.primary, emoji="\U0001f4ec")
            async def toggle_dm(self, interaction, button):
                await self._toggle(interaction, "dm_enabled")

            @discord.ui.button(label="Toggle Status", style=discord.ButtonStyle.primary, emoji="\U0001f4f1")
            async def toggle_status(self, interaction, button):
                await self._toggle(interaction, "show_status")

            @discord.ui.button(label="Toggle Dabloons", style=discord.ButtonStyle.primary, emoji="\U0001f4b0")
            async def toggle_dab(self, interaction, button):
                await self._toggle(interaction, "show_dabloons")

        await ctx.send(embed=embed, view=SettingsView(self))

    @commands.hybrid_command(aliases=["setpfx"])
    async def setmyprefix(self, ctx, *, prefix: str = None):
        """Set your personal command prefix (leave empty to reset)."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (ctx.author.id,))
        c.execute("UPDATE users SET personal_prefix = ? WHERE user_id = ?", (prefix, ctx.author.id))
        conn.commit()
        conn.close()
        if prefix:
            await ctx.send(embed=success_embed(f"Your personal prefix set to `{prefix}`.", ctx))
        else:
            await ctx.send(embed=success_embed("Your personal prefix has been reset.", ctx))


async def setup(bot):
    await bot.add_cog(User(bot))
