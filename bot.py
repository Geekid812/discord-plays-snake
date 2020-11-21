import discord
import traceback
import asyncio
from discord.ext import commands
from json import load
from datetime import datetime

from commands import CommandsCog
from snake import SnakeCog, StopMessage

__version__ = '1.0.0'
IGNORE_ERRORS = (commands.CommandNotFound, )

class Bot(commands.Bot):

    async def on_ready(self):
        print('--- DISCORD PLAYS SNAKE ---\nReady to play!')
        print(f'Version: {__version__}\nUser: {self.user.name} (ID: {self.user.id})\nServers: {len(self.guilds)}')
        self.add_check(no_private_messages)
        await self.update_presence()

    async def on_command_error(self, ctx, error):
        if type(error) in IGNORE_ERRORS: return

        if isinstance(error, StopMessage):
            return await ctx.send(f':exclamation: Discord Plays Snake has stopped:\n{error.message}\n\nUse `{settings["prefix"]}resume` to resume the game once the problem is resolved.')

        if isinstance(error, commands.ChannelNotFound):
            return await ctx.send(f"The `{error.argument}` channel doesn't exist. Give me a valid text channel, please!")

        if isinstance(error, commands.CheckFailure):
            return await ctx.send("Why are you trying to use commands in direct messages? That's pointless.")

        if isinstance(error, asyncio.TimeoutError):
            return await ctx.send("Wow, you ignored me. I feel great now...")

        try:
            error_type = str(type(error))[8:-2]
            await ctx.send(f":flushed: Woah there, an error occured. That's awkward...\n`{error_type}`")
        finally:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f'\n[Exception occured at {timestamp} - {error_type}]')
            if settings['print_traceback']:
                traceback.print_exception(type(error), error, error.__traceback__)

    async def update_presence(self):
        activity = discord.Activity(name=settings['activity'], type=getattr(discord.ActivityType, settings['activity_type']))
        await self.change_presence(activity=activity)

def no_private_messages(ctx):
    return ctx.guild is not None

if __name__ == '__main__':
    with open("token.txt","r") as f:
        token = f.read()
    
    with open("settings.json","r") as f:
        settings = load(f)

    bot = Bot(command_prefix=settings['prefix'], help_command=None, intents=discord.Intents.default())
    bot.add_cog(CommandsCog(bot))
    bot.add_cog(SnakeCog(bot, settings))
    bot.run(token)
