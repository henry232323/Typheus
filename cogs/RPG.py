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
from .utils import checks, dataIO
from discord.ext import commands
from traceback import print_exc
from collections import Counter
from functools import wraps
from random import choice, randint
from copy import copy
import discord
import asyncio
import ujson as json


def server_complex_mode(func):
    @wraps(func)
    async def predicate(self, ctx, *args, **kwargs):
        settings = await self.get_settings(ctx.guild)
        instgs = await self.in_settings(ctx.guild)
        if not instgs or settings["mode"] == 0:
            await ctx.send("This command requires complex mode to be enabled!"
                           " Use the `;settings configure` command to switch"
                           " to complex mode, where items are restricted to admin defined")
        else:
            await func(self, ctx, *args, **kwargs)

    return predicate


def server_eco_mode(func):
    @wraps(func)
    async def predicate(self, ctx, *args, **kwargs):
        settings = await self.get_settings(ctx.guild)
        instgs = await self.in_settings(ctx.guild)
        if not instgs or \
           settings["mode"] == 0 or \
           settings["eco"] == False:

            await ctx.send("To use this command the guild must be in complex mode and have economy enabled!"
                           " Use `settings configure` to change servmode to complex and change eco mode")
        else:
            await func(self, ctx, *args, **kwargs)

    return predicate


class Converter(commands.MemberConverter):
    def convert(self):
        if self.argument == 'everyone' or self.argument == '@everyone':
            return 'everyone'
        return super().convert()

class RPG(object):
    """Inventory/Economy related commands. Some commands require certain roles. 
    Bot Mod, Bot Admin, Bot Inventory. Bot inventory will allow you to give items
    Bot Mod and Admin can moderate item creation and lotto creation, as well as several others"""
    def __init__(self, bot):
        self.emote = "\U0001F4B5"
        self.bot = bot

        self.awaiting = dict()
        self.conn = self.bot.conn
        self.lotteries = dict()
        self.defaultsettings = dict(mode=0, items=dict(), eco=False, cur="dollars", lootboxes=dict(), start=0)
        self.defaultdump = json.dumps(self.defaultsettings).replace("'", "''")

    async def addserv(self, guild, mode=1, items=None, ecc=False, nil=False):
        if nil: # If there absolutely is not
            req = """INSERT INTO servdata (UUID, info) VALUES ({0.id}, '{1}')""".format(guild, self.defaultdump)
            await self.conn.fetch(req)
        else:
            req = f"""SELECT info FROM servdata WHERE UUID = {guild.id}"""
            values = await self.conn.fetch(req)
            if values:
                return
            else:
                await self.addserv(guild, mode=mode, items=items, ecc=ecc, nil=True)

    async def in_settings(self, guild):
        req = f"""SELECT * FROM servdata WHERE UUID = {guild.id}"""
        return bool(await self.conn.fetch(req))

    async def get_settings(self, guild):
        try:
            req = f"""SELECT info FROM servdata WHERE UUID = {guild.id}"""
            values = await self.conn.fetch(req)
            if values:
                data = json.loads(values[0]["info"])
                return data

            else:
                await self.addserv(guild, nil=True)
                return await self.get_settings(guild)
        except:
            print_exc()

    async def update_settings(self, guild, settings):
        try:
            json_data = json.dumps(settings).replace("'", "''")
            req = f"""UPDATE servdata
                      SET info = '{json_data}'
                      WHERE UUID = {guild.id}"""

            await self.conn.fetch(req)
        except:
            print(json_data)

    async def get_full_inv(self, member):
        values = await self.conn.fetch(
            """
            SELECT info FROM userdata WHERE UUID = {member.id};
            """.format(member=member))

        if not values:
            rd = dict(items=dict(), money=0)
            data = {str(member.guild.id): rd}
            await self.conn.fetch("""
                INSERT INTO userdata (UUID, info) VALUES ({member.id}, '{json_data}');
            """.format(member=member, json_data=json.dumps(data)))

        else:
            data = json.loads(values[0]["info"])
            try:
                itm = data[str(member.guild.id)]
                itm["items"] = {x: y for x, y in itm["items"].items() if y}

            except KeyError:
                rd = dict(items=dict(), money=0)
                data[str(member.guild.id)] = rd

            await self.conn.fetch("""UPDATE userdata
            SET info = '{json_data}'
            WHERE UUID = {member.id};""".format(member=member, json_data=json.dumps(data)))

        return data

    async def get_inv(self, member):
        return (await self.get_full_inv(member))[str(member.guild.id)]

    async def add_inv(self, member, *items):
        data = await self.get_full_inv(member)
        data[str(member.guild.id)]["items"] = Counter(data[str(member.guild.id)]["items"])
        data[str(member.guild.id)]["items"].update(dict(items))

        command = """UPDATE userdata
           SET info = '{json_data}'
           WHERE UUID = {member.id};""".format(json_data=json.dumps(data), member=member)
        await self.conn.fetch(command)

    async def get_eco(self, member):
        return (await self.get_inv(member))["money"]

    async def add_eco(self, member, amount):
        data = await self.get_full_inv(member)
        data[str(member.guild.id)]["money"] += amount
        if data[str(member.guild.id)]["money"] < 0:
            raise ValueError("Cannot take more than user has")
        command = """UPDATE userdata
           SET info = '{json_data}'
           WHERE UUID = {member.id};""".format(json_data=json.dumps(data).replace("'", "''"), member=member)

        await self.conn.fetch(command)

    async def remove_inv(self, member, *items):
        data = await self.get_full_inv(member)
        id = dict(items)
        data[str(member.guild.id)]["items"] = Counter(data[str(member.guild.id)]["items"])
        data[str(member.guild.id)]["items"].subtract(id)

        for item, value in data[str(member.guild.id)]["items"].items():
            if item in id:
                if value < 0:
                    raise ValueError("User does not have enough items to take")

        command = """UPDATE userdata
           SET info = '{json_data}'
           WHERE UUID = {member.id};""".format(json_data=json.dumps(data), member=member)
        await self.conn.fetch(command)

    @commands.group(invoke_without_command=True, aliases=['i', 'inv'])
    @checks.no_pm()
    async def inventory(self, ctx, *, member: discord.Member=None):
        """Check your or another users inventory. ;help inventory for more info"""
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
            embed.set_footer(text=str(ctx.message.created_at))
            await ctx.send(embed=embed)

    @checks.mod_or_inv()
    @inventory.command()
    @checks.no_pm()
    async def giveitem(self, ctx, item: str, num: int, *members: Converter):
        """Give an item a number of times to members
        Requires "Bot Mod" or "Bot Inventory" roles"""
        if "everyone" in members:
            members = ctx.guild.members
        num = abs(num)
        settings = await self.get_settings(ctx.guild)
        if settings["mode"] == 0 or item in settings["items"]:
            for member in members:
                await self.add_inv(member, (item, num))
            await ctx.send("Items given!")

        else:
            await ctx.send("Item is not available! (Add it or switch to simple mode)")

    @checks.mod_or_inv()
    @inventory.command()
    @checks.no_pm()
    async def takeitem(self, ctx, item: str, num: int, *members: Converter):
        """Take a number of an item from a user
        Same command usage as inventory giveitem, inversely
        Requires "Bot Mod" or "Bot Inventory" roles"""
        if "everyone" in members:
            members = ctx.guild.members
        num = abs(num)
        settings = await self.get_settings(ctx.guild)
        if settings["mode"] == 0 or item in settings["items"]:
            for member in members:
                try:
                    await self.remove_inv(member, (item, num))
                    await ctx.send("Items taken!")
                except ValueError:
                    await ctx.send("Could not take item from {}! Skipping".format(member))
        else:
            await ctx.send("Item is not available! (Add it or switch to simple mode)")

    @inventory.command()
    @checks.no_pm()
    async def offer(self, ctx, other: discord.Member, *items: str):
        """Send a trade offer to another user. Usage: ;inventory offer @Henry bananax3 applex1 --Format items as {item}x{#}"""
        self.awaiting[other] = (ctx, items)

    @inventory.command()
    @checks.no_pm()
    async def respond(self, ctx, other: discord.Member, *items: str):
        """Respond to a trade offer by another user. Usage: ;inventory respond @Henry grapex8 applex1 --Format items as {item}x{#}"""
        sender = ctx.message.author
        if sender in self.awaiting and other == self.awaiting[sender][0].message.author:
            await ctx.send("Both parties say ;accept @Other to accept the trade or !decline @Other to decline")

            def check(message):
                if not (message.channel == ctx.channel):
                    return False
                if not message.content.startswith((";accept", ";decline",)):
                    return False
                if message.author in (other, sender):
                    if message.author == sender:
                        return other in message.mentions
                    else:
                        return sender in message.mentions
                else:
                    return False

            msg = await self.bot.wait_for("message",
                                                  timeout=30,
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

            msg2 = await self.bot.wait_for("message",
                                           timeout=30,
                                           check=check)

            await ctx.send("Response two received!")

            if not msg2:
                await ctx.send("Failed to accept in time!")
                del self.awaiting[sender]
                return

            elif msg2.content.startswith(";decline"):
                await ctx.send("Trade declined, cancelling!")
                del self.awaiting[sender]
                return

            await ctx.send("Checking inventories")
            oinv = (await self.get_inv(other))['items']
            sinv = (await self.get_inv(sender))['items']
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

    @inventory.command()
    @checks.no_pm()
    async def give(self, ctx, other: discord.Member, *items: str):
        """Give items ({item}x{#}) to a member"""
        for item in items:
            split = item.split('x')
            split, num = "x".join(split[:-1]), abs(int(split[-1]))
            sinv = (await self.get_inv(ctx.message.author))['items']
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

    @inventory.command()
    @checks.no_pm()
    @server_complex_mode
    async def items(self, ctx):
        """See all items for a guild"""
        settings = await self.get_settings(ctx.guild)
        items = settings['items']
        if not items:
            await ctx.send("No items to display")
            return

        embed = discord.Embed()

        words = dict()
        for x in items.keys():
            if x[0].lower() in words:
                words[x[0].lower()].append(x)
            else:
                words[x[0].lower()] = [x]

        for key, value in words.items():
            if value:
                embed.add_field(name=key.upper(), value="\n".join(value))

        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.set_thumbnail(
            url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png")
        embed.set_footer(text=str(ctx.message.created_at))
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, aliases=['bal', 'money', 'balance', 'eco', 'e'])
    @checks.no_pm()
    @server_eco_mode
    async def economy(self, ctx, *, member: discord.Member=None):
        """Get your balance"""
        if not member:
            member = ctx.author
        settings = await self.get_settings(ctx.guild)
        val = await self.get_eco(member)
        fmt = "You have {} {}".format(val, settings['cur'])
        embed = discord.Embed(description=fmt)
        embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        embed.set_footer(text=str(ctx.message.created_at))
        embed.set_thumbnail(
            url="http://rs795.pbsrc.com/albums/yy232/PixKaruumi/Pixels/Pixels%2096/248.gif~c200")
        await ctx.send(embed=embed)

    @checks.mod_or_permissions()
    @economy.command()
    @checks.no_pm()
    async def givemoney(self, ctx, amount: int, *members: Converter):
        """Give `amount` of money to listed members
        Requires "Bot Mod" role"""
        if "everyone" in members:
            members = ctx.guild.members

        for member in members:
            await self.add_eco(member, amount)

        await ctx.send("Money given!")

    @checks.mod_or_permissions()
    @economy.command(aliases=["setbal"])
    @checks.no_pm()
    async def setbalance(self, ctx, amount: int, *members: Converter):
        """Set the balance of listed members to an `amount`
        Requires "Bot Mod" role"""
        if "everyone" in members:
            members = ctx.guild.members

        for member in members:
            bal = await self.get_eco(member)
            await self.add_eco(member, amount-bal)

        await ctx.send("Balance changed!")

    @economy.command()
    @checks.no_pm()
    @server_eco_mode
    async def sellto(self, ctx, user: discord.Member, amount: int, *items: str):
        """Sell items to another player for a set amount. (Using {item}x{#}
        Example: ;i sellto @Henry#6174 50 bananax3"""
        oinv = await self.get_inv(ctx.author)
        uinv = await self.get_inv(user)
        sitems = []
        for item in items:
            split = item.split('x')
            split, num = "x".join(split[:-1]), abs(int(split[-1]))
            if oinv["items"].get(split, 0) < num:
                await ctx.send("You do not have enough {} to offer that! Cancelled".format(split))
                return
            sitems.append((split, num))

        await ctx.send(";accept to accept the deal, else ;decline")
        msg = await self.bot.wait_for("message",
                                      timeout=30,
                                      check=lambda x: x.author is user and (";accept" in x.content or ";decline" in x.content))

        if msg.content == ";accept":
            await ctx.send("Accepted!")
            if uinv["money"] < amount:
                await ctx.send("You cannot afford to accept this deal! Cancelled")
                return
            await self.add_inv(user, *sitems)
            await self.add_eco(ctx.author, amount)
            await self.add_eco(user, -amount)
            await ctx.send("Exchange Completed")
        else:
            await ctx.send("Declined! Cancelling")

    @economy.command()
    @checks.no_pm()
    @server_eco_mode
    async def sell(self, ctx, item: str, num: int):
        """If item has a set value, sell x of the item"""
        num = abs(num)
        settings = await self.get_settings(ctx.guild)
        if item in settings['items']:
            if settings['items'][item].get("sellvalue", None):
                try:
                    val = int(settings['items'][item].get("sellvalue", None)) * num
                    await self.remove_inv(ctx.author, (item, num))
                    await self.add_eco(ctx.author, val)
                    await ctx.send("{} {}s sold for ${}".format(num, item, val))
                except ValueError:
                    await ctx.send("You don't have enough {} to give! Cancelled.".format(item))
            else:
                await ctx.send("This item has no set value!")
        else:
            await ctx.send("This is not a valid item!")

    @economy.command()
    @checks.no_pm()
    @server_eco_mode
    async def buy(self, ctx, item: str, num: int):
        """If item has a set value, buy x of the item"""
        try:
            num = abs(num)
            settings = await self.get_settings(ctx.guild)
            if item in settings['items']:
                if settings['items'][item].get("buyvalue", None):
                    try:
                        val = int(settings['items'][item].get("buyvalue", None)) * num
                        await self.add_inv(ctx.author, (item, num))
                        await self.add_eco(ctx.author, -val)
                        await ctx.send("{} {}s bought for ${}".format(num, item, val))
                    except IndexError:
                        await ctx.send("You cant afford to buy this!")
                else:
                    await ctx.send("This item has no set value!")
            else:
                await ctx.send("This is not a valid item!")
        except:
            print_exc()

    @economy.command()
    @checks.no_pm()
    @server_eco_mode
    async def pay(self, ctx, amount: int, other: discord.Member):
        """Pay another user an amount"""
        if await self.get_eco(ctx.author) < amount:
            await ctx.send("You don't have enough money to use this command!")
        else:
            await self.add_eco(ctx.author, -abs(amount))
            await self.add_eco(other, abs(amount))
            await ctx.send("Successfully paid {} {} to {}".format(abs(amount), (await self.get_settings(ctx.guild))["cur"], other))

    @checks.mod_or_permissions()
    @commands.group(name="settings", aliases=["s", "stgs"], invoke_without_command=True)
    @checks.no_pm()
    async def _settings(self, ctx):
        """Get the servers settings
        Requires "Bot Mod" role"""
        settings = await self.get_settings(ctx.guild)

        embed = discord.Embed()
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.set_thumbnail(
            url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png"
        )
        embed.add_field(name="Server Mode",
                        value="Complex mode" if settings["mode"] else "Simple mode")

        embed.add_field(name="Using Eco",
                        value=str(settings["eco"]))

        embed.add_field(name="Currency",
                        value=str(settings["cur"]))

        embed.add_field(name="Starting Money",
                        value="{} {}".format(settings["start"], settings["cur"]))

        embed.add_field(name="Loot Boxes",
                        value="{} lootboxes".format(len(settings["lootboxes"])))

        items = settings['items']
        if not items:
            fmt = "No items"
        else:
            fmt = "{} items".format(len(items))
        embed.add_field(name="Items", value=fmt)
        embed.set_footer(text=str(ctx.message.created_at))

        await ctx.send(embed=embed)

    @checks.mod_or_permissions()
    @_settings.command()
    @server_complex_mode
    @checks.no_pm()
    async def additem(self, ctx, name: str, *, data: str):
        """If guild mode is complex, add an item that can be given
                Usage: ;inventory additem itemname *data
                Where data is a newline separated list of attributes, for example
                ;i additem banana
                color: yellow
                value: 5
                Special Modifiers:
                    buyvalue: integer
                    sellvalue: integer
                Set data to 'None' for no data
                
        Requires "Bot Mod" role"""

        if "@everyone" in name or "@here" in name:
            await ctx.send("Forbidden words in item name (everyone or here mentions)")
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

        settings = await self.get_settings(ctx.guild)
        settings['items'][name] = fdict
        await ctx.send("Added item {}".format(name))
        await self.update_settings(ctx.guild, settings)

    @checks.mod_or_permissions()
    @_settings.command()
    @server_complex_mode
    @checks.no_pm()
    async def removeitem(self, ctx, name: str):
        """Remove an item that can be given, inverse of ;i additem
        Requires "Bot Mod" role"""
        settings = await self.get_settings(ctx.guild)
        if name in settings['items']:
            del settings['items'][name]

            await ctx.send("Item {} removed".format(name))
        else:
            await ctx.send("{} is not a valid item!".format(name))

        await self.update_settings(ctx.guild, settings)

    @checks.mod_or_permissions()
    @_settings.command()
    @checks.no_pm()
    @server_eco_mode
    async def addinfo(self, ctx, item: str, *, new_data):
        """Add new info data to an item, same syntax as editinfo and additem
        Requires "Bot Mod" role"""
        settings = await self.get_settings(ctx.guild)
        if item not in settings["items"]:
            await ctx.send("That is not a valid item!")
            return
        dfmt = new_data.split("\n")
        for item in dfmt:
            split = item.split(": ")
            key = split[0]
            val = ": ".join(split[1:])
            settings["items"][key] = val

        await self.update_settings(ctx.guild, settings)
        await ctx.send("Settings updated!")

    @checks.mod_or_permissions()
    @_settings.command()
    @checks.no_pm()
    @server_eco_mode
    async def setcurrency(self, ctx, currency: str):
        """Change the servers currency for example 'Gold', etc
        Requires "Bot Mod" role"""
        settings = await self.get_settings(ctx.guild)
        old = settings['cur']
        settings['cur'] = currency
        await ctx.send("Currency changed from {} to {}".format(old, currency))

        await self.update_settings(ctx.guild, settings)

    @checks.mod_or_permissions()
    @_settings.command(aliases=["beginamount", "startermoney", "startmoney"])
    @checks.no_pm()
    @server_eco_mode
    async def setstartamount(self, ctx, amount: int):
        """Set the amount of money users start with
        Requires "Bot Mod" role"""
        settings = await self.get_settings(ctx.guild)
        settings["start"] = amount
        await ctx.send("Players will now join the server with {} {}".format(amount, settings["cur"]))
        await self.update_settings(ctx.guild, settings)

    @_settings.command()
    @checks.no_pm()
    @server_complex_mode
    async def iteminfo(self, ctx, item: str):
        """Get metadata for an item"""
        servsetting = await self.get_settings(ctx.guild)
        items = servsetting['items']
        desc = ""
        if item not in items:
            await ctx.send("That is not a valid item!")
            return
        else:
            embed = discord.Embed(title=item)
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.set_thumbnail(
                url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png")
            embed.set_footer(text=str(ctx.message.created_at))

            for key, value in items[item].items():
                if key and value:
                    embed.add_field(name=key, value=value)
                else:
                    desc += key or value

            embed.description = desc
            try:
                await ctx.send(embed=embed)
            except:
                description = "\n".join("{}: {}".format(x, y) for x, y in items[item].items())
                embed = discord.Embed(title=item, description=description)
                embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
                embed.set_thumbnail(
                    url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png")
                embed.set_footer(text=str(ctx.message.created_at))
                await ctx.send(embed=embed)

    @checks.admin_or_permissions()
    @_settings.command(aliases=["conf", "config"])
    @checks.no_pm()
    async def configure(self, ctx):
        """Configure the server's inventory settings
        Requires "Bot Admin" role"""
        settings = await self.get_settings(ctx.guild)

        desc = """To toggle complex inventory emote with :baggage_claim:
               To toggle eco mode emote with :dollar:
               :white_check_mark: to save
               :negative_squared_cross_mark: to close
               """

        embed = discord.Embed(description=desc)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
        embed.add_field(name="Output", value="Empty")
        embed.set_footer(text=str(ctx.message.created_at))
        embed.set_thumbnail(
            url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png")

        msg = await ctx.send(embed=embed)
        emotes = ("\U0001F6C4", "\U0001F4B5", "\u2705", "\u274E")

        for emote in emotes:
            await msg.add_reaction(emote)

        tset = copy(settings)

        while True:
            try:
                r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id, timeout=80)
            except asyncio.TimeoutError:
                await msg.delete()
                await ctx.send("Menu timed out! ;s conf to go again")
                return

            if u is ctx.guild.me:
                continue

            if u is not ctx.author:
                pass

            elif r.emoji == emotes[0]:
                tset["mode"] = not tset["mode"]
                mode = "complex" if tset["mode"] else "simple"
                embed.set_field_at(0, name="Output", value="Server mode switched to {}".format(mode))
                await msg.edit(embed=embed)
            elif r.emoji == emotes[1]:
                tset["eco"] = not tset["eco"]
                embed.set_field_at(0, name="Output", value="Using eco is now {}".format(tset["eco"]))
                await msg.edit(embed=embed)
            elif r.emoji == emotes[2]:
                if tset["mode"] == 0 and not tset["eco"]:
                    embed.set_field_at(0,
                                       name="Output",
                                       value="For eco to be enabled, the server must be in complex mode")
                else:
                    settings.update(tset)
                    await self.update_settings(ctx.guild, settings)
                    embed.set_field_at(0, name="Output", value="Saved")
                    await msg.delete()
                    break
                await msg.edit(embed=embed)
            elif r.emoji == emotes[3]:
                await msg.delete()
                await ctx.send("Closed")
                return
            else:
                embed.set_field_at(0, name="Output", value="Invalid Reaction")
                await msg.edit(embed=embed)

            try:
                await msg.remove_reaction(r.emoji, u)
            except:
                pass

        try:
            await ctx.send("What would you like the new currency name to be? Type 'skip' to leave it unchanged. 'cancel' to cancel")
            resp = await self.bot.wait_for("message", check=lambda x: x.channel is ctx.channel and x.author is ctx.author)
            if resp.content == "skip":
                pass
            elif resp.content == "cancel":
                await ctx.send("Cancelling!")
                return
            else:
                tset["cur"] = resp.content
                await ctx.send("Currency changed")

            await ctx.send("How much money would you like players to start with? 'skip' to skip, 'cancel' to cancel")
            while True:
                resp = await self.bot.wait_for("message", check=lambda x: x.channel is ctx.channel and x.author is ctx.author)
                if resp.content == "skip":
                    break
                elif resp.content == "cancel":
                    await ctx.send("Cancelling!")
                    return
                else:
                    try:
                        tset["start"] = int(resp.content)
                        break
                    except:
                        await ctx.send("Invalid usage! Try again.")

            await ctx.send("Configuration complete!")
            await self.update_settings(ctx.guild, tset)
        except asyncio.TimeoutError:
            await ctx.send("Timed out! ;s configure to go again")



    @commands.group(invoke_without_command=True, aliases=['lottery'])
    @checks.no_pm()
    @server_eco_mode
    async def lotto(self, ctx):
        """List the currently running lottos."""
        if ctx.guild.id in self.lotteries:
            embed = discord.Embed()
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.set_thumbnail(
                url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png"
            )
            settings = await self.get_settings(ctx.guild)
            cur = settings["cur"]

            for lotto, value in self.lotteries[ctx.guild.id].items():
                embed.add_field(name=lotto,
                                value="Jackpot: {} {}\n{} players entered".format(value["jackpot"],
                                                                                  cur, len(value["players"])))
            embed.set_footer(text=str(ctx.message.created_at))

            await ctx.send(embed=embed)
        else:
            await ctx.send("No lotteries currently running!")

    @checks.mod_or_permissions()
    @lotto.command(aliases=["create"])
    @checks.no_pm()
    @server_eco_mode
    async def new(self, ctx, name: str, jackpot: int, time: int):
        """Create a new lotto, with jackpot payout lasting time in seconds
        Requires "Bot Mod" role"""
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

    @lotto.command(aliases=["join"])
    @checks.no_pm()
    @server_eco_mode
    async def enter(self, ctx, name: str):
        """Enter the lottery with the given name."""
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

    @commands.command(aliases=["rollthedice", "dice"])
    async def rtd(self, ctx, *dice: str):
        """Roll a number of dice with given sides (ndx notation)
        Example: ;rtd 3d7 2d4 5d8 +20 <30 Test for success by adding >/<# to the end (optional)"""
        try:
            dice = list(dice)
            rolls = dict()
            add = []
            rel = None
            if dice[-1].startswith((">", "<")):
                rel = dice.pop(-1)
                val = int(rel.strip("<>"))
                type = rel[0]

            for die in dice:
                try:
                    number, sides = die.split("d")
                    number, sides = int(number), int(sides)
                    rolls[sides] = [randint(1, sides) for x in range(number)]
                except ValueError:
                    add.append(int(die))

            total = sum(sum(x) for x in rolls.values()) + sum(add)

            if rel is not None:
                if type == "<":
                    if total <  val:
                        succ = "suceeded"
                    else:
                        succ = "failed"
                else:
                    if total > val:
                        succ = "suceeded"
                    else:
                        succ = "failed"

                fmt = "Roll **{0}** ({1} {2} {3}) ([{4}] + {5})" if add else "Roll **{0}** ({1} {2} {3}) ([{4}])"
                all = "] + [".join(" + ".join(map(lambda x: str(x), roll)) for roll in rolls.values())
                msg = fmt.format(succ, total, type, val, all, " + ".join(map(lambda x: str(x), add)))
            else:
                fmt = "Rolled **{0}** ([{1}] + {2})" if add else "Rolled **{0}** ([{1}])"
                all = "] + [".join(" + ".join(map(lambda x: str(x), roll)) for roll in rolls.values())
                msg = fmt.format(total, all, " + ".join(map(lambda x: str(x), add)))
            await ctx.send(msg)
        except:
            await ctx.send("Invalid syntax!")

    @checks.no_pm()
    @commands.group(invoke_without_command=True, aliases=['box'])
    @server_eco_mode
    async def lootbox(self, ctx):
        settings = await self.get_settings(ctx.guild)
        if settings["lootboxes"]:
            embed = discord.Embed()
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
            embed.set_thumbnail(
                url="https://mir-s3-cdn-cf.behance.net/project_modules/disp/196b9d18843737.562d0472d523f.png"
            )
            fmt = "{0}: {1:.2f}%"
            for box, data in settings["lootboxes"].items():
                total = sum(data["items"].values())
                value = "Cost: {}\n\t".format(data["cost"]) + "\n\t".join(fmt.format(item, (value/total)*100) for item, value in data["items"].items())
                embed.add_field(name=box,
                                value=value)

            embed.set_footer(text=str(ctx.message.created_at))

            await ctx.send(embed=embed)
        else:
            await ctx.send("No current lootboxes")

    @checks.mod_or_permissions()
    @checks.no_pm()
    @lootbox.command(name="create", aliases=["new"])
    @server_eco_mode
    async def _create(self, ctx, name: str, cost: int, *items: str):
        """Create a new lootbox, under the given `name` for the given cost
        Use {item}x{#} notation to add items with {#} weight
        Weight being an integer. For example:
        bananax2 orangex3. The outcome of the box will be
        Random Choice[banana, banana, orange, orange, orange]
        
        Requires "Bot Mod" role"""

        settings = await self.get_settings(ctx.guild)
        if name in settings["lootboxes"]:
            await ctx.send("Lootbox already exists, updating...")

        winitems = {}
        for item in items:
            split = item.split('x')
            split, num = "x".join(split[:-1]), abs(int(split[-1]))
            winitems.update({split: num})


        settings["lootboxes"][name] = dict(cost=cost, items=winitems)

        await ctx.send("Lootbox successfully created")
        await self.update_settings(ctx.guild, settings)

    @checks.no_pm()
    @lootbox.command(name="buy")
    @server_eco_mode
    async def _buy(self, ctx, name: str):
        """Buy a lootbox of the given name"""
        settings = await self.get_settings(ctx.guild)
        try:
            box = settings["lootboxes"][name]
        except KeyError:
            await ctx.send("That is not a valid lootbox")
            return

        bal = await self.get_eco(ctx.author)
        if bal < box["cost"]:
            await ctx.send("You cant afford this box")
            return

        await self.add_eco(ctx.author, box["cost"])
        winitems = []
        for item, amount in box["items"].items():
            winitems += [item] * amount

        result = choice(winitems)
        await self.add_inv(ctx.author, (result, 1))
        await ctx.send("You won a(n) {}".format(result))

    @checks.no_pm()
    @lootbox.command(name="delete", aliases=["remove"])
    @server_eco_mode
    async def _delete(self, ctx, name: str):
        """Delete a lootbox with the given name"""
        settings = await self.get_settings(ctx.guild)
        if name in settings["lootboxes"]:
            del settings["lootboxes"][name]
            await ctx.send("Loot box removed")
        else:
            await ctx.send("Invalid loot box")

            await self.update_settings(ctx.guild, settings)