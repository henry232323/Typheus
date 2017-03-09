import io
import base64
import asyncio
import aiohttp
from binascii import Error as PaddingError
from collections import Counter
import discord

from cogs.utils import checks
from discord.ext import commands


class Misc(object):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def info(self):
        """Bot Info"""
        revision = os.popen(r'git show -s HEAD --format="%s (%cr)"').read().strip()
        result = ['**About Me:**']
        result.append('- Author: Henry#6174 (Discord ID: 122739797646245899)')
        result.append('- Library: discord.py (Python)')
        result.append('- Uptime: {}'.format(self.bot.get_bot_uptime()))
        result.append('- Servers: {}'.format(len(self.bot.servers)))
        result.append('- Commands Run: {}'.format(sum(self.bot.commands_used.values())))

        total_members = sum(len(s.members) for s in self.bot.servers)
        total_online = sum(1 for m in self.bot.get_all_members() if m.status != discord.Status.offline)
        unique_members = set(self.bot.get_all_members())
        unique_online = sum(1 for m in unique_members if m.status != discord.Status.offline)
        channel_types = Counter(c.type for c in self.bot.get_all_channels())
        voice = channel_types[discord.ChannelType.voice]
        text = channel_types[discord.ChannelType.text]
        result.append('- Total Members: {} ({} online)'.format(total_members, total_online))
        result.append('- Unique Members: {} ({} online)'.format(len(unique_members), unique_online))
        result.append('- {} text channels, {} voice channels'.format(text, voice))

        msg = await self.bot.say('\n'.join(result))
        await asyncio.sleep(20)
        await self.bot.delete_message(msg)

    @commands.command()
    async def undertext(self, ctx, sprite: str, text: str):
        """Create an Undertale style text box
        https://github.com/valrus/undertale-dialog-generator
        Example Usage: ;undertext sprites/Papyrus/1.png "Sans!!!\""""
        try:
            words = text.split()
            lens = map(len, words)
            lines = []
            ctr = 0
            brk = 0
            for ix, leng in enumerate(lens):
                if ctr+leng > 25:
                    lines.append(" ".join(words[brk:ix]))
                    brk = ix
                    ctr = 0
                ctr += leng + 1
            lines.append(" ".join(words[brk:ix]))
            text = "\r\n".join(lines)
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
            await ctx.send("API failure! Error Code: {} (You probably got the image path wrong)".format(response.status))


    @commands.command()
    async def uptime(self, ctx):
        """Check bot's uptime"""
        await ctx.send("```{}```".format(await self.bot.get_bot_uptime()))


