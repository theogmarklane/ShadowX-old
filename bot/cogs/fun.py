import discord
from discord.ext import commands
import random
from .embed_utils import make_embed, error_embed, Colors


class Fun(commands.Cog):
    """Fun and entertaining commands."""
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def say(self, ctx, *, message: str):
        """Make the bot say something."""
        embed = make_embed(description=message, color=Colors.PURPLE, ctx=ctx)
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def choose(self, ctx, *, choices: str):
        """Let the bot choose between options (comma-separated)."""
        options = [c.strip() for c in choices.split(',') if c.strip()]
        if len(options) < 2:
            return await ctx.send(embed=error_embed("Provide at least 2 options separated by commas.", ctx))
        choice = random.choice(options)
        embed = make_embed(title="\U0001f914 The bot has chosen...", color=Colors.PURPLE, ctx=ctx)
        embed.add_field(name="Options", value=" \u2022 ".join(f"`{o}`" for o in options), inline=False)
        embed.add_field(name="\U0001f3af Result", value=f"**{choice}**", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def reverse(self, ctx, *, text: str):
        """Reverse your text."""
        embed = make_embed(
            title="\U0001f500 Reversed",
            description=f"```\n{text[::-1]}\n```",
            color=Colors.PURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["UwU"])
    async def uwu(self, ctx, *, text: str):
        """UwU-ify your message."""
        t = text.replace('r', 'w').replace('l', 'w').replace('R', 'W').replace('L', 'W')
        t = t.replace('no', 'nyo').replace('No', 'Nyo').replace('na', 'nya').replace('Na', 'Nya')
        faces = [' UwU', ' OwO', ' >w<', ' ^w^', ' \u2764\ufe0f']
        embed = make_embed(
            title="UwU",
            description=t + random.choice(faces),
            color=Colors.PINK, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["OwO"])
    async def owo(self, ctx, *, text: str):
        """OwO-ify your message."""
        t = text.replace('r', 'w').replace('l', 'w').replace('R', 'W').replace('L', 'W')
        t = t.replace('th', 'd').replace('Th', 'D')
        embed = make_embed(title="OwO", description=t + " OwO", color=Colors.PINK, ctx=ctx)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["sarcasm"])
    async def mock(self, ctx, *, text: str):
        """SaRcAsM tExT gEnErAtOr."""
        mocked = ''.join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
        embed = make_embed(
            title="\U0001f913 Mocked",
            description=mocked,
            color=Colors.GOLD, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["8ball", "magic8ball"])
    async def eightball(self, ctx, *, question: str):
        """Ask the magic 8-ball a question."""
        responses = [
            ("\U0001f7e2", "It is certain."), ("\U0001f7e2", "Without a doubt."),
            ("\U0001f7e2", "Yes, definitely."), ("\U0001f7e2", "You may rely on it."),
            ("\U0001f7e2", "Most likely."), ("\U0001f7e2", "Outlook good."),
            ("\U0001f7e2", "Yes."), ("\U0001f7e2", "Signs point to yes."),
            ("\U0001f7e1", "Reply hazy, try again."), ("\U0001f7e1", "Ask again later."),
            ("\U0001f7e1", "Better not tell you now."), ("\U0001f7e1", "Cannot predict now."),
            ("\U0001f534", "Don't count on it."), ("\U0001f534", "My reply is no."),
            ("\U0001f534", "My sources say no."), ("\U0001f534", "Outlook not so good."),
            ("\U0001f534", "Very doubtful."),
        ]
        emoji, answer = random.choice(responses)
        embed = make_embed(title="\U0001f3b1 Magic 8-Ball", color=Colors.DARK, ctx=ctx)
        embed.add_field(name="\U0001f4ad Question", value=question, inline=False)
        embed.add_field(name=f"{emoji} Answer", value=f"**{answer}**", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def clap(self, ctx, *, text: str):
        """Add \U0001f44f between \U0001f44f every \U0001f44f word."""
        embed = make_embed(
            description=' \U0001f44f '.join(text.split()),
            color=Colors.GOLD, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def emojify(self, ctx, *, text: str):
        """Convert text to regional indicator emojis."""
        result = ""
        for c in text.lower():
            if c.isalpha():
                result += f":regional_indicator_{c}: "
            elif c == " ":
                result += "   "
            elif c.isdigit():
                num_words = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
                result += f":{num_words[int(c)]}: "
            else:
                result += c
        embed = make_embed(description=result[:2000], color=Colors.GOLD, ctx=ctx)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def rate(self, ctx, *, thing: str):
        """Rate anything out of 10."""
        rating = random.randint(0, 10)
        bar = "\u2588" * rating + "\u2591" * (10 - rating)
        embed = make_embed(
            title=f"\U0001f4ca Rating: {thing}",
            description=f"```\n[{bar}] {rating}/10\n```",
            color=Colors.PURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def ship(self, ctx, user1: discord.User, user2: discord.User = None):
        """Ship two users together and see their compatibility."""
        user2 = user2 or ctx.author
        combined = user1.id + user2.id
        percent = combined % 101
        bar_fill = int(percent / 10)
        bar = "\u2764\ufe0f" * bar_fill + "\U0001f5a4" * (10 - bar_fill)
        if percent > 80:
            status = "\U0001f496 Soulmates!"
        elif percent > 60:
            status = "\U0001f495 Great match!"
        elif percent > 40:
            status = "\U0001f49b Could work!"
        elif percent > 20:
            status = "\U0001f494 Unlikely..."
        else:
            status = "\U0001f480 Not happening."
        embed = make_embed(
            title=f"\U0001f48d Ship: {user1.display_name} x {user2.display_name}",
            description=f"```\n[{bar}] {percent}%\n```\n{status}",
            color=Colors.PINK, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def roast(self, ctx, member: discord.Member = None):
        """Roast someone (or yourself)."""
        member = member or ctx.author
        roasts = [
            "I'd agree with you but then we'd both be wrong.",
            "You're like a cloud. When you disappear, it's a beautiful day.",
            "I'd explain it to you but I left my crayons at home.",
            "You're not stupid, you just have bad luck thinking.",
            "If you were any more inbred you'd be a sandwich.",
            "You bring everyone so much joy... when you leave.",
            "You're proof that even evolution makes mistakes.",
            "I've seen better coding from a random number generator.",
            "You're the reason the gene pool needs a lifeguard.",
            "Your secrets are safe with me. I wasn't even listening.",
            "You're like a software update. Whenever I see you, I think 'not now.'",
            "If you were a spice, you'd be flour.",
        ]
        embed = make_embed(
            title="\U0001f525 Roasted",
            description=f"{member.mention}, {random.choice(roasts)}",
            color=Colors.ERROR, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def compliment(self, ctx, member: discord.Member = None):
        """Give someone a nice compliment."""
        member = member or ctx.author
        compliments = [
            "You're an awesome person!", "You light up the room!",
            "You're one of a kind!", "You have the best smile!",
            "You're more fun than bubble wrap!", "You're like sunshine on a rainy day!",
            "You could survive a zombie apocalypse.", "Your code probably compiles on the first try.",
            "You're the type of person everyone wants to be around.",
            "If you were a vegetable, you'd be a cute-cumber!",
            "You're more refreshing than a cold drink on a hot day.",
        ]
        embed = make_embed(
            title="\U0001f31f Compliment",
            description=f"{member.mention}, {random.choice(compliments)}",
            color=Colors.SUCCESS, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def fact(self, ctx):
        """Get a random fun fact."""
        facts = [
            "Honey never spoils. Archaeologists have found 3000-year-old honey that was still edible.",
            "Octopuses have three hearts and blue blood.",
            "A group of flamingos is called a 'flamboyance'.",
            "Bananas are berries, but strawberries aren't.",
            "The shortest war in history lasted 38 minutes (Britain vs Zanzibar).",
            "A day on Venus is longer than a year on Venus.",
            "There are more possible iterations of a game of chess than atoms in the known universe.",
            "The unicorn is Scotland's national animal.",
            "Cows have best friends and get stressed when separated.",
            "The inventor of the Pringles can is buried in one.",
            "There's enough DNA in the average person's body to stretch from the sun to Pluto 17 times.",
            "An eagle can kill a young deer and fly away with it.",
        ]
        embed = make_embed(
            title="\U0001f4a1 Fun Fact",
            description=random.choice(facts),
            color=Colors.INFO, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def joke(self, ctx):
        """Get a random joke."""
        jokes = [
            ("Why do programmers prefer dark mode?", "Because light attracts bugs."),
            ("Why did the scarecrow win an award?", "He was outstanding in his field."),
            ("What do you call a fake noodle?", "An impasta."),
            ("Why don't scientists trust atoms?", "Because they make up everything!"),
            ("What do you call a bear with no teeth?", "A gummy bear."),
            ("Why did the math book look sad?", "Because it had too many problems."),
            ("What's a computer's favorite snack?", "Microchips."),
            ("Why do Java developers wear glasses?", "Because they can't C#."),
            ("How do you comfort a JavaScript bug?", "You console it."),
            ("Why was the computer cold?", "It left its Windows open."),
        ]
        setup, punchline = random.choice(jokes)
        embed = make_embed(title="\U0001f602 Joke", color=Colors.GOLD, ctx=ctx)
        embed.add_field(name=setup, value=f"||{punchline}||", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def quote(self, ctx):
        """Get an inspirational quote."""
        quotes = [
            ("The only way to do great work is to love what you do.", "Steve Jobs"),
            ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
            ("Stay hungry, stay foolish.", "Steve Jobs"),
            ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
            ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
            ("Life is what happens when you're busy making other plans.", "John Lennon"),
            ("The purpose of our lives is to be happy.", "Dalai Lama"),
            ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
            ("Talk is cheap. Show me the code.", "Linus Torvalds"),
            ("First, solve the problem. Then, write the code.", "John Johnson"),
        ]
        quote_text, author = random.choice(quotes)
        embed = make_embed(
            title="\U0001f4dc Quote",
            description=f"*\"{quote_text}\"*\n\n\u2014 **{author}**",
            color=Colors.BLURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def pp(self, ctx, member: discord.Member = None):
        """Check someone's pp size."""
        member = member or ctx.author
        size = random.randint(1, 15)
        pp = "8" + "=" * size + "D"
        embed = make_embed(
            title=f"\U0001f346 {member.display_name}'s PP Size",
            description=f"```\n{pp}\n```",
            color=Colors.PURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def iq(self, ctx, member: discord.Member = None):
        """Check someone's IQ."""
        member = member or ctx.author
        iq_val = random.randint(1, 200)
        if iq_val > 140:
            comment = "\U0001f9e0 Genius!"
        elif iq_val > 100:
            comment = "\U0001f4a1 Above average!"
        elif iq_val > 70:
            comment = "\U0001f610 Average."
        else:
            comment = "\U0001f921 Bruh."
        embed = make_embed(
            title=f"\U0001f9e0 {member.display_name}'s IQ",
            description=f"**{iq_val}** \u2014 {comment}",
            color=Colors.INFO, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def hack(self, ctx, member: discord.Member):
        """Fake hack someone (totally legit)."""
        import asyncio
        msg = await ctx.send(embed=make_embed(description=f"Hacking {member.display_name}...", color=Colors.DARK, ctx=ctx))
        steps = [
            f"\U0001f50d Finding {member.display_name}'s IP address...",
            f"\U0001f4e7 Logging into {member.display_name}'s email...",
            f"\U0001f4b3 Stealing credit card info...",
            f"\U0001f5c3\ufe0f Downloading their files...",
            f"\U0001f4f1 Accessing their phone...",
            f"\u2705 **Hack complete!** (jk this is fake lol)",
        ]
        for step in steps:
            await asyncio.sleep(1.5)
            await msg.edit(embed=make_embed(description=step, color=Colors.DARK, ctx=ctx))

    @commands.hybrid_command()
    async def howgay(self, ctx, member: discord.Member = None):
        """How gay is someone?"""
        member = member or ctx.author
        percent = random.randint(0, 100)
        bar_fill = int(percent / 10)
        bar = "\U0001f3f3\ufe0f\u200d\U0001f308" * bar_fill + "\u2b1c" * (10 - bar_fill)
        embed = make_embed(
            title=f"\U0001f3f3\ufe0f\u200d\U0001f308 Gay Meter",
            description=f"{member.mention} is **{percent}%** gay\n{bar}",
            color=Colors.PINK, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def randomword(self, ctx):
        """Get a random word with its definition."""
        words = [
            ("serendipity", "The occurrence of events by chance in a happy way."),
            ("ephemeral", "Lasting for a very short time."),
            ("luminous", "Full of or shedding light; bright or shining."),
            ("zenith", "The time at which something is most powerful or successful."),
            ("quixotic", "Exceedingly idealistic; unrealistic and impractical."),
            ("mellifluous", "Sweet or musical; pleasant to hear."),
            ("petrichor", "The pleasant smell after rain on dry earth."),
            ("ineffable", "Too great to be expressed in words."),
            ("sonder", "The realization that each passerby lives a life as vivid as your own."),
            ("ethereal", "Extremely delicate and light; heavenly."),
        ]
        word, definition = random.choice(words)
        embed = make_embed(
            title=f"\U0001f4d6 Word: {word.title()}",
            description=f"*{definition}*",
            color=Colors.BLURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def ascii(self, ctx, *, text: str):
        """Convert text to ASCII art (simple block style)."""
        if len(text) > 15:
            return await ctx.send(embed=error_embed("Text must be 15 characters or less.", ctx))
        result = text.upper()
        embed = make_embed(
            title="\U0001f524 ASCII Text",
            description=f"```\n{result}\n```",
            color=Colors.DARK, ctx=ctx
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))
