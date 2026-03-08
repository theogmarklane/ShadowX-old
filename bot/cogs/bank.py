import discord
from discord.ext import commands
import sqlite3
import os
import random
import time
from .embed_utils import make_embed, success_embed, error_embed, Colors

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))


def is_dev_or_owner():
    async def predicate(ctx):
        config = getattr(ctx.bot, 'config', {})
        ids = set(config.get('BOT_OWNERS', []) + config.get('BOT_DEVELOPERS', []))
        return ctx.author.id in ids or await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


class Economy(commands.Cog):
    """Economy system: earn, spend, and manage dabloons."""
    def __init__(self, bot):
        self.bot = bot
        self._daily_cooldowns = {}
        self._weekly_cooldowns = {}
        self._rob_cooldowns = {}
        self._work_cooldowns = {}

    def _get_db(self):
        return sqlite3.connect(DB_PATH)

    def _ensure_user(self, conn, user_id):
        conn.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))

    # ── Balance ─────────────────────────────────────────────

    @commands.hybrid_command(aliases=["bal", "money", "dabloons", "wallet"])
    async def balance(self, ctx, user: discord.User = None):
        """Check your or someone's dabloons balance."""
        user = user or ctx.author
        conn = self._get_db()
        self._ensure_user(conn, user.id)
        c = conn.cursor()
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (user.id,))
        bal = c.fetchone()[0]
        conn.close()

        embed = make_embed(
            title=f"\U0001f4b0 {user.display_name}'s Wallet",
            color=Colors.GOLD, ctx=ctx,
            thumbnail=user.display_avatar.url
        )
        embed.add_field(name="\U0001f4b5 Balance", value=f"**{bal:,.2f}** dabloons", inline=False)
        await ctx.send(embed=embed)

    # ── Pay ──────────────────────────────────────────────────

    @commands.hybrid_command(aliases=["give", "transfer", "send"])
    async def pay(self, ctx, user: discord.User, amount: float):
        """Pay dabloons to another user (5% tax)."""
        if user.id == ctx.author.id:
            return await ctx.send(embed=error_embed("You can't pay yourself.", ctx))
        if amount <= 0:
            return await ctx.send(embed=error_embed("Amount must be positive.", ctx))
        conn = self._get_db()
        self._ensure_user(conn, ctx.author.id)
        self._ensure_user(conn, user.id)
        c = conn.cursor()
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (ctx.author.id,))
        bal = c.fetchone()[0]
        if bal < amount:
            conn.close()
            return await ctx.send(embed=error_embed(f"You only have **{bal:,.2f}** dabloons.", ctx))
        tax = round(amount * 0.05, 2)
        received = amount - tax
        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (amount, ctx.author.id))
        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (received, user.id))
        conn.commit()
        conn.close()

        embed = make_embed(title="\U0001f4b8 Payment Sent", color=Colors.SUCCESS, ctx=ctx)
        embed.add_field(name="From", value=ctx.author.mention, inline=True)
        embed.add_field(name="To", value=user.mention, inline=True)
        embed.add_field(name="Amount", value=f"**{received:,.2f}** dabloons", inline=True)
        embed.add_field(name="Tax (5%)", value=f"**{tax:,.2f}** dabloons", inline=True)
        await ctx.send(embed=embed)

    # ── Daily / Weekly ──────────────────────────────────────

    @commands.hybrid_command()
    async def daily(self, ctx):
        """Claim your daily dabloons reward (50-150)."""
        key = ctx.author.id
        now = time.time()
        if key in self._daily_cooldowns and now - self._daily_cooldowns[key] < 86400:
            remaining = int(86400 - (now - self._daily_cooldowns[key]))
            h, m = divmod(remaining, 3600)
            mins, s = divmod(m, 60)
            return await ctx.send(embed=error_embed(f"You already claimed your daily! Come back in **{h}h {mins}m {s}s**.", ctx))
        self._daily_cooldowns[key] = now
        reward = random.randint(50, 150)
        conn = self._get_db()
        self._ensure_user(conn, ctx.author.id)
        conn.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (reward, ctx.author.id))
        conn.commit()
        conn.close()
        embed = make_embed(
            title="\U0001f381 Daily Reward",
            description=f"You received **{reward}** dabloons!",
            color=Colors.SUCCESS, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def weekly(self, ctx):
        """Claim your weekly dabloons reward (200-500)."""
        key = ctx.author.id
        now = time.time()
        if key in self._weekly_cooldowns and now - self._weekly_cooldowns[key] < 604800:
            remaining = int(604800 - (now - self._weekly_cooldowns[key]))
            d, rem = divmod(remaining, 86400)
            h, rem2 = divmod(rem, 3600)
            return await ctx.send(embed=error_embed(f"You already claimed your weekly! Come back in **{d}d {h}h**.", ctx))
        self._weekly_cooldowns[key] = now
        reward = random.randint(200, 500)
        conn = self._get_db()
        self._ensure_user(conn, ctx.author.id)
        conn.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (reward, ctx.author.id))
        conn.commit()
        conn.close()
        embed = make_embed(
            title="\U0001f4e6 Weekly Reward",
            description=f"You received **{reward}** dabloons!",
            color=Colors.SUCCESS, ctx=ctx
        )
        await ctx.send(embed=embed)

    # ── Work ────────────────────────────────────────────────

    @commands.hybrid_command()
    async def work(self, ctx):
        """Work a shift to earn some dabloons (1h cooldown)."""
        key = ctx.author.id
        now = time.time()
        if key in self._work_cooldowns and now - self._work_cooldowns[key] < 3600:
            remaining = int(3600 - (now - self._work_cooldowns[key]))
            m, s = divmod(remaining, 60)
            return await ctx.send(embed=error_embed(f"You're still tired! Come back in **{m}m {s}s**.", ctx))
        self._work_cooldowns[key] = now

        jobs = [
            ("Software Developer", 30, 80),
            ("Pizza Delivery Driver", 10, 40),
            ("Astronaut", 50, 100),
            ("Streamer", 20, 60),
            ("Hacker", 40, 90),
            ("Chef", 15, 50),
            ("Teacher", 20, 45),
            ("Artist", 10, 60),
        ]
        job, min_pay, max_pay = random.choice(jobs)
        pay = random.randint(min_pay, max_pay)
        conn = self._get_db()
        self._ensure_user(conn, ctx.author.id)
        conn.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (pay, ctx.author.id))
        conn.commit()
        conn.close()

        embed = make_embed(
            title="\U0001f4bc Work Shift",
            description=f"You worked as a **{job}** and earned **{pay}** dabloons!",
            color=Colors.SUCCESS, ctx=ctx
        )
        await ctx.send(embed=embed)

    # ── Rob ──────────────────────────────────────────────────

    @commands.hybrid_command(aliases=["steal"])
    async def rob(self, ctx, member: discord.Member):
        """Try to rob someone! 40% success rate, 2h cooldown."""
        if member.id == ctx.author.id:
            return await ctx.send(embed=error_embed("You can't rob yourself.", ctx))
        if member.bot:
            return await ctx.send(embed=error_embed("You can't rob bots.", ctx))

        key = ctx.author.id
        now = time.time()
        if key in self._rob_cooldowns and now - self._rob_cooldowns[key] < 7200:
            remaining = int(7200 - (now - self._rob_cooldowns[key]))
            h, m = divmod(remaining, 3600)
            mins = m // 60
            return await ctx.send(embed=error_embed(f"You're laying low! Come back in **{h}h {mins}m**.", ctx))
        self._rob_cooldowns[key] = now

        conn = self._get_db()
        self._ensure_user(conn, member.id)
        self._ensure_user(conn, ctx.author.id)
        c = conn.cursor()
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (member.id,))
        victim_bal = c.fetchone()[0]

        if victim_bal < 20:
            conn.close()
            return await ctx.send(embed=error_embed(f"{member.display_name} doesn't have enough dabloons to rob.", ctx))

        if random.random() < 0.4:
            stolen = random.randint(1, min(int(victim_bal * 0.3), 200))
            c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (stolen, member.id))
            c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (stolen, ctx.author.id))
            conn.commit()
            conn.close()
            embed = make_embed(
                title="\U0001f4b0 Rob Successful!",
                description=f"You stole **{stolen}** dabloons from {member.mention}!",
                color=Colors.SUCCESS, ctx=ctx
            )
        else:
            fine = random.randint(20, 80)
            c.execute("SELECT dabloons FROM users WHERE user_id = ?", (ctx.author.id,))
            author_bal = c.fetchone()[0]
            actual_fine = min(fine, int(author_bal))
            c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (actual_fine, ctx.author.id))
            conn.commit()
            conn.close()
            embed = make_embed(
                title="\U0001f6a8 Rob Failed!",
                description=f"You got caught and were fined **{actual_fine}** dabloons!",
                color=Colors.ERROR, ctx=ctx
            )
        await ctx.send(embed=embed)

    # ── Economy Leaderboard ─────────────────────────────────

    @commands.hybrid_command(aliases=["richest", "baltop"])
    async def richlist(self, ctx):
        """Show the top 10 richest users."""
        conn = self._get_db()
        c = conn.cursor()
        c.execute("SELECT user_id, dabloons FROM users WHERE dabloons > 0 ORDER BY dabloons DESC LIMIT 10")
        rows = c.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=error_embed("No one has any dabloons yet.", ctx))

        medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
        desc = ""
        for i, (uid, bal) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            desc += f"{medal} <@{uid}> \u2014 **{bal:,.2f}** dabloons\n"

        embed = make_embed(
            title="\U0001f4b0 Richest Users",
            description=desc, color=Colors.GOLD, ctx=ctx
        )
        await ctx.send(embed=embed)

    # ── Bank ────────────────────────────────────────────────

    @commands.hybrid_command(aliases=["seebank", "bankbalance"])
    async def bank(self, ctx):
        """Check the bot's bank balance."""
        conn = self._get_db()
        self._ensure_user(conn, self.bot.user.id)
        c = conn.cursor()
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (self.bot.user.id,))
        bal = c.fetchone()[0]
        conn.close()
        embed = make_embed(
            title="\U0001f3e6 Project SHDW Bank",
            description=f"The bank holds **{bal:,.2f}** dabloons.",
            color=Colors.INFO, ctx=ctx
        )
        await ctx.send(embed=embed)

    # ── Admin Commands ──────────────────────────────────────

    @commands.command(aliases=["setbal"])
    @is_dev_or_owner()
    async def adminsetbal(self, ctx, user: discord.User, amount: float):
        """[Admin] Set a user's balance."""
        conn = self._get_db()
        self._ensure_user(conn, user.id)
        conn.execute("UPDATE users SET dabloons = ? WHERE user_id = ?", (amount, user.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Set {user.display_name}'s balance to **{amount:,.2f}** dabloons.", ctx))

    @commands.command(aliases=["addbal"])
    @is_dev_or_owner()
    async def adminaddbal(self, ctx, user: discord.User, amount: float):
        """[Admin] Add dabloons to a user."""
        conn = self._get_db()
        self._ensure_user(conn, user.id)
        conn.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (amount, user.id))
        conn.commit()
        conn.close()
        await ctx.send(embed=success_embed(f"Added **{amount:,.2f}** dabloons to {user.display_name}.", ctx))


async def setup(bot):
    await bot.add_cog(Economy(bot))
