#!/usr/bin/python3
# Copyright (c) 2016-2017, henry232323
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
import io
import re
import os
import json
import base64
import asyncio
import discord
import aiohttp
import async_timeout
from time import time
from html import unescape
from random import choice
from cogs.utils import checks
from collections import Counter
from discord.ext import commands
from binascii import Error as PaddingError
from bs4 import BeautifulSoup

class Misc(object):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.bot.shutdowns.append(self.shutdown)

    async def shutdown(self):
        self.session.close()

    @commands.command()
    async def ping(self, ctx):
        '''
        Test the bot's connection ping
        '''
        msg = "P{0}ng".format(choice("aeiou"))
        a = time()
        ping = await ctx.send(msg)
        b = time()
        await self.bot.edit_message(ping, " ".join([msg,"`{:.3f}ms`".format((b-a)*1000)]))

    @commands.command()
    async def info(self, ctx):
        """Bot Info"""
        me = ctx.guild.me
        appinfo = await self.bot.application_info()
        embed = discord.Embed(
                              color=me.top_role.color.value,
                              )
        embed.set_author(name=me.display_name, icon_url=appinfo.owner.avatar_url)
        embed.add_field(name="Author", value='Henry#6174 (Discord ID: 122739797646245899)')
        embed.add_field(name="Library", value='discord.py (Python)')
        embed.add_field(name="Uptime", value=await self.bot.get_bot_uptime())
        embed.add_field(name="Servers", value="{} servers".format(len(self.bot.guilds)))
        embed.add_field(name="Commands Run", value='{} commands'.format(sum(self.bot.commands_used.values())))

        total_members = sum(len(s.members) for s in self.bot.guilds)
        total_online = sum(1 for m in self.bot.get_all_members() if m.status != discord.Status.offline)
        unique_members = set(self.bot.get_all_members())
        unique_online = sum(1 for m in unique_members if m.status != discord.Status.offline)
        channel_types = Counter(isinstance(c, discord.TextChannel) for c in self.bot.get_all_channels())
        voice = channel_types[False]
        text = channel_types[True]
        embed.add_field(name="Total Members", value='{} ({} online)'.format(total_members, total_online))
        embed.add_field(name="Unique Members", value='{} ({} online)'.format(len(unique_members), unique_online))
        embed.add_field(name="Channels", value='{} text channels, {} voice channels'.format(text, voice))

        embed.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(delete_after=60, embed=embed)

    @commands.command()
    async def totalcmds(self, ctx):
        '''Get totals of commands and their number of uses'''
        await ctx.send('\n'.join("{0}: {1}".format(val[0], val[1]) for val in self.bot.commands_used.items()))

    @commands.command()
    async def source(self, ctx, command: str = None):
        """Displays my full source code or for a specific command.
        To display the source code of a subcommand you have to separate it by
        periods, e.g. tag.create for the create subcommand of the tag command.
        """
        source_url = 'https://github.com/henry232323/Typheus'
        if command is None:
            await ctx.send(source_url)
            return

        code_path = command.split('.')
        obj = self.bot
        for cmd in code_path:
            try:
                obj = obj.get_command(cmd)
                if obj is None:
                    await ctx.send('Could not find the command ' + cmd)
                    return
            except AttributeError:
                await ctx.send('{0.name} command has no subcommands'.format(obj))
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

        await ctx.send(final_url)

    @commands.command()
    async def undertext(self, ctx, sprite: str, *, text: str):
        """Create an Undertale style text box
        https://github.com/valrus/undertale-dialog-generator
        Example Usage: ;undertext sprites/Papyrus/1.png "Sans!!!\""""
        try:
            async with ctx.channel.typing():
                sprite = "undertale/static/images/" + sprite
                response, data = await self.fetch('http://ianmccowan.nfshost.com/undertale/submit',
                                       params={'text': text,
                                               'moodImg': sprite})
                fp = io.BytesIO(base64.b64decode(data))
                await ctx.send(file=fp, filename=text + ".png")

        except PaddingError:
            await ctx.send("API failure! Error Code: {} (You probably got the image path wrong)".format(response.status))

    @commands.command()
    async def uptime(self, ctx):
        """Check bot's uptime"""
        await ctx.send("```{}```".format(await self.bot.get_bot_uptime()))

    async def fetch(self, *args, **kwargs):
        with async_timeout.timeout(10):
            async with self.session.get(*args, **kwargs) as response:
                return response, await response.text()

    @commands.command()
    async def pol(self, ctx):
        """Do you like /pol?"""
        with ctx.channel.typing():
            for x in range(5):
                try:
                    response, data = await self.fetch('https://a.4cdn.org/pol/catalog.json')
                    api = json.loads(data)
                    html = choice(api[0]["threads"])["com"]
                    snd = BeautifulSoup(html, 'html.parser').get_text()
                    break
                except IndexError:
                    pass
            else:
                snd = "Failed to get a post!"
            await ctx.send(snd, delete_after=300)

    @commands.command()
    @checks.nsfw_channel()
    async def fchan(self, ctx, board: str):
        """4 cham"""
        with ctx.channel.typing():
            for x in range(5):
                try:
                    response, data = await self.fetch('https://a.4cdn.org/{}/catalog.json'.format(board))
                    api = json.loads(data)
                    html = choice(api[0]["threads"])["com"]
                    snd = BeautifulSoup(html, 'html.parser').get_text()
                    break
                except IndexError:
                    pass
            else:
                snd = "Failed to get a post!"
            await ctx.send(snd, delete_after=300)

    @commands.command(aliases=["seduce", "seduceme"])
    async def sm(self, ctx):
        await ctx.send("http://gifsec.com/wp-content/uploads/GIF/2014/08/GIF-Seduce-me-Seducing-Seduced-TF2-Team-Fortress-2-Spy-Seduce-me-now-GIF.gif", delete_after=60)

    @commands.command()
    async def donate(self, ctx):
        await ctx.send("If you'd like, you can donate to me here: https://ko-fi.com/henrys")
