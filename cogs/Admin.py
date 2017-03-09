import copy
import asyncio
from cogs.utils import checks
from inspect import isawaitable
from discord.ext import commands
import discord


class Admin(object):
    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.command(hidden=True)
    async def eval(self, ctx, *, args: str):
        bot = self.bot
        rtrn = eval(args)
        if isawaitable(rtrn):
            rtrn = await rtrn
        await ctx.send(str(rtrn))

    @commands.command(hidden=True)
    @checks.is_owner()
    async def repeatcommand(self, ctx, times: int, *, command):
        """Repeats a command a specified number of times."""
        msg = copy.copy(ctx.message)
        msg.content = command
        for i in range(times):
            await self.bot.process_commands(msg)

    @commands.command(hidden=True)
    @checks.owner_or_permissions(manage_messagees=True)
    async def purge(self, ctx, number: int):
        '''Purge messages'''
        await ctx.message.channel.purge(limit=number)

    @commands.command(hidden=True)
    @checks.is_owner()
    async def logout(self, ctx):
        await ctx.send("Logging out")
        self.bot.running = False
        for shutdown in self.bot.shutdowns:
            await shutdown
        await self.bot.logout()

    @commands.command(hidden=True)
    @checks.is_owner()
    async def restart(self, ctx):
        await ctx.send("Restarting!")
        for shutdown in self.bot.shutdowns:
            await shutdown
        await self.bot.logout()
