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
    async def ping(self):
        '''
        Test the bot's connection ping
        '''
        msg = "P{0}ng".format(choice("aeiou"))
        a = time.time()
        ping = await self.bot.say(msg)
        b = time.time()
        await self.bot.edit_message(ping, " ".join([msg,"`{:.3f}ms`".format((b-a)*1000)]))

    @commands.command()
    async def info(self, ctx):
        """Bot Info"""
        result = ['**About Me:**']
        result.append('- Author: Henry#6174 (Discord ID: 122739797646245899)')
        result.append('- Library: discord.py (Python)')
        result.append('- Uptime: {}'.format(await self.bot.get_bot_uptime()))
        result.append('- Servers: {}'.format(len(self.bot.guilds)))
        result.append('- Commands Run: {}'.format(sum(self.bot.commands_used.values())))

        total_members = sum(len(s.members) for s in self.bot.guilds)
        total_online = sum(1 for m in self.bot.get_all_members() if m.status != discord.Status.offline)
        unique_members = set(self.bot.get_all_members())
        unique_online = sum(1 for m in unique_members if m.status != discord.Status.offline)
        channel_types = Counter(isinstance(c, discord.TextChannel) for c in self.bot.get_all_channels())
        voice = channel_types[False]
        text = channel_types[True]
        result.append('- Total Members: {} ({} online)'.format(total_members, total_online))
        result.append('- Unique Members: {} ({} online)'.format(len(unique_members), unique_online))
        result.append('- {} text channels, {} voice channels'.format(text, voice))

        await ctx.send('\n'.join(result), delete_after=20)

    @commands.command()
    async def totalcmds(self):
        '''Get totals of commands and their number of uses'''
        await self.bot.say('\n'.join("{0}: {1}".format(val[0], val[1]) for val in self.bot.commands_used.items()))

    @commands.command()
    async def source(self, command : str = None):
        """Displays my full source code or for a specific command.
        To display the source code of a subcommand you have to separate it by
        periods, e.g. tag.create for the create subcommand of the tag command.
        """
        source_url = 'https://github.com/henry232323/Typheus'
        if command is None:
            await self.bot.say(source_url)
            return

        code_path = command.split('.')
        obj = self.bot
        for cmd in code_path:
            try:
                obj = obj.get_command(cmd)
                if obj is None:
                    await self.bot.say('Could not find the command ' + cmd)
                    return
            except AttributeError:
                await self.bot.say('{0.name} command has no subcommands'.format(obj))
                return

        # since we found the command we're looking for, presumably anyway, let's
        # try to access the code itself
        src = obj.callback.__code__

        if not obj.callback.__module__.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(src.co_filename).replace('\\', '/')
            final_url = '<{}/tree/master/{}#L{}>'.format(source_url, location, src.co_firstlineno)
        else:
            location = obj.callback.__module__.replace('.', '/') + '.py'
            base = 'https://github.com/Rapptz/discord.py'
            final_url = '<{}/blob/master/{}#L{}>'.format(base, location, src.co_firstlineno)

        await self.bot.say(final_url)

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
            await ctx.send("API failure! Error Code: {} (You probably got the image path wrong)".format(response.status))


    @commands.command()
    async def uptime(self, ctx):
        """Check bot's uptime"""
        await ctx.send("```{}```".format(await self.bot.get_bot_uptime()))
