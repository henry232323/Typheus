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
from .utils import checks, dataIO
from discord.ext import commands
import discord
from functools import wraps

json = dataIO.DataIO()


def server_complex_mode(func):
    @wraps(func)
    async def predicate(self, ctx, *args):
        if str(ctx.guild.id) not in self.settings or self.settings[str(ctx.message.guild.id)]["mode"] == 0:
            await ctx.send("This command requires complex mode to be enabled!"
                           " Use the `;inventory servmode` command to switch"
                           " to complex mode, where items are restricted to admin defined")
        else:
            await func(self, ctx, *args)

    return predicate

def server_eco_mode(func):
    @wraps(func)
    async def predicate(self, ctx, *args):
        if str(ctx.guild.id) not in self.settings or \
           self.settings[str(ctx.guild.id)]["mode"] is 0 or \
           self.settings[str(ctx.guild.id)]["eco"] is False:

            await ctx.send("To use this command the guild must be in complex mode and have economy enabled!"
                           " Use `inventory servmode complex` to change servmode to complex"
                           " and use `inventory useeco True` to use economy features")
        else:
            await func(self, ctx, *args)

    return predicate


class RPG(object):
    def __init__(self, bot):
        self.bot = bot
        self.bot.shutdowns.append(self.shutdown)
        file = "invdata/servers.json"
        if json.is_valid_json(file):
            self.settings = json.load_json(file)
        else:
            self.settings = dict()

        self.awaiting = dict()

    async def shutdown(self):
        json.save_json("invdata/servers.json", self.settings)

    def addserv(self, ctx, mode=1, items=None, ecc=False):
        if items is None:
            items = dict()
        self.settings[str(ctx.message.guild.id)] = dict(mode=mode, items=items, eco=ecc, cur="dollars")

    @commands.group(invoke_without_command=True, no_pm=True, aliases=['i', 'inv'])
    async def inventory(self, ctx, *, member: discord.Member=None):
        """Check your or another users inventory
        Usage: ;inventory @User"""
        if member is None:
            member = ctx.message.author

        inv = (await self.get_inv(member))["items"]
        fmap = map(lambda itm: "x{1} {0}".format(itm, inv[itm]), inv)
        fmt = "\n".join(fmap)
        if not fmt:
            await ctx.send("This inventory is empty!")
        else:
            await ctx.send("```\n{}\n```".format(fmt))

    @checks.mod_or_permissions()
    @inventory.command(no_pm=True)
    async def servmode(self, ctx, mode: str):
        """Change the guild inventory mode. Two modes, simple or complex, if simple, items of any name can be given
        else if the mode is complex, items must be specified"""
        mode = mode.lower()
        if str(ctx.message.guild.id) not in self.settings:
            if mode == "complex":
                self.addserv(ctx)
                await ctx.send("Mode changed to complex!")
                return
            else:
                await ctx.send("Mode changed to simple!")
                return
        if mode == "simple":
            self.settings[str(ctx.guild.id)]["mode"] = 0
            await ctx.send("Mode changed to simple!")
        elif mode == "complex":
            self.settings[str(ctx.guild.id)]["mode"] = 1
            await ctx.send("Mode changed to complex!")
        else:
            await ctx.send("Invalid mode!")

    @checks.mod_or_permissions()
    @inventory.command(no_pm=True)
    @server_complex_mode
    async def additem(self, ctx, name: str, *, data: str):
        """If guild mode is complex, add an item that can be given
        Usage: ;inventory additem itemname *data
        Where data is a newline separated list of attributes, for example
        ;i additem banana
        color: red
        value: 5
        Special identifiers include:
        value: a 'market' value, more implementation later
        Set data to 'None' for no data"""

        if "@everyone" in name or "@here" in name:
            await ctx.send("Forbidden words in item name (@everyone or @here)")
            return

        if data.lower() == "none":
            dfmt = ()
        else:
            dfmt = data.split("\n")
        fdict = dict()
        for item in dfmt:
            split = item.split(": ")
            key = split[0]
            val = ": ".join(split[1:])
            fdict[key] = val

        self.settings[str(ctx.guild.id)]['items'][name] = fdict
        await ctx.send("Added item {}".format(name))

    @checks.mod_or_inv()
    @inventory.command(no_pm=True)
    async def giveitem(self, ctx, item: str, num: int, *members: discord.Member):
        """Give an item a number of times to members
        Usage ;inventory giveitem itemname number *@Users"""
        num = abs(num)
        if str(ctx.guild.id) not in self.settings:
            self.addserv(ctx, mode=False)
        if self.settings[str(ctx.guild.id)]["mode"] == 0 or item in self.settings[str(ctx.guild.id)]["items"]:
            for member in members:
                await self.add_inv(member, (item, num))
                await ctx.send("Items given!")

        else:
            await ctx.send("Item is not available! (Add it or switch to simple mode)")

    @checks.mod_or_inv()
    @inventory.command(no_pm=True)
    async def takeitem(self, ctx, item: str, num: int, *members: discord.Member):
        """Take a number of an item from a user (won't go past 0)
        Same command usage as inventory giveitem, inversely"""
        num = abs(num)
        if self.settings[ctx.message.guild.id]["mode"] == 0 or item in self.settings[ctx.message.guild.id]["items"]:
            for member in members:
                await self.remove_inv(member, (item, num))
                await ctx.send("Items taken!")
        else:
            await ctx.send("Item is not available! (Add it or switch to simple mode)")

    async def get_inv(self, member):
        file = "invdata/{}.json".format(member.id)
        if json.is_valid_json(file):
            data = json.load_json(file)[str(member.guild.id)]
        else:
            data = dict(items=dict(), money=0)
        return data

    async def add_inv(self, member, *items):
        sid = str(member.guild.id)
        for item, num in items:
            file = "invdata/{}.json".format(member.id)
            if json.is_valid_json(file):
                data = json.load_json(file)
            else:
                data = {sid: dict(money=0, items=dict())}
            if sid not in data:
                data[sid] = dict()
                data[sid]['money'] = 0
                data[sid]['items'] = dict()
            if item in data[sid]['items']:
                data[sid]['items'][item] += num
            else:
                data[sid]['items'][item] = num
            json.save_json(file, data)

    async def remove_inv(self, member, *items):
        sid = str(member.guild.id)
        for item, num in items:
            try:
                file = "invdata/{}.json".format(member.id)
                if json.is_valid_json(file):
                    data = json.load_json(file)
                else:
                    data = {sid: dict(money=0, items=dict())}
                if sid not in data:
                    data[sid] = dict()
                    data[sid]['money'] = 0
                    data[sid]['items'] = dict()
                if item in data[sid]['items']:
                    if num > data[sid]['items'][item]:
                        raise ValueError("User has negative!")
                    elif num == data[sid]['items'][item]:
                        del data[sid]['items'][item]
                    else:
                        data[sid]['items'][item] -= num
                else:
                    data[sid]['items'][item] = 0
                    raise ValueError("User has negative!")
            finally:
                json.save_json(file, data)

    @inventory.command(no_pm=True)
    async def offer(self, ctx, other: discord.Member, *items: str):
        """Send a trade offer to another user
        Usage: ;inventory offer @Henry bananax3 applex2
        Separate the number of items with an x,
        include even if just one!"""
        self.awaiting[other] = (ctx, items)

    @inventory.command(no_pm=True)
    async def respond(self, ctx, other: discord.Member, *items: str):
        """Respond to a trade offer by another user
        Usage: ;inventory respond @Henry grapex8 applex3
        Separate the number of items with an x,
        include even if just one! To accept the trade use !accept @OtherPerson or !decline @OtherPerson"""
        sender = ctx.message.author
        if sender in self.awaiting and other == self.awaiting[sender][0].message.author:
            await ctx.send("Both parties say !accept @Other to accept the trade or !decline @Other to decline")

            def check(message):
                if not message.content.startswith(("!accept", "!decline",)):
                    return False
                if message.author in (other, sender):
                    if message.author == sender:
                        return other in message.mentions
                    else:
                        return sender in message.mentions
                else:
                    return False

            msg = await self.bot.wait_for_message(timeout=30,
                                                  channel=ctx.message.channel,
                                                  check=check)
            await ctx.send("Response one received!")
            if not msg:
                await ctx.send("Failed to accept in time!")
                del self.awaiting[sender]
                return

            elif msg.content.startswith("!decline"):
                await ctx.send("Trade declined, cancelling!")
                del self.awaiting[sender]
                return

            msg2 = await self.bot.wait_for_message(timeout=30,
                                                   channel=ctx.message.channel,
                                                   check=check)
            await ctx.send("Response two received!")

            if not msg2:
                await ctx.send("Failed to accept in time!")
                del self.awaiting[sender]
                return

            elif msg2.content.startswith("!decline"):
                await ctx.send("Trade declined, cancelling!")
                del self.awaiting[sender]
                return

            await ctx.send("Checking inventories")
            oinv = await self.get_inv(other)['items']
            sinv = await self.get_inv(sender)['items']
            for item in self.awaiting[sender][1]:
                split = item.split('x')
                split, num = "x".join(split[:-1]), abs(int(split[-1]))
                if num <= 0:
                    await ctx.send("Invalid value for number {} of {}".format(num, split))
                    del self.awaiting[sender]
                    return
                if split not in oinv or num > oinv[split]:
                    await ctx.send("{} does not have enough {} to trade! Trade cancelled!".format(other, split))
                    del self.awaiting[sender]
                    return

            for item in items:
                split = item.split('x')
                split, num = "x".join(split[:-1]), abs(int(split[-1]))
                if num <= 0:
                    await ctx.send("Invalid value for number {} of {}".format(num, split))
                    del self.awaiting[sender]
                    return
                if split not in sinv or num > sinv[split]:
                    await ctx.send("{} does not have enough {} to trade! Trade cancelled!".format(sender, split))
                    del self.awaiting[sender]
                    return

            await ctx.send("Swapping items")
            titems = []
            for item in items:
                split = item.split('x')
                titems.append(("x".join(split[:-1]), abs(int(split[-1]))))
            await self.remove_inv(sender, *titems)
            await self.add_inv(other, *titems)
            ritems = []
            for item in self.awaiting[sender][1]:
                split = item.split('x')
                ritems.append(("x".join(split[:-1]), abs(int(split[-1]))))
            await self.remove_inv(other, *ritems)
            await self.add_inv(sender, *ritems)

            await ctx.send("Trade complete!")
            del self.awaiting[sender]

    @inventory.command(no_pm=True)
    async def give(self, ctx, other: discord.Member, *items: str):
        """Give items (using itemx# notation) to a member"""
        for item in items:
            split = item.split('x')
            split, num = "x".join(split[:-1]), abs(int(split[-1]))
            sinv = await self.get_inv(ctx.message.author)['items']
            if num <= 0:
                await ctx.send("Invalid value for number {} of {}".format(num, split))
                return
            if split not in sinv or num > sinv[split]:
                await ctx.send("You do not have enough {} to give! Cancelled!".format(split))
                return
        await ctx.send("Giving items")
        for item in items:
            split = item.split('x')
            split, num = "x".join(split[:-1]), abs(int(split[-1]))
            await self.remove_inv(ctx.message.author, (split, num))
            await self.add_inv(other, (split, num))

    @inventory.command(no_pm=True)
    @server_complex_mode
    async def items(self, ctx):
        """See all set items on a guild"""
        items = self.settings[str(ctx.guild.id)]['items']
        if not items:
            await ctx.send("No items to display")
            return
        fmt = "```\n{}\n```".format("\n".join(items.keys()))
        await ctx.send(fmt)

    @inventory.command(no_pm=True)
    @server_complex_mode
    async def iteminfo(self, ctx, item : str):
        """Get metadata for an item"""
        servsetting = self.settings[str(ctx.message.guild.id)]
        items = servsetting['items']
        if item not in items:
            await ctx.send("That is not a valid item!")
        else:
            vfmt = ""
            for key, value in items[item].items():
                vfmt += "{}: {}".format(key, value)
            await ctx.send("```\n{}\n```".format(vfmt))

    @inventory.command(no_pm=True)
    @server_complex_mode
    async def useeco(self, ctx, value: str):
        """Toggle guild economy features, off by default"""
        value = value.lower()
        if value == "true":
            if str(ctx.guild.id) not in self.settings:
                self.addserv(ctx, ecc=True)
            else:
                self.settings[str(ctx.guild.id)]['eco'] = True
            await ctx.send("Server economy features set to ON")
        elif value == "false":
            if str(ctx.guild.id) in self.settings:
                self.settings[str(ctx.guild.id)]['eco'] = True
            await ctx.send("Server economy features set to OFF (default)")
        else:
            ctx.send("{} is not a valid option!".format(value))
            return

    @inventory.command(no_pm=True)
    @server_eco_mode
    async def sell(self, ctx, item: str, num: int):
        """If item has a set value, sell a number of the item"""
        num = abs(num)
        settings = self.settings[str(ctx.guild.id)]
        if item in settings['items']:
            if settings['items'][item].get("value", None):
                try:
                    val = int(settings['items'][item].get("value", None)) * num
                    await self.remove_inv(ctx.author, (item, num))
                    await self.add_eco(ctx.author, val)
                    await ctx.send("{} {}s sold for ${}".format(num, item, val))
                except ValueError:
                    await ctx.send("You don't have enough {} to give! Cancelled.".format(item))
            else:
                await ctx.send("This item has no set value!")
        else:
            await ctx.send("This is not a valid item!")

    async def add_eco(self, member, amount):
        sid = str(member.guild.id)
        file = "invdata/{}.json".format(member.id)
        if json.is_valid_json(file):
            data = json.load_json(file)
        else:
            data = {sid: dict(money=0, items=dict())}
        if sid not in data:
            data[sid] = dict(items=dict(), money=0)
        data[sid]['money'] = int(data[sid]['money']) + amount
        json.save_json(file, data)

    @inventory.command(no_pm=True, aliases=['bal', 'money'])
    @server_eco_mode
    async def balance(self, ctx):
        """Get your balance"""
        udata = await self.get_inv(ctx.author)
        val = udata['money']
        await ctx.send("You have {} {}".format(val, self.settings[str(ctx.message.guild.id)]['cur']))

    @inventory.command(no_pm=True)
    @server_eco_mode
    async def setcurrency(self, ctx, currency: str):
        """Change the servers currency (a name) for example 'Gold'; 'Dollars'; 'Credits'; etc"""
        self.settings[str(ctx.message.guild.id)]['cur'] = currency
