import discord
from discord.ext import commands
import asyncio
import os
from collections import deque
from .embed_utils import make_embed, success_embed, error_embed, Colors


class Music(commands.Cog):
    """Music playback commands for voice channels."""
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    def _get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    async def _ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(embed=error_embed("You must be in a voice channel.", ctx))
            return False
        return True

    @commands.hybrid_command(aliases=["j", "connect"])
    async def join(self, ctx):
        """Join your voice channel."""
        if not await self._ensure_voice(ctx):
            return
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            if ctx.voice_client.channel != channel:
                await ctx.voice_client.move_to(channel)
                await ctx.send(embed=success_embed(f"Moved to **{channel.name}**.", ctx))
            else:
                await ctx.send(embed=make_embed(description=f"Already in **{channel.name}**.", color=Colors.INFO, ctx=ctx))
        else:
            await channel.connect()
            embed = make_embed(
                title="\U0001f3b5 Connected",
                description=f"Joined **{channel.name}**",
                color=Colors.SUCCESS, ctx=ctx
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["l", "dc", "disconnect"])
    async def leave(self, ctx):
        """Leave the voice channel."""
        if not ctx.voice_client:
            return await ctx.send(embed=error_embed("I'm not in a voice channel.", ctx))
        name = ctx.voice_client.channel.name
        self.queues.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await ctx.send(embed=make_embed(
            title="\U0001f44b Disconnected",
            description=f"Left **{name}**",
            color=Colors.ERROR, ctx=ctx
        ))

    @commands.hybrid_command()
    async def play(self, ctx, *, query: str):
        """Play audio from a YouTube URL or search term."""
        if not await self._ensure_voice(ctx):
            return
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        vc = ctx.voice_client
        embed = make_embed(
            title="\U0001f50d Searching...",
            description=f"Looking for: `{query}`",
            color=Colors.INFO, ctx=ctx
        )
        msg = await ctx.send(embed=embed)

        try:
            import yt_dlp
        except ImportError:
            return await msg.edit(embed=error_embed("yt-dlp is not installed.", ctx))

        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
        }
        ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        loop = asyncio.get_event_loop()

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                return info

        try:
            info = await loop.run_in_executor(None, extract)
        except Exception as e:
            return await msg.edit(embed=error_embed(f"Failed to find audio: {e}", ctx))

        url = info.get('url')
        title = info.get('title', 'Unknown')
        duration = info.get('duration', 0)
        thumb = info.get('thumbnail')
        webpage = info.get('webpage_url', '')

        mins, secs = divmod(duration, 60)

        if vc.is_playing():
            queue = self._get_queue(ctx.guild.id)
            queue.append({'url': url, 'title': title, 'duration': duration, 'thumb': thumb, 'requester': ctx.author, 'ffmpeg_opts': ffmpeg_opts})
            embed = make_embed(
                title="\U0001f4cb Added to Queue",
                description=f"**{title}**\nDuration: `{mins}:{secs:02d}`\nPosition: `#{len(queue)}`",
                color=Colors.INFO, ctx=ctx,
                thumbnail=thumb
            )
            return await msg.edit(embed=embed)

        def play_next(error):
            queue = self._get_queue(ctx.guild.id)
            if queue:
                next_song = queue.popleft()
                source = discord.FFmpegPCMAudio(next_song['url'], **next_song['ffmpeg_opts'])
                vc.play(source, after=play_next)

        source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)
        vc.play(source, after=play_next)

        embed = make_embed(
            title="\U0001f3b6 Now Playing",
            description=f"**{title}**\nDuration: `{mins}:{secs:02d}`",
            color=Colors.PURPLE, ctx=ctx,
            thumbnail=thumb
        )
        if webpage:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Open on YouTube", style=discord.ButtonStyle.link, url=webpage))
            await msg.edit(embed=embed, view=view)
        else:
            await msg.edit(embed=embed)

    @commands.hybrid_command(aliases=["pa"])
    async def pause(self, ctx):
        """Pause the current track."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send(embed=make_embed(description="\u23f8\ufe0f Paused.", color=Colors.WARNING, ctx=ctx))
        else:
            await ctx.send(embed=error_embed("Nothing is playing.", ctx))

    @commands.hybrid_command(aliases=["res"])
    async def resume(self, ctx):
        """Resume the paused track."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send(embed=make_embed(description="\u25b6\ufe0f Resumed.", color=Colors.SUCCESS, ctx=ctx))
        else:
            await ctx.send(embed=error_embed("Nothing is paused.", ctx))

    @commands.hybrid_command()
    async def stop(self, ctx):
        """Stop playing and clear the queue."""
        if ctx.voice_client:
            self.queues.pop(ctx.guild.id, None)
            ctx.voice_client.stop()
            await ctx.send(embed=make_embed(description="\u23f9\ufe0f Stopped and cleared queue.", color=Colors.ERROR, ctx=ctx))
        else:
            await ctx.send(embed=error_embed("Nothing to stop.", ctx))

    @commands.hybrid_command()
    async def skip(self, ctx):
        """Skip the currently playing track."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send(embed=make_embed(description="\u23ed\ufe0f Skipped.", color=Colors.INFO, ctx=ctx))
        else:
            await ctx.send(embed=error_embed("Nothing to skip.", ctx))

    @commands.hybrid_command(aliases=["q"])
    async def queue(self, ctx):
        """Show the current music queue."""
        q = self._get_queue(ctx.guild.id)
        if not q:
            return await ctx.send(embed=make_embed(description="The queue is empty.", color=Colors.INFO, ctx=ctx))
        desc = ""
        for i, song in enumerate(q):
            mins, secs = divmod(song['duration'], 60)
            desc += f"`{i+1}.` **{song['title']}** (`{mins}:{secs:02d}`)\n"
        embed = make_embed(
            title=f"\U0001f4cb Queue \u2014 {len(q)} tracks",
            description=desc[:2000], color=Colors.PURPLE, ctx=ctx
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["np", "nowplaying"])
    async def now(self, ctx):
        """Show what's currently playing."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send(embed=error_embed("Nothing is currently playing.", ctx))
        await ctx.send(embed=make_embed(
            description="\U0001f3b6 Music is currently playing!",
            color=Colors.PURPLE, ctx=ctx
        ))

    @commands.hybrid_command(aliases=["vol"])
    async def volume(self, ctx, vol: int):
        """Set the playback volume (0-100)."""
        if not ctx.voice_client:
            return await ctx.send(embed=error_embed("I'm not in a voice channel.", ctx))
        if vol < 0 or vol > 100:
            return await ctx.send(embed=error_embed("Volume must be between 0 and 100.", ctx))
        if ctx.voice_client.source:
            ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, volume=vol / 100)
        await ctx.send(embed=make_embed(
            description=f"\U0001f50a Volume set to **{vol}%**",
            color=Colors.INFO, ctx=ctx
        ))


async def setup(bot):
    await bot.add_cog(Music(bot))
