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
import io
import os
import ujson as json
import psutil
import base64
import discord
import asyncio
import datetime
import async_timeout
from time import time
from random import choice
from textwrap import indent
from cogs.utils import checks
from collections import Counter
from discord.ext import commands
from binascii import Error as PaddingError
from bs4 import BeautifulSoup


class Misc(object):
    def __init__(self, bot):
        self.bot = bot
        self.emote = "\U0001F35F"
        self.session = self.bot.session

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
        me = self.bot.user if not ctx.guild else ctx.guild.me
        appinfo = await self.bot.application_info()
        embed = discord.Embed()
        embed.set_author(name=me.display_name, icon_url=appinfo.owner.avatar_url)
        embed.add_field(name="Author", value='Henry#6174 (Discord ID: 122739797646245899)')
        embed.add_field(name="Library", value='discord.py (Python)')
        embed.add_field(name="Uptime", value=await self.bot.get_bot_uptime())
        embed.add_field(name="Servers", value="{} servers".format(len(self.bot.guilds)))
        embed.add_field(name="Commands Run", value='{} commands'.format(sum(self.bot.commands_used.values())))

        total_members = sum(len(s.members) for s in self.bot.guilds)
        total_online = sum(1 for m in self.bot.get_all_members() if m.status != discord.Status.offline)
        unique_members = set(map(lambda x: x.id, self.bot.get_all_members()))
        channel_types = Counter(isinstance(c, discord.TextChannel) for c in self.bot.get_all_channels())
        voice = channel_types[False]
        text = channel_types[True]
        embed.add_field(name="Total Members", value='{} ({} online)'.format(total_members, total_online))
        embed.add_field(name="Unique Members", value='{}'.format(len(unique_members)))
        embed.add_field(name="Channels", value='{} text channels, {} voice channels'.format(text, voice))

        embed.add_field(name="CPU Percentage", value="{}%".format(psutil.Process(os.getpid()).cpu_percent()))
        embed.add_field(name="Memory Usage", value="{0:.2f} MB".format(await self.bot.get_ram()))
        embed.add_field(name="Observed Events", value=sum(self.bot.socket_stats.values()))

        embed.add_field(name="Source", value="https://github.com/henry232323/Typheus")


        embed.set_footer(text='Made with discord.py', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        await ctx.send(delete_after=60, embed=embed)

    @commands.command()
    async def totalcmds(self, ctx):
        '''Get totals of commands and their number of uses'''
        embed = discord.Embed()
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        for val in self.bot.commands_used.items():
            embed.add_field(name=val[0], value=val[1])
        embed.set_footer(text=str(ctx.message.created_at))
        await ctx.send(embed=embed)

    @commands.command(pass_context=True, no_pm=True)
    async def memberinfo(self, ctx, *, member: discord.Member = None):
        """
        Shows info about a member.
        This cannot be used in private messages. If you don't specify
        a member then the info returned will be yours.
        """
        if member is None:
            member = ctx.author

        roles = map(lambda x: x.name, member.roles)
        shared = sum(1 for m in self.bot.get_all_members() if m.id == member.id)
        voice = member.voice
        if voice is not None:
            voice = voice.channel
            other_people = len(voice.members) - 1
            voice_fmt = '{} with {} others' if other_people else '{} by themselves'
            voice = voice_fmt.format(voice.name, other_people)
        else:
            voice = 'Not connected.'

        entries = [
            ('Name', member.name),
            ('Discriminator', member.discriminator),
            ('ID', member.id),
            ('Joined', member.joined_at),
            ('Created', member.created_at),
            ('Roles', ', '.join(roles)),
            ('Servers', '{} shared'.format(shared)),
            ('Voice', voice),
            ('Avatar', member.avatar_url),
        ]

        embed = discord.Embed()
        embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=str(ctx.message.created_at))
        for name, value in entries:
            embed.add_field(name=name, value=value)
        await ctx.send(embed=embed)

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
                await ctx.send(file=discord.File(fp, filename=text + ".png"))

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
                except (IndexError, KeyError):
                    pass
            else:
                snd = "Failed to get a post!"
            await ctx.send(snd, delete_after=300)
            try:
                ctx.message.delete()
            except:
                pass

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
                except (IndexError, KeyError):
                    pass
            else:
                snd = "Failed to get a post!"
            await ctx.send(snd, delete_after=300)
            try:
                ctx.message.delete()
            except:
                pass

    @commands.command(aliases=["seduce", "seduceme"])
    async def sm(self, ctx):
        """Seduce me"""
        await ctx.send("http://gifsec.com/wp-content/uploads/GIF/2014/08/GIF-Seduce-me-Seducing-Seduced-TF2-Team-Fortress-2-Spy-Seduce-me-now-GIF.gif", delete_after=60)

    @commands.command()
    async def donate(self, ctx):
        """Donation information"""
        await ctx.send("Keeping the bots running takes money, "
                       "if several people would buy me a coffee each month, "
                       "I wouldn't have to worry about it coming out of my pocket. "
                       "If you'd like, you can donate to me here: https://ko-fi.com/henrys")

    @commands.command()
    async def feedback(self, ctx, *, feedback):
        """Give me some feedback on the bot"""
        with open("feedback.txt", "a+") as f:
            f.write(feedback + "\n")
        await ctx.send("Thank you for the feedback!")

    @commands.command(hidden=True)
    async def socketstats(self, ctx):
        delta = datetime.datetime.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes

        fmt = '%s socket events observed (%.2f/minute):\n%s'
        await ctx.send(fmt % (total, cpm, self.bot.socket_stats))

    @commands.command()
    async def help(self, ctx, *command):
        if command:
            fmt = "**{}**: _{}_"
            parts = list(command)
            main = parts.pop(0)
            if not parts and main in self.bot.cogs:
                cog = self.bot.get_cog(main)
                command = self.bot.get_cog_commands(main)
                dfmt = indent("\n".join(
                    fmt.format(x.qualified_name, x.help) for x in command),
                              prefix="\t")
                value = "**{0}**\n{1}\n__Subcommands:__\n{2}".format(main.upper(), cog.__doc__, dfmt
                                                                             )

                await ctx.send(value)
                return

            command = discord.utils.get(self.bot.commands, name=main)
            if not command:
                await ctx.send("Invalid command!")
                return
            if parts:
                subcommand = discord.utils.get(command.commands, name=parts.pop(0))
                if not subcommand:
                    await ctx.send("Invalid subcommand!")
                    return
                value = "**;{}**\n{}".format(subcommand.signature, subcommand.help)
            elif isinstance(command, commands.Group):
                dfmt = indent("\n".join(fmt.format(x.qualified_name[len(command.qualified_name) + 1:], x.help) for x in command.commands), prefix="\t")
                value = "**{0}**\n_;{3}_\n{1}\n__Subcommands:__\n{2}".format(main.upper(), command.help, dfmt, command.signature)
            else:
                value = "**;{}**\n{}".format(command.signature, command.help)

            await ctx.send(value)
            return

        desc = """
Typheus, a little discord bot by Henry#6174
**Add to your server:** https://discordapp.com/oauth2/authorize?client_id=284456340879966231&scope=bot&permissions=305196074
**Join the Support Server:** https://discord.gg/UYJb8fQ
;help {{command}} for more info on a command
{}
""".format("\n".join("{}: {}".format(n, c.emote) for n, c in self.bot.cogs.items() if c.emote))
        embed = discord.Embed(description=desc)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_footer(text="Made by Henry#6174 using discord.py", icon_url=(await self.bot.application_info()).owner.avatar_url)
        message = await ctx.author.send(embed=embed)

        emotes = {cog.emote: name for name, cog in self.bot.cogs.items() if cog.emote}
        emotes["\u274E"] = "EXIT"
        for emote in emotes:
            await message.add_reaction(emote)

        while True:
            try:
                r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == message.id, timeout=80)
            except asyncio.TimeoutError:
                await message.delete()
                await ctx.author.send("Menu timed out! ;help to go again")
                return

            if u.id == self.bot.user.id:
                continue

            try:
                await message.remove_reaction(r.emoji, u)
            except:
                pass

            if r.emoji not in emotes:
                continue

            if emotes[r.emoji] == "EXIT":
                await message.delete()
                return

            embed.clear_fields()
            fmt = "**{}**: {}"
            for command in self.bot.get_cog_commands(emotes[r.emoji]):
                defhelp = command.help
                if command.qualified_name == "help":
                    continue
                if isinstance(command, commands.Group):
                    value = "{}\n__Subcommands:__\n\t{}".format(defhelp,
                            "\n\t".join(fmt.format(x.qualified_name[len(command.qualified_name) + 1:], x.help) for x in command.commands))

                    if len(value) >= 1024:
                        value = "{}\n__Subcommands:__\n\t{}".format(defhelp,
                                                                  "\n\t".join(x.qualified_name[len(command.qualified_name) + 1:] for x in
                                                                            command.commands))
                else:
                    value = defhelp

                embed.add_field(name=command.qualified_name, value=value)

            await message.edit(embed=embed)