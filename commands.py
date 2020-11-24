import discord
from discord.ext import commands
from os import remove

class CommandsCog(commands.Cog):
    def __init__(self, bot, version):
        self.bot = bot
        self.version = version

    @commands.command()
    async def ping(self, ctx):
        latency = format(self.bot.latency * 1000, ".1f")
        await ctx.send(f":ping_pong: Pong! `{latency}ms`")

    @commands.command()
    async def about(self, ctx):
        embed = discord.Embed(color=discord.Colour.green())

        embed.description = (
            'This bot is an instance of __Discord Plays Snake__ by Geekid812!'
            '\n[GitHub Repository](https://github.com/Geekid812/discord-plays-snake)'
            f'\n\nVersion: {self.version}'
        )

        embed.set_author(name='About', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def reset(self, ctx):
        def response_check(message):
            return message.channel == ctx.channel and message.author == ctx.author
        
        await ctx.send(':warning: Are you sure you want to reset all save data? This action is irreversible. `yes`/`no`')
        msg = await self.bot.wait_for('message', check=response_check, timeout=60.0)
        response = msg.content.lower()

        if response == 'no':
            return await ctx.send('Alright then, reset cancelled.')
        
        if response != 'yes':
            return await ctx.send('That\'s neither `yes` or `no`. I\'m going to consider this as a no, just in case...')
        
        try: remove('save.json')
        except FileNotFoundError: pass

        await ctx.send(':wastebasket: Save deleted.')
