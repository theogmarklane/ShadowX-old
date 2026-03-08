import discord
from datetime import datetime


class Colors:
    PURPLE = 0x9b59b6
    SUCCESS = 0x2ecc71
    ERROR = 0xe74c3c
    WARNING = 0xf1c40f
    INFO = 0x3498db
    DARK = 0x2b2d31
    GOLD = 0xf39c12
    PINK = 0xe91e63
    BLURPLE = 0x5865F2


def make_embed(
    title=None, description=None, color=Colors.PURPLE,
    ctx=None, footer=None, thumbnail=None, image=None, author=None
):
    e = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if ctx:
        e.set_footer(
            text=f"Project SHDW \u2022 {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
    elif footer:
        e.set_footer(text=footer)
    if thumbnail:
        e.set_thumbnail(url=thumbnail)
    if image:
        e.set_image(url=image)
    if author:
        e.set_author(name=author.get("name", ""), icon_url=author.get("icon_url", ""))
    return e


def success_embed(description, ctx=None):
    return make_embed(description=f"\u2705 {description}", color=Colors.SUCCESS, ctx=ctx)


def error_embed(description, ctx=None):
    return make_embed(description=f"\u274c {description}", color=Colors.ERROR, ctx=ctx)


def warning_embed(description, ctx=None):
    return make_embed(description=f"\u26a0\ufe0f {description}", color=Colors.WARNING, ctx=ctx)
