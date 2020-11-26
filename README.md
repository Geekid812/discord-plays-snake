[![GitHub](https://img.shields.io/github/license/geekid812/discord-plays-snake?style=for-the-badge)](https://github.com/geekid812/discord-plays-snake)

[![Twitter Follow](https://img.shields.io/twitter/follow/geekid812?style=social)](https://twitter.com/geekid812)
[![Discord](https://img.shields.io/discord/760194844001304616?logo=discord&style=social)](https://discord.gg/mHnjK8K)

# Discord Plays Snake
A Discord bot that plays Snake in your server.

## Setup
No public instance of this bot is available. You must host it yourself.

Python version **3.8** or higher is required to run the bot.
```sh
# Clone the repository
git clone https://github.com/Geekid812/discord-plays-snake
# Get into the directory
cd discord-plays-snake
# Install dependencies
pip install -r requirements.txt
```
To make a new Discord bot, create an application on the [Discord Developer Portal](https://discord.com/developers/applications/) and invite it to your server.

Create a new file `token.txt` and paste your bot token in.

Run the bot using `python bot.py`. This can fail if you are not using a supported version of Python. (use `python --version` to check your version)

## Commands
`ping`: Check the bot latency.\
`start <channel>`: Start a Snake game in the specified channel. There can only be one instance of Snake running per bot.\
`resume`: Resume a Snake game from save data.\
`reset`: Reset save data.\
`about`: Version and bot info.

## Configuration
You can modify `settings.json` and `emojis.json` to alter the bot's behaviour.

`settings.json` parameters:
- `prefix`: The bot prefix.
- `print_traceback`: A boolean indicating whether to print error traceback to the console.
- `activity`: The bot's activity. This will show up in its status.
- `activity_type` Either `playing`, `listening`, `watching`, `streaming` or `competing`. (case sensitive)
- `twitter_controls`: A boolean indicating whether the game should use Twitter controls (likes and retweets). If this is `false` arrow controls are used instead.
- `grid_height`: A number representing Snake's grid height.
- `grid_width`: A number representing Snake's grid width.
- `update_frequency`: The number of minutes between each game update.
- `tie_threshold`: A percentage representing the maximum difference between likes and retweets for a tie to happen. (Twitter controls only)
- `embed_color`: A list of 3 numbers representing the RGB value of the game embed.

## Contributing
PRs are welcome! Make sure to open an issue for breaking changes in order to discuss them beforehand.
