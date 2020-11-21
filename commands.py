import discord
from discord.ext import commands

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        latency = format(self.bot.latency * 1000, ".1f")
        await ctx.send(f":ping_pong: Pong! `{latency}ms`")
