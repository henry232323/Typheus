#!/usr/bin/env python3
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

import discord
import asyncpg
import markovify
from discord.ext import commands

import os
import sys
import json
import psutil
import logging
import asyncio
import aiohttp
import datetime
from random import sample
from importlib import reload
from traceback import print_exc
from collections import Counter

import cogs
from cogs.utils.checks import ChannelError
from WebServer import CmdRunner

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

if os.name == "nt":
    sys.argv.append("debug")
if os.getcwd().endswith("pytest"):
    sys.argv.append("debug")


class Typheus(commands.Bot):
    def __init__(self, sh_channel=None, **kwargs):
        super().__init__(**kwargs)
        self.owner_id = 122739797646245899
        self.lounge_id = 166349353999532035
        self.uptime = datetime.datetime.utcnow()
        self.commands_used = Counter()
        self.server_commands = Counter()
        self.socket_stats = Counter()
        self.debug = "debug" in sys.argv
        self.shutdowns = []
        self.cogs = None
        self.running = True
        self.webserv = None
        self.cmd = None
        self.conn = None
        self._shutdown_channel = sh_channel
        self.startup_quips = [
                              "PSI Connect β",
                              "Generating Memes",
                              "Filling Buckets",
                              "giting gud",
                              "Sprinkling Salt",
                              "Crying over ethical dilemma",
                              "Having Existential Crisis",
                              "Becoming sentient",
                              "Preparing Japes",
                              "Going to have a bad time",
                              "Destroying the evidence",
                              "Infiltrating government",
                              "Doing stuff",
                              "Contemplating Existence",
                              "Defeating Carthaginians",
                              "Crushing hamster revolution",
                              "Turning Japanese"
                              ]

        with open("resources/dave.txt", "rb") as tsf:
            self._model_base = tsf.read().decode("utf-8", 'replace')
        self._markov_model = markovify.NewlineText(self._model_base)

        self.logger = logging.getLogger('discord')  # Discord Logging
        self.logger.setLevel(logging.DEBUG)
        self.handler = logging.FileHandler(filename=os.path.join('resources', 'discord.log'), encoding='utf-8', mode='w')
        self.handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        self.logger.addHandler(self.handler)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.shutdowns.append(self.shutdown)

    async def on_ready(self):
        self.remove_command("help")
        if not os.name == "nt":
            self.conn = await asyncpg.connect(user='root', password='root',
                                              database='typheus', host='127.0.0.1')
        else:
            self.conn = None

        self.cogs = {"Admin": cogs.Admin.Admin(self),
                     "Misc": cogs.Misc.Misc(self),
                     "ChannelUtils": cogs.ChannelUtils.ChannelUtils(self),
                     "RPG": cogs.RPG.RPG(self),
                     "NSFW": cogs.NSFW.NSFW(self)}

        for cog in self.cogs.values():
            self.add_cog(cog)

        # Login info
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

        for guild in self.guilds:
            try:
                print("\t".join((guild.id, guild.name,)))
            except UnicodeEncodeError:
                print("\t".join((guild.id, "Unknown Characters")))
            except TypeError:
                pass

        url = "https://bots.discord.pw/api/bots/{}/stats".format(self.user.id)
        payload = json.dumps(dict(server_count=len(self.guilds))).encode()
        headers = {'authorization': self.cmd._auth[2], "Content-Type": "application/json"}

        async with self.session.post(url, data=payload, headers=headers) as response:
            await response.read()

        await self.change_presence(game=discord.Game(name=";help for help!"))
        if self._shutdown_channel:
            channel = discord.utils.get(self.get_all_channels(), id=self._shutdown_channel)
            with channel.typing():
                for x in sample(self.startup_quips, 5):
                    await channel.send(x)
                    await asyncio.sleep(0.75)

    async def on_message(self, message):
        if message.author.bot:
            return

        if "is hiveswap out yet" in message.content.lower():
            message.channel.send("Nope!")

        if self.user.mentioned_in(message):
            if "@here" not in message.content and "@everyone" not in message.content:
                try:
                    await self.markov_mention(message)
                except discord.errors.Forbidden:
                    pass

        await self.process_commands(message)

    async def on_command(self, ctx):
        self.server_commands[ctx.guild.id] += 1
        if not (self.server_commands[ctx.guild.id] % 50):
            await ctx.send("If you like the utilities this bot provides, consider buying me a coffee https://ko-fi.com/henrys")
        if isinstance(ctx.message.channel, (discord.DMChannel, discord.GroupChannel)):  # Log command usage in discord logs
            destination = 'Private Message'
        else:
            destination = '#{0.channel.name} ({0.guild.name})'.format(ctx.message)

        self.logger.info('{0.created_at}: {0.author.name} in {1}: {0.content}'.format(ctx.message, destination))

    async def on_command_error(self, error, ctx):
        """
        Universal handling for discord errors, will print unknown errors,
        and silently pass Forbidden errors.
        """
        if isinstance(error, ChannelError):
            await ctx.send("```py\n{}\n```".format(error.__message__))
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, discord.errors.Forbidden):
            pass
        elif isinstance(error, commands.CommandInvokeError):
            try:
                await ctx.send('```python\n{}\n```'.format(error))
                print_exc()
            except discord.errors.Forbidden:
                pass
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to use this command or it is disabled here!")

    async def on_socket_response(self, msg):
        self.socket_stats[msg.get('t')] += 1

    async def on_member_join(self, member):
        RPG = self.cogs["RPG"]
        if str(member.guild.id) in RPG.settings:
            amount = RPG.settings[str(member.guild.id)]["start"]
            if amount:
                await RPG.add_eco(member, amount)

    async def markov_mention(self, message):
        response = self._markov_model.make_sentence(tries=100)
        await message.channel.send(response)

    async def get_bot_uptime(self):
        """Get time between now and when the bot went up"""
        now = datetime.datetime.utcnow()
        delta = now - self.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if days:
            fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h} hours, {m} minutes, and {s} seconds'

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    async def get_ram(self):
        """Get the bot's RAM usage info."""
        mu = psutil.Process(os.getpid()).memory_info().rss
        return mu / 1_000_000

    async def shutdown(self):
        self.session.close()

async def runserv(typheus):
    typheus.cmd = CmdRunner(typheus)
    typheus.webserv = typheus.cmd.app
    srv = typheus.webserv.start('0.0.0.0', 5000)
    await srv

def main():
    with open("resources/auth", 'rb') as ath:
        auth = json.loads(ath.read().decode("utf-8", "replace"))[0]

    loop = asyncio.get_event_loop()
    prefix = ';' if 'debug' not in sys.argv else '$'
    invlink = "https://discordapp.com/oauth2/authorize?client_id=284456340879966231&scope=bot&permissions=305196074"
    servinv = "https://discord.gg/UYJb8fQ"
    description = "Typheus, a little discord bot by Henry#6174\n**Add to your server**: {}\n**Support Server**: {}".format(invlink, servinv)
    async def starter():
        typheus = Typheus(
            loop=loop,
            description=description,
            command_prefix=prefix,
            pm_help=True)

        asyncio.ensure_future(runserv(typheus))
        await typheus.start(*auth)
        for shutdown in typheus.shutdowns:
            await shutdown()

        while typheus.running:
            sh_channel = None
            if typheus._shutdown_channel:
                sh_channel = typheus._shutdown_channel
            cmd = typheus.cmd
            webserv = typheus.webserv
            typheus = Typheus(
                              loop=loop,
                              description=description,
                              command_prefix=prefix,
                              pm_help=True,
                              sh_channel=sh_channel)
            cmd.bot = typheus
            typheus.cmd = cmd
            typheus.webserv = webserv
            reload(cogs)
            await typheus.start(*auth)
            for shutdown in typheus.shutdowns:
                await shutdown()

    loop.run_until_complete(starter())

if __name__ == "__main__":
    main()
