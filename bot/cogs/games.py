import discord
from discord.ext import commands
import random
import asyncio
import sqlite3
import os
from .embed_utils import make_embed, success_embed, error_embed, Colors

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))


class Games(commands.Cog):
    """Casino, gambling, and interactive games."""
    def __init__(self, bot):
        self.bot = bot

    def _get_db(self):
        return sqlite3.connect(DB_PATH)

    def _get_balance(self, user_id):
        conn = self._get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
        bal = c.fetchone()[0]
        conn.commit()
        conn.close()
        return bal

    def _update_balance(self, user_id, amount):
        conn = self._get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

    # ── Coinflip ────────────────────────────────────────────

    @commands.hybrid_command(aliases=["cf", "flip"])
    async def coinflip(self, ctx, bet: int = 0, call: str = None):
        """Flip a coin! Optionally bet dabloons and call heads/tails."""
        result = random.choice(["Heads", "Tails"])
        emoji = "\U0001fa99"

        if bet > 0 and call:
            call = call.lower()
            if call not in ("heads", "tails", "h", "t"):
                return await ctx.send(embed=error_embed("Call `heads` or `tails`.", ctx))
            call_full = "Heads" if call in ("heads", "h") else "Tails"
            bal = self._get_balance(ctx.author.id)
            if bal < bet:
                return await ctx.send(embed=error_embed(f"You only have **{bal}** dabloons.", ctx))
            won = result == call_full
            if won:
                self._update_balance(ctx.author.id, bet)
                embed = make_embed(
                    title=f"{emoji} Coinflip \u2014 {result}!",
                    description=f"You called **{call_full}** and **won {bet}** dabloons! \U0001f389",
                    color=Colors.SUCCESS, ctx=ctx
                )
            else:
                self._update_balance(ctx.author.id, -bet)
                embed = make_embed(
                    title=f"{emoji} Coinflip \u2014 {result}!",
                    description=f"You called **{call_full}** and **lost {bet}** dabloons.",
                    color=Colors.ERROR, ctx=ctx
                )
        else:
            embed = make_embed(
                title=f"{emoji} Coinflip",
                description=f"The coin landed on **{result}**!",
                color=Colors.GOLD, ctx=ctx
            )
        await ctx.send(embed=embed)

    # ── Dice Roll ───────────────────────────────────────────

    @commands.hybrid_command(aliases=["dice"])
    async def roll(self, ctx, sides: int = 6):
        """Roll a die (default 6 sides)."""
        if sides < 2:
            return await ctx.send(embed=error_embed("Sides must be at least 2.", ctx))
        result = random.randint(1, sides)
        embed = make_embed(
            title="\U0001f3b2 Dice Roll",
            description=f"You rolled a **{result}** (d{sides})",
            color=Colors.GOLD, ctx=ctx
        )
        await ctx.send(embed=embed)

    # ── Slots ───────────────────────────────────────────────

    @commands.hybrid_command()
    async def slots(self, ctx, bet: int = 10):
        """Play the slot machine! Bet dabloons to win big."""
        if bet < 5:
            return await ctx.send(embed=error_embed("Minimum bet is **5** dabloons.", ctx))
        bal = self._get_balance(ctx.author.id)
        if bal < bet:
            return await ctx.send(embed=error_embed(f"You only have **{bal}** dabloons.", ctx))

        symbols = ["\U0001f352", "\U0001f34b", "\U0001f34a", "\U0001f349", "\u2b50", "\U0001f48e"]
        weights = [30, 25, 20, 15, 7, 3]
        result = random.choices(symbols, weights=weights, k=3)
        display = f"**\u2003{result[0]} \u2502 {result[1]} \u2502 {result[2]}\u2003**"

        payout = 0
        tier = ""
        if result[0] == result[1] == result[2]:
            if result[0] == "\U0001f48e":
                payout = bet * 15
                tier = "\U0001f48e\U0001f48e\U0001f48e JACKPOT! (15x)"
            elif result[0] == "\u2b50":
                payout = bet * 7
                tier = "\u2b50\u2b50\u2b50 MEGA WIN! (7x)"
            else:
                payout = bet * 3
                tier = "Three of a kind! (3x)"
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            payout = int(bet * 1.5)
            tier = "Two of a kind! (1.5x)"

        net = payout - bet
        self._update_balance(ctx.author.id, net)

        if payout > 0:
            embed = make_embed(
                title="\U0001f3b0 Slot Machine",
                description=f"{display}\n\n\U0001f389 **{tier}**\nYou won **{payout}** dabloons!",
                color=Colors.SUCCESS, ctx=ctx
            )
        else:
            embed = make_embed(
                title="\U0001f3b0 Slot Machine",
                description=f"{display}\n\nBetter luck next time! You lost **{bet}** dabloons.",
                color=Colors.ERROR, ctx=ctx
            )
        await ctx.send(embed=embed)

    # ── Blackjack ───────────────────────────────────────────

    @commands.hybrid_command(aliases=["bj"])
    async def blackjack(self, ctx, bet: int = 10):
        """Play blackjack against the dealer! Hit or stand."""
        if bet < 5:
            return await ctx.send(embed=error_embed("Minimum bet is **5** dabloons.", ctx))
        bal = self._get_balance(ctx.author.id)
        if bal < bet:
            return await ctx.send(embed=error_embed(f"You only have **{bal}** dabloons.", ctx))
        self._update_balance(ctx.author.id, -bet)

        cards = list(range(2, 11)) + [10, 10, 10, 11]
        player = [random.choice(cards), random.choice(cards)]
        dealer = [random.choice(cards), random.choice(cards)]

        def hand_val(hand):
            total = sum(hand)
            aces = hand.count(11)
            while total > 21 and aces:
                total -= 10
                aces -= 1
            return total

        def hand_str(hand):
            return " ".join(f"`{c}`" for c in hand)

        def make_bj_embed(footer_msg=""):
            pv = hand_val(player)
            embed = make_embed(title="\U0001f0cf Blackjack", color=Colors.DARK, ctx=ctx)
            embed.add_field(name=f"\U0001f464 You ({pv})", value=hand_str(player), inline=True)
            embed.add_field(name=f"\U0001f916 Dealer (?)", value=f"`{dealer[0]}` `?`", inline=True)
            if footer_msg:
                embed.add_field(name="", value=footer_msg, inline=False)
            return embed

        msg = await ctx.send(embed=make_bj_embed("Press **Hit** or **Stand**."))

        class BJView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.result = None

            @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="\U0001f4a5")
            async def hit(self, interaction: discord.Interaction, button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Not your game!", ephemeral=True)
                player.append(random.choice(cards))
                if hand_val(player) >= 21:
                    self.stop()
                    for item in self.children:
                        item.disabled = True
                    await interaction.response.edit_message(embed=make_bj_embed(), view=self)
                else:
                    await interaction.response.edit_message(embed=make_bj_embed("Press **Hit** or **Stand**."))

            @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="\u270b")
            async def stand(self, interaction: discord.Interaction, button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Not your game!", ephemeral=True)
                self.stop()
                for item in self.children:
                    item.disabled = True
                await interaction.response.edit_message(embed=make_bj_embed(), view=self)

        view = BJView()
        await msg.edit(view=view)
        await view.wait()

        # Dealer plays
        while hand_val(dealer) < 17:
            dealer.append(random.choice(cards))

        pv = hand_val(player)
        dv = hand_val(dealer)

        result_embed = make_embed(title="\U0001f0cf Blackjack \u2014 Results", color=Colors.DARK, ctx=ctx)
        result_embed.add_field(name=f"\U0001f464 You ({pv})", value=hand_str(player), inline=True)
        result_embed.add_field(name=f"\U0001f916 Dealer ({dv})", value=hand_str(dealer), inline=True)

        if pv > 21:
            result_embed.add_field(name="\U0001f4a2 Result", value=f"**Bust!** You lost **{bet}** dabloons.", inline=False)
            result_embed.color = Colors.ERROR
        elif dv > 21 or pv > dv:
            winnings = bet * 2
            self._update_balance(ctx.author.id, winnings)
            result_embed.add_field(name="\U0001f389 Result", value=f"**You win!** +**{winnings}** dabloons!", inline=False)
            result_embed.color = Colors.SUCCESS
        elif pv == dv:
            self._update_balance(ctx.author.id, bet)
            result_embed.add_field(name="\U0001f91d Result", value=f"**Push!** Your **{bet}** dabloons were returned.", inline=False)
            result_embed.color = Colors.WARNING
        else:
            result_embed.add_field(name="\U0001f4a2 Result", value=f"**Dealer wins!** You lost **{bet}** dabloons.", inline=False)
            result_embed.color = Colors.ERROR

        await msg.edit(embed=result_embed, view=None)

    # ── High Low ────────────────────────────────────────────

    @commands.hybrid_command(aliases=["hl"])
    async def highlow(self, ctx, bet: int = 5):
        """Guess if the next number is higher or lower."""
        if bet < 1:
            return await ctx.send(embed=error_embed("Minimum bet is **1** dabloon.", ctx))
        bal = self._get_balance(ctx.author.id)
        if bal < bet:
            return await ctx.send(embed=error_embed(f"You only have **{bal}** dabloons.", ctx))

        number = random.randint(1, 100)
        embed = make_embed(
            title="\u2b06\ufe0f\u2b07\ufe0f High-Low",
            description=f"The number is **{number}**.\nWill the next be **higher** or **lower**?",
            color=Colors.INFO, ctx=ctx
        )

        class HLView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.choice = None

            @discord.ui.button(label="Higher", style=discord.ButtonStyle.success, emoji="\u2b06\ufe0f")
            async def higher(self, interaction: discord.Interaction, button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Not your game!", ephemeral=True)
                self.choice = "high"
                self.stop()
                await interaction.response.defer()

            @discord.ui.button(label="Lower", style=discord.ButtonStyle.danger, emoji="\u2b07\ufe0f")
            async def lower(self, interaction: discord.Interaction, button):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Not your game!", ephemeral=True)
                self.choice = "low"
                self.stop()
                await interaction.response.defer()

        view = HLView()
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.choice is None:
            return await msg.edit(embed=error_embed("Timed out!", ctx), view=None)

        next_num = random.randint(1, 100)
        won = (view.choice == "high" and next_num > number) or (view.choice == "low" and next_num < number)

        if next_num == number:
            self._update_balance(ctx.author.id, bet)
            result = make_embed(
                title="\u2b06\ufe0f\u2b07\ufe0f High-Low \u2014 Tie!",
                description=f"Next number: **{next_num}** \u2014 Same number! Bet returned.",
                color=Colors.WARNING, ctx=ctx
            )
        elif won:
            self._update_balance(ctx.author.id, bet)
            result = make_embed(
                title="\u2b06\ufe0f\u2b07\ufe0f High-Low \u2014 You Win!",
                description=f"Next number: **{next_num}** \u2014 You won **{bet * 2}** dabloons! \U0001f389",
                color=Colors.SUCCESS, ctx=ctx
            )
        else:
            self._update_balance(ctx.author.id, -bet)
            result = make_embed(
                title="\u2b06\ufe0f\u2b07\ufe0f High-Low \u2014 You Lose!",
                description=f"Next number: **{next_num}** \u2014 You lost **{bet}** dabloons.",
                color=Colors.ERROR, ctx=ctx
            )
        await msg.edit(embed=result, view=None)

    # ── Rock Paper Scissors ─────────────────────────────────

    @commands.hybrid_command(aliases=["rockpaperscissors"])
    async def rps(self, ctx, bet: int = 0):
        """Play Rock Paper Scissors against the bot."""
        if bet > 0:
            bal = self._get_balance(ctx.author.id)
            if bal < bet:
                return await ctx.send(embed=error_embed(f"You only have **{bal}** dabloons.", ctx))

        embed = make_embed(
            title="\u270a\u270b\u2702\ufe0f Rock Paper Scissors",
            description="Choose your weapon!",
            color=Colors.BLURPLE, ctx=ctx
        )

        class RPSView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.choice = None

            async def handle(self, interaction, choice):
                if interaction.user.id != ctx.author.id:
                    return await interaction.response.send_message("Not your game!", ephemeral=True)
                self.choice = choice
                self.stop()
                await interaction.response.defer()

            @discord.ui.button(label="Rock", emoji="\u270a")
            async def rock(self, interaction, button):
                await self.handle(interaction, "rock")

            @discord.ui.button(label="Paper", emoji="\u270b")
            async def paper(self, interaction, button):
                await self.handle(interaction, "paper")

            @discord.ui.button(label="Scissors", emoji="\u2702\ufe0f")
            async def scissors(self, interaction, button):
                await self.handle(interaction, "scissors")

        view = RPSView()
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        if not view.choice:
            return await msg.edit(embed=error_embed("Timed out!", ctx), view=None)

        bot_choice = random.choice(["rock", "paper", "scissors"])
        emoji_map = {"rock": "\u270a", "paper": "\u270b", "scissors": "\u2702\ufe0f"}

        if view.choice == bot_choice:
            outcome = "It's a **tie**!"
            color = Colors.WARNING
        elif (view.choice == "rock" and bot_choice == "scissors") or \
             (view.choice == "paper" and bot_choice == "rock") or \
             (view.choice == "scissors" and bot_choice == "paper"):
            outcome = "You **win**!"
            color = Colors.SUCCESS
            if bet > 0:
                self._update_balance(ctx.author.id, bet)
                outcome += f" +**{bet}** dabloons!"
        else:
            outcome = "You **lose**!"
            color = Colors.ERROR
            if bet > 0:
                self._update_balance(ctx.author.id, -bet)
                outcome += f" -**{bet}** dabloons."

        result = make_embed(
            title="\u270a\u270b\u2702\ufe0f Rock Paper Scissors",
            description=f"You: {emoji_map[view.choice]} vs Bot: {emoji_map[bot_choice]}\n\n{outcome}",
            color=color, ctx=ctx
        )
        await msg.edit(embed=result, view=None)

    # ── Russian Roulette ────────────────────────────────────

    @commands.hybrid_command(aliases=["rr"])
    async def russianroulette(self, ctx, bet: int = 10):
        """Take a chance! 1 in 6 chance to lose, 5 in 6 to win double."""
        if bet < 1:
            return await ctx.send(embed=error_embed("Minimum bet is **1** dabloon.", ctx))
        bal = self._get_balance(ctx.author.id)
        if bal < bet:
            return await ctx.send(embed=error_embed(f"You only have **{bal}** dabloons.", ctx))

        chamber = random.randint(1, 6)
        if chamber == 1:
            self._update_balance(ctx.author.id, -bet)
            embed = make_embed(
                title="\U0001f52b Russian Roulette",
                description=f"**BANG!** \U0001f4a5 You lost **{bet}** dabloons!",
                color=Colors.ERROR, ctx=ctx
            )
        else:
            winnings = int(bet * 0.4)
            self._update_balance(ctx.author.id, winnings)
            embed = make_embed(
                title="\U0001f52b Russian Roulette",
                description=f"*Click.* You survived! \U0001f389 You won **{winnings}** dabloons!",
                color=Colors.SUCCESS, ctx=ctx
            )
        await ctx.send(embed=embed)

    # ── Trivia ──────────────────────────────────────────────

    @commands.hybrid_command()
    async def trivia(self, ctx):
        """Answer a random trivia question! Win 5 dabloons."""
        questions = [
            ("What planet is known as the Red Planet?", ["Mars", "Venus", "Jupiter", "Saturn"], 0),
            ("What is the chemical symbol for gold?", ["Au", "Ag", "Fe", "Cu"], 0),
            ("How many bones does the adult human body have?", ["206", "186", "256", "196"], 0),
            ("What year did the Titanic sink?", ["1912", "1905", "1920", "1898"], 0),
            ("What is the smallest country in the world?", ["Vatican City", "Monaco", "Nauru", "Malta"], 0),
            ("Who painted the Mona Lisa?", ["Leonardo da Vinci", "Michelangelo", "Raphael", "Donatello"], 0),
            ("What is the speed of light?", ["299,792 km/s", "150,000 km/s", "500,000 km/s", "199,792 km/s"], 0),
            ("How many hearts does an octopus have?", ["3", "2", "4", "1"], 0),
            ("What language has the most native speakers?", ["Mandarin Chinese", "English", "Spanish", "Hindi"], 0),
            ("What is the hardest natural substance?", ["Diamond", "Titanium", "Steel", "Quartz"], 0),
        ]
        q, options, correct = random.choice(questions)
        # Shuffle options while tracking correct answer
        correct_answer = options[correct]
        random.shuffle(options)
        correct_idx = options.index(correct_answer)

        embed = make_embed(title="\U0001f9e0 Trivia", description=f"**{q}**", color=Colors.BLURPLE, ctx=ctx)
        labels = ["A", "B", "C", "D"]
        for i, opt in enumerate(options):
            embed.add_field(name=f"{labels[i]})", value=opt, inline=True)

        class TriviaView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=20)
                self.answered = None
                for i in range(4):
                    btn = discord.ui.Button(label=labels[i], style=discord.ButtonStyle.primary)
                    btn.callback = self.make_callback(i)
                    self.add_item(btn)

            def make_callback(self, idx):
                async def callback(interaction: discord.Interaction):
                    if interaction.user.id != ctx.author.id:
                        return await interaction.response.send_message("Not your game!", ephemeral=True)
                    self.answered = idx
                    self.stop()
                    await interaction.response.defer()
                return callback

        view = TriviaView()
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.answered is None:
            return await msg.edit(embed=error_embed(f"Time's up! The answer was **{correct_answer}**.", ctx), view=None)

        if view.answered == correct_idx:
            self._update_balance(ctx.author.id, 5)
            result = make_embed(
                title="\U0001f9e0 Trivia \u2014 Correct! \U0001f389",
                description=f"**{correct_answer}** is right! You earned **5** dabloons!",
                color=Colors.SUCCESS, ctx=ctx
            )
        else:
            result = make_embed(
                title="\U0001f9e0 Trivia \u2014 Wrong!",
                description=f"The correct answer was **{correct_answer}**.",
                color=Colors.ERROR, ctx=ctx
            )
        await msg.edit(embed=result, view=None)

    # ── Guess the Number ────────────────────────────────────

    @commands.hybrid_command(aliases=["guess"])
    async def guessnumber(self, ctx, max_num: int = 10):
        """Guess a number between 1 and max (default 10). 3 attempts!"""
        if max_num < 2:
            return await ctx.send(embed=error_embed("Max must be at least 2.", ctx))
        answer = random.randint(1, max_num)
        embed = make_embed(
            title="\U0001f522 Guess the Number",
            description=f"I'm thinking of a number between **1** and **{max_num}**.\nYou have **3** attempts. Type your guess!",
            color=Colors.INFO, ctx=ctx
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        for attempt in range(3):
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=15)
            except asyncio.TimeoutError:
                return await ctx.send(embed=error_embed(f"Time's up! The number was **{answer}**.", ctx))
            guess = int(msg.content)
            if guess == answer:
                reward = max(1, max_num // 2)
                self._update_balance(ctx.author.id, reward)
                return await ctx.send(embed=success_embed(f"Correct! The number was **{answer}**! +**{reward}** dabloons! \U0001f389", ctx))
            elif guess < answer:
                await ctx.send(embed=make_embed(description=f"\u2b06\ufe0f Higher! ({2 - attempt} attempts left)", color=Colors.WARNING, ctx=ctx))
            else:
                await ctx.send(embed=make_embed(description=f"\u2b07\ufe0f Lower! ({2 - attempt} attempts left)", color=Colors.WARNING, ctx=ctx))

        await ctx.send(embed=error_embed(f"Out of attempts! The number was **{answer}**.", ctx))

    # ── Tic Tac Toe ─────────────────────────────────────────

    @commands.hybrid_command(aliases=["ttt"])
    async def tictactoe(self, ctx, opponent: discord.Member = None):
        """Play Tic Tac Toe against another member or the bot."""
        if opponent and opponent.id == ctx.author.id:
            return await ctx.send(embed=error_embed("You can't play against yourself!", ctx))
        if opponent and opponent.bot and opponent.id != self.bot.user.id:
            return await ctx.send(embed=error_embed("You can't play against other bots!", ctx))

        vs_bot = opponent is None or opponent.id == self.bot.user.id
        opponent = opponent or self.bot.user
        board = ["\u2b1c"] * 9
        current = ctx.author
        symbols = {ctx.author.id: "\u274c", opponent.id: "\u2b55"}

        def render():
            rows = ""
            for i in range(0, 9, 3):
                rows += " ".join(board[i:i+3]) + "\n"
            return rows

        def check_win():
            wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
            for a, b, c in wins:
                if board[a] == board[b] == board[c] != "\u2b1c":
                    return board[a]
            if "\u2b1c" not in board:
                return "tie"
            return None

        def bot_move():
            empty = [i for i, v in enumerate(board) if v == "\u2b1c"]
            return random.choice(empty) if empty else None

        class TTTButton(discord.ui.Button):
            def __init__(self, idx):
                super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=idx // 3)
                self.idx = idx

            async def callback(self, interaction: discord.Interaction):
                nonlocal current
                if interaction.user.id != current.id:
                    return await interaction.response.send_message("Not your turn!", ephemeral=True)
                if board[self.idx] != "\u2b1c":
                    return await interaction.response.send_message("Spot taken!", ephemeral=True)

                board[self.idx] = symbols[current.id]
                self.label = symbols[current.id]
                self.disabled = True
                self.style = discord.ButtonStyle.success if symbols[current.id] == "\u274c" else discord.ButtonStyle.danger

                winner = check_win()
                if winner:
                    for item in self.view.children:
                        item.disabled = True
                    if winner == "tie":
                        embed = make_embed(title="\u2696\ufe0f Tic Tac Toe \u2014 Tie!", description=render(), color=Colors.WARNING, ctx=ctx)
                    else:
                        win_name = ctx.author.display_name if winner == symbols[ctx.author.id] else opponent.display_name
                        embed = make_embed(title=f"\U0001f3c6 {win_name} wins!", description=render(), color=Colors.SUCCESS, ctx=ctx)
                    return await interaction.response.edit_message(embed=embed, view=self.view)

                current = opponent if current == ctx.author else ctx.author

                if vs_bot and current.id == opponent.id:
                    move = bot_move()
                    if move is not None:
                        board[move] = symbols[opponent.id]
                        btn = self.view.children[move]
                        btn.label = symbols[opponent.id]
                        btn.disabled = True
                        btn.style = discord.ButtonStyle.danger
                    current = ctx.author
                    winner = check_win()
                    if winner:
                        for item in self.view.children:
                            item.disabled = True
                        if winner == "tie":
                            embed = make_embed(title="\u2696\ufe0f Tic Tac Toe \u2014 Tie!", description=render(), color=Colors.WARNING, ctx=ctx)
                        else:
                            win_name = ctx.author.display_name if winner == symbols[ctx.author.id] else opponent.display_name
                            embed = make_embed(title=f"\U0001f3c6 {win_name} wins!", description=render(), color=Colors.SUCCESS, ctx=ctx)
                        return await interaction.response.edit_message(embed=embed, view=self.view)

                turn_name = current.display_name
                embed = make_embed(
                    title="\u274c\u2b55 Tic Tac Toe",
                    description=f"{render()}\n{turn_name}'s turn ({symbols[current.id]})",
                    color=Colors.BLURPLE, ctx=ctx
                )
                await interaction.response.edit_message(embed=embed, view=self.view)

        view = discord.ui.View(timeout=120)
        for i in range(9):
            view.add_item(TTTButton(i))

        embed = make_embed(
            title="\u274c\u2b55 Tic Tac Toe",
            description=f"{render()}\n{ctx.author.display_name}'s turn (\u274c)",
            color=Colors.BLURPLE, ctx=ctx
        )
        await ctx.send(embed=embed, view=view)

    # ── Word Scramble ───────────────────────────────────────

    @commands.hybrid_command(aliases=["scramble"])
    async def wordscramble(self, ctx):
        """Unscramble the word! Win 3 dabloons."""
        words = ["python", "discord", "gaming", "shadow", "coding", "server", "knight",
                 "dragon", "wizard", "galaxy", "planet", "matrix", "cipher", "phantom",
                 "eclipse", "rocket", "nebula", "prism", "storm", "thunder"]
        word = random.choice(words)
        scrambled = list(word)
        while "".join(scrambled) == word:
            random.shuffle(scrambled)
        scrambled = "".join(scrambled)

        embed = make_embed(
            title="\U0001f500 Word Scramble",
            description=f"Unscramble this word:\n\n**`{scrambled.upper()}`**\n\nYou have 20 seconds!",
            color=Colors.PURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=20)
        except asyncio.TimeoutError:
            return await ctx.send(embed=error_embed(f"Time's up! The word was **{word}**.", ctx))

        if msg.content.lower().strip() == word:
            self._update_balance(ctx.author.id, 3)
            await ctx.send(embed=success_embed(f"Correct! The word was **{word}**! +**3** dabloons! \U0001f389", ctx))
        else:
            await ctx.send(embed=error_embed(f"Wrong! The word was **{word}**.", ctx))


async def setup(bot):
    await bot.add_cog(Games(bot))
