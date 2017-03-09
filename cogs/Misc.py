import io
import base64
import asyncio
import aiohttp
from binascii import Error as PaddingError

from cogs.utils import checks
from discord.ext import commands


class Misc(object):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def undertext(self, ctx, sprite: str, text: str):
        """Create an Undertale style text box
        https://github.com/valrus/undertale-dialog-generator
        Example Usage: ;undertext sprites/Papyrus/1.png "Sans!!!\""""
        try:
            words = text.split()
            lens = map(len, words)
            brk = 0
            ctr = 0
            lines = []
            for ix, leng in enumerate(lens):
                if ctr+leng > 25:
                    lines.append(" ".join(words[brk:ix]))
                    brk = ix
                    ctr = 0
                ctr += leng + 1
            lines.append(" ".join(words[brk:len(words)]))
            text = "\n".join(lines)
            async with ctx.channel.typing():
                async with aiohttp.ClientSession() as session:
                    sprite = "undertale/static/images/" + sprite
                    async with session.get('http://ianmccowan.nfshost.com/undertale/submit',
                                           params={'text': text,
                                                   'moodImg': sprite}) as response:
                        data = await response.read()
                    fp = io.BytesIO(base64.b64decode(data))
                    await ctx.send(file=fp, filename=text + ".png")
        except PaddingError:
            await ctx.send("API is down! Error Code: {}".format(response.status))


    @commands.command()
    async def uptime(self, ctx):
        """Check bot's uptime"""
        await ctx.send("```{}```".format(await self.bot.get_bot_uptime()))


