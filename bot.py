import nextcord
from nextcord.ext import commands
import os


intents = nextcord.Intents.default()
intents.members = True    
intents.reactions = True    
intents.message_content = True 

bot = commands.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f'A connection has been established with {bot.user.name}.')
bot.load_extension('role_changer')

print(f"A connection is being established with the bot.")
bot.run('your token')