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
from discord.ext import commands

from .utils import checks


class ChannelUtils(object):
    '''A utility to mimic Teamspeak mechanics, allowing creation of temporary channels lasting one half hour for users'''
    def __init__(self, bot):
        self.bot = bot
        self.current_users = dict()
        self.current_channels = dict()
        self.bot.shutdowns.append(self.shutdown)
        for guild in self.bot.guilds:
            self.current_users[guild] = list()
            self.current_channels[guild] = list()

    async def shutdown(self):
        for channel in self.current_channels:
            channel.delete()

    @commands.group(aliases=['ch'])
    @checks.no_pm()
    async def channel(self, ctx):
        '''Shows ;help channel, refer to that for command usage'''
        if ctx.invoked_subcommand is None:
            ctx.message.content = ";help channel"
            await self.bot.process_commands(ctx.message)

    @checks.chcreate_or_permissions(manage_channels=True)
    @channel.command(aliases=['cr'])
    @checks.no_pm()
    async def create(self, ctx, limit: int, *, name: str):
        '''Requires the role of 'Create Channel' Create a temporary text channel,
        where limit is the user limit and name is the name of the channel.
        Set the limit to "0" for no limit. Do ?channel for help'''
        if ctx.guild not in self.current_users:
            self.current_users[ctx.guild] = list()
            self.current_channels[ctx.guild] = list()
        try:
            guild = ctx.message.guild
            if ctx.message.author not in self.current_users[guild]:
                author = ctx.message.author
                if not name:
                    name = author.name
                channel = await guild.create_voice_channel(name)
                if limit:
                    await channel.edit(user_limit=limit)
                await ctx.send('`Channel {0} created, it will expire in 1 Hour`'.format(name))
                self.current_users[guild].append(author.id)
                info = (author, channel, ctx.message.guild)
                self.current_channels[guild].append(info)
                ch = await self.bot.wait_for("channel_delete", check=lambda dc: dc.id == channel.id, timeout=3600)
                if ch is not None:
                    self.current_channels[guild].remove(info)
                    self.current_users[guild].remove(author.id)
                else:
                    if ctx.message.author in self.current_users[guild]:
                        try:
                            await channel.delete()
                            self.current_channels[guild].remove(info)
                            self.current_users[guild].remove(author.id)
                            await ctx.send(author.mention + " `your channel has expired`")
                        except discord.NotFound:
                            self.current_channels[guild].remove(info)
                            self.current_users[guild].remove(author.id)
            else:
                await ctx.send('`You already have a channel in use!`')
        except discord.errors.Forbidden:
            await ctx.send('`This command is disabled in this guild`')

    @channel.command()
    @checks.no_pm()
    async def rename(self, ctx, *, name : str):
        """Rename your voice channel"""
        try:
            if self.current_channels:
                changed = False
                for channel in self.current_channels[ctx.message.guild]:
                    if channel[0] == ctx.message.author:
                        await channel[1].edit(name=name)
                        changed = True
                if not changed:
                    await ctx.send('`You do not currently have a channel to edit`')
                
        except discord.errors.Forbidden as err:
            await ctx.send('`This command is disabled in this guild`')

    @channel.command()
    @checks.no_pm()
    async def limit(self, ctx, *, limit : int):
        """Change your voice channel's user limit"""
        try:
            if self.current_channels:
                for channel in self.current_channels[ctx.message.guild]:
                    if channel[0] == ctx.message.author:
                        await channel[1].edit(user_limit=limit)
                        break
        except discord.errors.Forbidden:
            await ctx.send('`This command is disabled in this guild`')

    @channel.command()
    @checks.no_pm()
    async def delete(self, ctx):
        '''Delete your voice channel'''
        if ctx.message.author in self.current_users[ctx.message.guild]:
            for channel in self.current_channels[ctx.message.guild]:
                if channel[0] == ctx.message.author:
                    await channel[1].delete()
                    self.current_channels[ctx.message.guild].remove(channel)
                    self.current_users[ctx.message.guild].remove(ctx.message.author)
                    await ctx.send('`Your channel has been deleted`')
        else:
            ctx.send('`You do not currently have a channel`')

    @channel.command()
    @checks.no_pm()
    async def setusers(self, ctx, *, users: discord.Member):
        '''Change the users allowed in the channel'''
        if ctx.message.author in self.current_users[ctx.message.guild]:
            for channel in self.current_channels[ctx.message.guild]:
                if channel[0] == ctx.message.author:
                    override = discord.PermissionOverwrite()
                    override.connect = True
                    await channel[1].set_permissions(ctx.message.author, override)
                    override.connect = False
                    await channel[1].set_permissions(ctx.message.guild.default_role, override)
                    override.connect = True
                    for user in ctx.message.mentions:
                        await channel[1].set_permissions(user, override)
                    await ctx.send("` Permissions added for " + ", ".join([mention.name for mention in ctx.message.mentions]) + "`")
        else:
            await ctx.send("You don't currently have a channel!")

