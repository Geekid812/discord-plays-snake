import discord
import asyncio
import json
import numpy
from discord.ext import commands
from datetime import datetime, timedelta
from random import randrange

class SnakeObject:
    BLANK = 0
    HEAD = -1
    APPLE = -2

class FacialExpression:
    NORMAL = 0
    EATING = 1
    DEAD = 2

class Emoji:
    LIKE = '\N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16}'
    RETWEET = '\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}'
    LEFT = '\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}'
    RIGHT = '\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}'
    DOWN = '\N{DOWNWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}'
    UP = '\N{UPWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}'

class StopMessage(commands.CommandError):
    def __init__(self, message):
        self.message = message

class SnakeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_loop = None

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def start(self, ctx, channel : discord.TextChannel):
        def response_check(message):
            return message.channel == ctx.channel and message.author == ctx.author
        
        with open("settings.json","r") as f:
            settings = json.load(f)

        try:
            with open('save.json', 'r') as f:
                save_data = json.load(f)
            
            await ctx.send((
                ':warning: Starting a new game will override the current save.'
                '\nThe best score will be kept, however the current game progress will be reset.'
                '\nAre you sure you want to proceed? `yes`/`no`'
            ))
            msg = await self.bot.wait_for('message', check=response_check, timeout=60.0)
            response = msg.content.lower()

            if response == 'no':
                return await ctx.send('Alright then, game creation cancelled.')
            
            if response != 'yes':
                return await ctx.send('That\'s neither `yes` or `no`. I\'m going to consider this as a no, just in case...')
            
            save_data = self.create_save_data(channel, settings, best=save_data['best'])
        
        except (OSError, json.JSONDecodeError):
            # No save data exists, so we can create one without any worries
            save_data = self.create_save_data(channel, settings)
        
        self.save_data = save_data
        self.channel = channel

        if self.game_loop: self.game_loop.cancel()
        self.game_loop = asyncio.create_task(self.start_loop(ctx))
        await ctx.send(':checkered_flag: The game has now started!')

    def create_save_data(self, channel, settings, best=0):
        height = settings['grid_height']
        width = settings['grid_width']
        grid = numpy.zeros((height, width), dtype=int)

        # Place snake at the center
        snake_pos = (height // 2, width // 2)
        grid[snake_pos[0]][snake_pos[1]] = SnakeObject.HEAD

        # Place an apple somewhere
        apple_pos = self.find_new_apple_position(grid)
        grid[apple_pos[0]][apple_pos[1]] = SnakeObject.APPLE

        timestamp = int(datetime.utcnow().timestamp())

        save = {
            'start_timestamp': timestamp,
            'save_timestamp': timestamp,
            'next_update': 0,
            'channel_id': channel.id,
            'message_id': 0,
            'configuration': {
                'grid_height': settings['grid_height'],
                'grid_width': settings['grid_width'],
                'update_frequency': settings['update_frequency'],
                'twitter_controls': settings['twitter_controls'],
                'tie_threshold': settings['tie_threshold'],
                'embed_color': settings['embed_color']
            },
            'facial_expression': 0,
            'score': 0,
            'best': best,
            'facing': 'down',
            'grid': grid.tolist()
        }

        with open('save.json', 'w') as f:
            json.dump(save, f, indent=4)
        
        return save
    
    async def start_loop(self, ctx):
        try:
            await self.snake_loop()
        except Exception as error:
            await ctx.bot.on_command_error(ctx, error)

    async def snake_loop(self):
        while True:
            wait_until = datetime.fromtimestamp(self.save_data['next_update'])
            await discord.utils.sleep_until(wait_until)

            # Time for a new update!
            try:
                channel_id = self.save_data['channel_id']
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                raise StopMessage(f'The game channel was not found. Maybe it has been deleted, or I can\'t access it.\nChannel: <#{channel_id}> `ID: {channel_id}`')
            
            dead = False
            facial_expression = FacialExpression.NORMAL
            grid = numpy.array(self.save_data['grid'])

            if self.save_data['message_id'] == 0:
                # No previous message, don't update game logic
                await self.send_grid(channel)
                continue

            # Get the previous results
            try:
                message_id = self.save_data['message_id']
                message = await channel.fetch_message(message_id)
            except discord.HTTPException:
                # TODO: do something when this fails
                pass

            self.reactions = message.reactions
            if self.save_data['configuration']['twitter_controls']:
                # Using Twitter controls
                likes = self.find_reaction_count(Emoji.LIKE)
                retweets = self.find_reaction_count(Emoji.RETWEET)

                try:
                    ratio = likes / retweets
                    ratio_min = 1 - (self.save_data['configuration']['tie_threshold'] / 100)
                    ratio_max = 1 + (self.save_data['configuration']['tie_threshold'] / 100)
                    is_tie = ratio_min <= ratio <= ratio_max
                except ZeroDivisionError:
                    is_tie = True

                if is_tie:
                    # Go straight
                    facing = self.save_data['facing']

                elif self.save_data['facing'] in ('up','down'):
                    if likes > retweets:
                        facing = 'right'
                    else:
                        facing = 'left'
                    
                else:
                    if likes > retweets:
                        facing = 'down'
                    else:
                        facing = 'up'

            else:
                # Using arrow controls
                count = {}
                count['up'] = self.find_reaction_count(Emoji.UP)
                count['down'] = self.find_reaction_count(Emoji.DOWN)
                count['left'] = self.find_reaction_count(Emoji.LEFT)
                count['right'] = self.find_reaction_count(Emoji.RIGHT)

                # Prevent the snake from going backwards
                del count[self.opposite(self.save_data['facing'])]

                directions = ('left', 'right', 'down', 'up')
                facing = max(directions, key=lambda direction: count[direction] if direction in count else -1)

                # Check if there is a tie (The highest score appears more than once)
                is_tie = list(count.values()).count(count[facing]) > 1

                if is_tie: facing = self.save_data['facing']
    
            # Update the grid
            # Check out of bounds
            find_head = numpy.where(grid == SnakeObject.HEAD)
            head_position = list(zip(find_head[0], find_head[1]))[0]

            predicates = (
                facing == 'left' and head_position[1] == 0,
                facing == 'right' and head_position[1] == len(grid[0]) - 1,
                facing == 'up' and head_position[0] == 0,
                facing == 'down' and head_position[0] == len(grid) - 1
            )

            if any(predicates):
                dead = True
            
            else:
                # Find the next head position
                next_pos = {
                    'left': (head_position[0], head_position[1] - 1),
                    'right': (head_position[0], head_position[1] + 1),
                    'up': (head_position[0] - 1, head_position[1]),
                    'down': (head_position[0] + 1, head_position[1]),
                }
                new_pos = next_pos[facing]
                tile = grid[new_pos[0]][new_pos[1]]

                # Body Tile
                if tile > 1:
                    # The snake crashed into itself, RIP
                    dead = True
                
                elif tile == SnakeObject.APPLE:
                    self.save_data['score'] += 1
                    if self.save_data['score'] > self.save_data['best']:
                        self.save_data['best'] = self.save_data['score']
                    
                    new_apple_pos = self.find_new_apple_position(grid)
                    grid[new_apple_pos[0]][new_apple_pos[1]] = SnakeObject.APPLE
                    facial_expression = FacialExpression.EATING
                    # Make the body grow
                    grid = numpy.where(grid > 0, grid + 1, grid)

            if not dead:
                # Make the snake move forward
                grid = numpy.where(grid > 0, grid - 1, grid)
                # Move head forward
                grid[new_pos[0]][new_pos[1]] = SnakeObject.HEAD
                grid[head_position[0]][head_position[1]] = self.save_data['score']
            else:
                facial_expression = FacialExpression.DEAD
            
            self.save_data['facing'] = facing
            await self.send_grid(channel, grid=grid.tolist(), facial_expression=facial_expression)


    async def send_grid(self, channel, grid=None, facial_expression=None):
        if grid is None: grid = self.save_data['grid']
        if facial_expression is None: facial_expression = self.save_data['facial_expression']

        rendered_grid = self.render_grid(grid, facial_expression)

        # Get next update timestamp
        current_time = datetime.utcnow()
        delta = timedelta(minutes=self.save_data['configuration']['update_frequency'])
        next_update = current_time + delta

        twitter_controls = self.save_data['configuration']['twitter_controls']
        facing = self.save_data['facing']
        dead = facial_expression == FacialExpression.DEAD

        if twitter_controls and not dead:
            if facing in ('up', 'down'):
                rendered_grid += f'\n{Emoji.RETWEET}{Emoji.LEFT}\n\n{Emoji.LIKE}{Emoji.RIGHT}'
            else:
                rendered_grid += f'\n{Emoji.RETWEET}{Emoji.UP}\n\n{Emoji.LIKE}{Emoji.DOWN}'

        color = self.save_data['configuration']['embed_color']
        embed_color = discord.Colour.from_rgb(color[0], color[1], color[2])
        embed = discord.Embed(description=rendered_grid, color=embed_color, timestamp=next_update)
        embed.set_author(name=f'Score: {self.save_data["score"]}\nBest: {self.save_data["best"]}')
        embed.set_footer(text='Next update ')

        if dead:
            embed.timestamp = discord.Embed.Empty
            embed.set_footer(text='oops')

        msg = await channel.send(embed=embed)

        if dead:
            # Restart the game
            with open("settings.json","r") as f:
                settings = json.load(f)
            
            self.save_data = self.create_save_data(channel, settings, best=self.save_data['best'])
            self.save_data['next_update'] = int(next_update.timestamp())
            await self.save()
            return

        if not any((facing == 'right', twitter_controls)): await msg.add_reaction(Emoji.LEFT)
        if not any((facing == 'left', twitter_controls)): await msg.add_reaction(Emoji.RIGHT)
        if not any((facing == 'up', twitter_controls)): await msg.add_reaction(Emoji.DOWN)
        if not any((facing == 'down', twitter_controls)): await msg.add_reaction(Emoji.UP)

        if twitter_controls:
            await msg.add_reaction(Emoji.RETWEET)
            await msg.add_reaction(Emoji.LIKE)

        self.save_data['grid'] = grid
        self.save_data['facial_expression'] = facial_expression
        self.save_data['save_timestamp'] = int(current_time.timestamp())
        self.save_data['next_update'] = int(next_update.timestamp())
        self.save_data['message_id'] = msg.id

        await self.save()
    
    async def save(self):
        with open('save.json', 'w') as f:
            json.dump(self.save_data, f, indent=4)

    def find_new_apple_position(self, grid):
        max_x = len(grid[0])
        max_y = len(grid)

        while True:
            x = randrange(0, max_x)
            y = randrange(0, max_y)

            if grid[y][x] == 0:
                # A valid position for the apple, we can exit the loop
                return y, x

    def find_reaction_count(self, emoji):
        find_emoji = [reaction for reaction in self.reactions if reaction.emoji == emoji]
        if find_emoji:
            return find_emoji[0].count
        else:
            return 0

    def opposite(self, direction):
        opposites = {
            'left': 'right',
            'right': 'left',
            'up': 'down',
            'down': 'up'
        }

        return opposites[direction]

    def render_grid(self, grid, facial_expression: FacialExpression):
        # Emojis used to render the grid
        BLANK = ':black_large_square:'
        APPLE = ':apple:'
        SNAKE_BODY = ':yellow_square:'
        HEAD_NORMAL = ':flushed:'
        HEAD_EATING = ':weary:'
        HEAD_DEAD = ':dizzy_face:'
        TAIL = ':yellow_circle:'

        rendered = ''
        for i in range(len(grid)):
            for j in range(len(grid[i])):
                
                if grid[i][j] == SnakeObject.BLANK:
                    rendered += BLANK
                
                elif grid[i][j] == SnakeObject.APPLE:
                    rendered += APPLE
                
                elif grid[i][j] == SnakeObject.HEAD:

                    if facial_expression == FacialExpression.NORMAL:
                        rendered += HEAD_NORMAL
                    elif facial_expression == FacialExpression.EATING:
                        rendered += HEAD_EATING
                    else:
                        rendered += HEAD_DEAD
                
                elif grid[i][j] == 1:
                    rendered += TAIL

                else:
                    rendered += SNAKE_BODY
        
            # New line after each row
            rendered += '\n'
        
        return rendered
