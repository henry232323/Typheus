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
from traceback import print_exc
from collections import Counter
from functools import wraps
from random import choice
from copy import copy
import discord
import asyncio
import json

dio = dataIO.DataIO()
#  TODO: New Help formatter, replace the old one
#  TODO: Gamble game


def server_complex_mode(func):
    @wraps(func)
    async def predicate(self, ctx, *args, **kwargs):
        if str(ctx.guild.id) not in self.settings or self.settings[str(ctx.message.guild.id)]["mode"] == 0:
            await ctx.send("This command requires complex mode to be enabled!"
                           " Use the `;inventory configure` command to switch"
                           " to complex mode, where items are restricted to admin defined")
        else:
            await func(self, ctx, *args, **kwargs)

    return predicate


def server_eco_mode(func):
    @wraps(func)
    async def predicate(self, ctx, *args, **kwargs):
        if str(ctx.guild.id) not in self.settings or \
           self.settings[str(ctx.guild.id)]["mode"] is 0 or \
           self.settings[str(ctx.guild.id)]["eco"] is False:

            await ctx.send("To use this command the guild must be in complex mode and have economy enabled!"
                           " Use `inventory configure` to change servmode to complex and change eco mode")
        else:
            await func(self, ctx, *args, **kwargs)

    return predicate


class RPG(object):
    def __init__(self, bot):
        self.bot = bot
        self.bot.shutdowns.append(self.shutdown)
        file = "invdata/servers.json"
        if dio.is_valid_json(file):
            self.settings = dio.load_json(file)
        else:
            self.settings = dict()

        self.awaiting = dict()
        self.conn = self.bot.conn
        self.lotteries = dict()

    async def shutdown(self):
        dio.save_json("invdata/servers.json", self.settings)

    def addserv(self, ctx, mode=1, items=None, ecc=False):
        if items is None:
            items = dict()
        self.settings[str(ctx.message.guild.id)] = dict(mode=mode, items=items, eco=ecc, cur="dollars")

    async def get_inv(self, member):
        values = await self.conn.fetch(
            """
            SELECT info FROM userdata WHERE UUID = {member.id};
            """.format(member=member))
        if not values:
            rd = dict(items=dict(), money=0)
            values = [dict(info=dict())]
            values[0]["info"][str(member.guild.id)] = rd
            await self.conn.fetch("""
                INSERT INTO userdata (UUID, info) VALUES ({member.id}, '{json_data}');
            """.format(member=member, json_data=json.dumps(values[0]["info"])))
            return rd
        else:
            data = json.loads(values[0]["info"])
            try:
                return data[str(member.guild.id)]
            except KeyError:
                rd = dict(items=dict(), money=0)
                data[str(member.guild.id)] = rd
                await self.conn.fetch("""
                    INSERT INTO userdata (UUID, info) VALUES ({member.id}, '{json_data}');
                """.format(member=member, json_data=json.dumps(data)))
                return rd

    async def add_inv(self, member, *items):
        values = await self.conn.fetch(
            """
            SELECT info FROM userdata WHERE UUID = {member.id};
            """.format(member=member))

        if not values:
            rd = dict(items=dict(items), money=0)
            values = [dict(info=dict())]
            values[0]["info"][str(member.guild.id)] = rd
            await self.conn.fetch("""
                INSERT INTO userdata (UUID, info) VALUES ({member.id}, '{json_data}');
            """.format(member=member, json_data=json.dumps(values[0]["info"])))
            return
        else:
            data = json.loads(values[0]["info"])
            if str(member.guild.id) not in data:
                data[str(member.guild.id)] = dict(items=dict(), money=0)
            data[str(member.guild.id)]["items"] = Counter(data[str(member.guild.id)]["items"])
            data[str(member.guild.id)]["items"].update(dict(items))

            print(data)
            command = """UPDATE userdata
               SET info = '{json_data}'
               WHERE UUID = {member.id};""".format(json_data=json.dumps(data), member=member)
            await self.conn.fetch(command)

    async def get_eco(self, member):
        return (await self.get_inv(member))["money"]

    async def add_eco(self, member, amount):
        command = """SELECT info FROM userdata WHERE UUID = {member.id};""".format(member=member)
        values = await self.conn.fetch(command)
        if not values:
            fd = {str(member.guild.id): dict(items=dict(), money=amount)}
            json_data = json.dumps(fd)
            command = """INSERT INTO userdata (UUID, info) VALUES ({member.id}, '{json_data}');""".format(member=member, json_data=json_data)
        else:
            data = json.loads(values[0]["info"])
            if str(member.guild.id) not in data:
                data[str(member.guild.id)] = dict(items=dict(), money=0)
            data[str(member.guild.id)]["money"] += amount
            command = """UPDATE userdata
               SET info = '{json_data}'
               WHERE UUID = {member.id};""".format(json_data=json.dumps(data), member=member)

        await self.conn.fetch(command)

    async def remove_inv(self, member, *items):
        values = await self.conn.fetch(
            """
            SELECT info FROM userdata WHERE UUID = {member.id};
            """.format(member=member))
        if not values:
            rd = dict(items=dict(items), money=0)
            values = [dict(info=dict())]
            values[0]["info"][str(member.guild.id)] = rd
            await self.conn.fetch("""
                INSERT INTO userdata (UUID, info) VALUES ({member.id}, '{json_data}');
            """.format(member=member, json_data=json.dumps(values[0]["info"])))
            return
        else:
            data = json.loads(values[0]["info"])
            if str(member.guild.id) not in data:
                data[str(member.guild.id)] = dict(items=dict(), money=0)
            data[str(member.guild.id)]["items"] = Counter(data[str(member.guild.id)]["items"])
            data[str(member.guild.id)]["items"].subtract(dict(items))

            command = """UPDATE userdata
               SET info = '{json_data}'
               WHERE UUID = {member.id};""".format(json_data=json.dumps(data), member=member)
            await self.conn.fetch(command)

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
            embed = discord.Embed(description=fmt)
            embed.set_author(name=member.display_name, icon_url=member.avatar_url)
            embed.set_thumbnail(url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png")
            await ctx.send(embed=embed)

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
    async def givemoney(self, ctx, amount: int, *members: discord.Member):
        """Give `amount` of money to listed members"""
        for member in members:
            await self.add_eco(member, amount)

        await ctx.send("Money given!")

    @checks.mod_or_inv()
    @inventory.command(no_pm=True, aliases=["setbal"])
    async def setbalance(self, ctx, amount: int, *members: discord.Member):
        """Set the balance of listed members to an `amount`"""
        for member in members:
            bal = await self.get_inv(ctx.author)['money']
            await self.add_eco(member, amount-bal)

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
        if self.settings[str(ctx.guild.id)]["mode"] == 0 or item in self.settings[str(ctx.guild.id)]["items"]:
            for member in members:
                await self.remove_inv(member, (item, num))
                await ctx.send("Items taken!")
        else:
            await ctx.send("Item is not available! (Add it or switch to simple mode)")

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
        fmt = "\n".join(items.keys())
        embed = discord.Embed(description=fmt)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.set_thumbnail(
            url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png")
        await ctx.send(embed=embed)

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

    @inventory.command(no_pm=True, aliases=['bal', 'money'])
    @server_eco_mode
    async def balance(self, ctx):
        """Get your balance"""
        udata = await self.get_inv(ctx.author)
        val = udata['money']
        fmt = "You have {} {}".format(val, self.settings[str(ctx.message.guild.id)]['cur'])
        embed = discord.Embed(description=fmt)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(
            url="http://rs795.pbsrc.com/albums/yy232/PixKaruumi/Pixels/Pixels%2096/248.gif~c200")
        await ctx.send(embed=embed)

    @inventory.command(no_pm=True)
    @server_eco_mode
    async def setcurrency(self, ctx, currency: str):
        """Change the servers currency (a name) for example 'Gold'; 'Dollars'; 'Credits'; etc"""
        self.settings[str(ctx.message.guild.id)]['cur'] = currency

    @checks.mod_or_permissions()
    @inventory.command(no_pm=True, aliases=["conf", "config"])
    async def configure(self, ctx):
        """Configure the server's inventory settings"""
        perms = ctx.guild.me.permissions_in(ctx.channel)
        if not perms.manage_messages:
            await ctx.send("The bot doesn't have enough permissions to use this command! Please use togglemode and toggleeco")
            return

        if str(ctx.message.guild.id) not in self.settings:
            self.addserv(ctx, mode=0)

        desc = """To toggle complex inventory emote with :baggage_claim:
               To toggle eco mode emote with :dollar:
               :white_check_mark: to save
               :negative_squared_cross_mark: to close
               """

        embed = discord.Embed(description=desc)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.add_field(name="Output", value="Empty")
        embed.set_thumbnail(
            url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png")

        msg = await ctx.send(embed=embed)
        emotes = ("\U0001F6C4", "\U0001F4B5", "\u2705", "\u274E")

        for emote in emotes:
            await msg.add_reaction(emote)

        tset = copy(self.settings[str(ctx.guild.id)])

        while True:
            try:
                r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id, timeout=80)
            except asyncio.TimeoutError:
                await msg.delete()
                await ctx.send("Menu timed out! ;i configure to go again")
                return

            if u is ctx.guild.me:
                continue

            if u is not ctx.author:
                await msg.remove_reaction(r.emoji, u)
                continue

            if r.emoji not in emotes:
                msg.remove_reaction(r.emoji, u)

            elif r.emoji == emotes[0]:
                tset["mode"] = not tset["mode"]
                mode = "complex" if tset["mode"] else "simple"
                embed.set_field_at(0, name="Output", value="Server mode switched to {}".format(mode))
                await msg.edit(embed=embed)
                await msg.remove_reaction(r.emoji, u)
            elif r.emoji == emotes[1]:
                tset["eco"] = not tset["eco"]
                embed.set_field_at(0, name="Output", value="Using eco is now {}".format(tset["eco"]))
                await msg.edit(embed=embed)
                await msg.remove_reaction(r.emoji, u)
            elif r.emoji == emotes[2]:
                self.settings[str(ctx.guild.id)].update(tset)
                embed.set_field_at(0, name="Output", value="Saved")
                await msg.edit(embed=embed)
            elif r.emoji == emotes[3]:
                await msg.delete()
                await ctx.send("Closed")
                return
            else:
                embed.set_field_at(0, name="Output", value="Invalid Reaction")

            await msg.remove_reaction(r.emoji, u)

    @checks.mod_or_permissions()
    @inventory.command(no_pm=True, name="settings")
    async def _settings(self, ctx):
        """Get the servers settings"""
        if str(ctx.guild.id) not in self.settings:
            self.addserv(ctx, mode=0)

        embed = discord.Embed()
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.set_thumbnail(
            url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png"
        )
        embed.add_field(name="Server Mode", value="Complex mode" if self.settings[str(ctx.guild.id)]["mode"] else "Simple mode")
        embed.add_field(name="Using Eco", value=str(self.settings[str(ctx.guild.id)]["eco"]))

        items = self.settings[str(ctx.guild.id)]['items']
        if not items:
            fmt = "No items"
        else:
            fmt = "\n".join(items.keys())
        embed.add_field(name="Items", value=fmt)

        await ctx.send(embed=embed)

    @checks.mod_or_permissions()
    @inventory.command(no_pm=True)
    async def togglemode(self, ctx):
        """Toggle mode without configure (If bot doesn't have full perms)"""
        self.settings[str(ctx.guild.id)]["mode"] = not self.settings[str(ctx.guild.id)]["mode"]
        await ctx.send("Mode toggled to {}".format(self.settings[str(ctx.guild.id)]["mode"]))

    @checks.mod_or_permissions()
    @inventory.command(no_pm=True)
    async def toggleeco(self, ctx):
        """Toggle eco without configure (If bot doesn't have full perms)"""
        self.settings[str(ctx.guild.id)]["eco"] = not self.settings[str(ctx.guild.id)]["eco"]
        await ctx.send("Eco toggled to {}".format(self.settings[str(ctx.guild.id)]["eco"]))

    @inventory.command(no_pm=True)
    @server_eco_mode
    async def pay(self, ctx, amount: int, other: discord.Member):
        if await self.get_eco(ctx.author) < amount:
            await ctx.send("You don't have enough money to use this command!")
        else:
            await self.add_eco(ctx.author, -abs(amount))
            await self.add_eco(other, abs(amount))
            await ctx.send("{} successfully paid to {}".format(abs(amount), other))

    @commands.group(invoke_without_command=True, no_pm=True, aliases=['lottery'])
    @server_eco_mode
    async def lotto(self, ctx):
        if ctx.guild.id in self.lotteries:
            embed = discord.Embed()
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.set_thumbnail(
                url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png"
            )
            if str(ctx.guild.id) in self.settings:
                cur = self.settings[str(ctx.guild.id)]["cur"]
            else:
                cur = "dollars"
            for lotto, value in self.lotteries[ctx.guild.id].items():
                embed.add_field(name=lotto, value="Jackpot: {} {}\n{} players entered".format(value["jackpot"], cur, len(value["players"])))

            await ctx.send(embed=embed)
        else:
            await ctx.send("No lotteries currently running!")

    @checks.mod_or_permissions()
    @lotto.command(aliases=["create"])
    @server_eco_mode
    async def new(self, ctx, name: str, jackpot: int, time: int):
        if ctx.guild.id not in self.lotteries:
            self.lotteries[ctx.guild.id] = dict()
        if name in self.lotteries[ctx.guild.id]:
            await ctx.send("A lottery of that name already exists!")
            return
        current = dict(jackpot=jackpot, players=list(), channel=ctx.channel)
        self.lotteries[ctx.guild.id][name] = current
        await ctx.send("Lottery created!")
        await asyncio.sleep(time)
        if current["players"]:
            winner = choice(current["players"])
            await self.add_eco(winner, current["jackpot"])
            await current["channel"].send("Lottery {} is now over!\n{} won {}! Congratulations!".format(name, winner.mention, current["jackpot"]))
        else:
            await ctx.send("Nobody entered {}! Its over now.".format(name))
        del self.lotteries[ctx.guild.id][name]

    @lotto.command(no_pm=True, aliases=["join"])
    @server_eco_mode
    async def enter(self, ctx, name: str):
        if ctx.guild.id in self.lotteries:
            if name in self.lotteries[ctx.guild.id]:
                if ctx.author not in self.lotteries[ctx.guild.id][name]["players"]:
                    self.lotteries[ctx.guild.id][name]["players"].append(ctx.author)
                    await ctx.send("Lotto entered!")
                else:
                    await ctx.send("You're already in this lotto!")
            else:
                await ctx.send("This server has no lotto by that name! See ;lotto")
        else:
            await ctx.send("This server has no lottos currently running!")
