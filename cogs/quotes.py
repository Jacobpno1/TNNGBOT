import discord
import random
import os
from discord.ext import commands
from db.manager import MongoDBManager
from utils.quotes import get_random_quote

# Database setup
MONGO_DBNAME = os.environ['MONGO_DBNAME']
MONGO_URI = os.environ['MONGO_URI']
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)

class Quotes(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot    

  @commands.Cog.listener()  
  async def on_message(self, message: discord.Message):
    client = self.bot
    if not client.user:  # make sure the bot user is ready
      return
    # Do not reply to comments from these users, including itself (client.user)
    blocked_users = [ client.user ]

    if message.author in blocked_users:
      return

    if client.user.mentioned_in(message):
      if message.content.lower().find('bobbyb') != -1:
        print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
        msg = get_random_quote('./bobbyBquotes.json').format(message)
        await message.channel.send(str(client.get_emoji(917134295225741313)) + " BobbyB: " + msg)

      if message.content.lower().find('machoman') != -1:
        print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
        msg = get_random_quote('./machoManQuotes.json').format(message)
        await message.channel.send(str(client.get_emoji(1278457600404623401)) + " Macho Man: " + msg)

      if message.content.lower().find('gandalf') != -1:
        print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
        msg = get_random_quote('./gandalfQuotes.json').format(message)
        await message.channel.send(str(client.get_emoji(917135652171161681)) + " Gandalf: " + msg)

    # if random.randrange(1, int(os.environ['pokemonSpawnRate'])) == 1:
    #   await spawnPokemon(message)     

    await db.messages.insert_message(message)

  
  def sarcasm(self, char):  
    if bool(random.getrandbits(1)):
      char = char.capitalize()
    return char

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload): 
    client = self.bot 
    if not client.user:  # make sure the bot user is ready
      return
    if payload.user_id == client.user.id:  # do not respond to itself
      return
    if payload.guild_id is None:  # do not respond to DMs
      return  
    guild = client.get_guild(payload.guild_id)
    if guild is None:  # do not respond if guild is None
      return
    channel = guild.get_channel(payload.channel_id)
    if not isinstance(channel, discord.TextChannel):
      return

    message = await channel.fetch_message(payload.message_id)

    # :bobbyb:917134295225741313
    if (payload.emoji.name == "bobbyb"):    
      await message.reply(str(payload.emoji) + " BobbyB: " + get_random_quote('./bobbyBquotes.json').format(message))    
    
    # :gandalf:917135652171161681
    if (payload.emoji.name == "gandalf"):    
      await message.reply(str(payload.emoji) + " Gandalf: " + get_random_quote('./gandalfQuotes.json').format(message))      
      
    if (payload.emoji.name == "laszlo"):    
      await message.reply(str(payload.emoji) + " Laszlo: " + get_random_quote('./laszloQuotes.json').format(message))

    if (payload.emoji.name == "machoman"):    
      await message.reply(str(payload.emoji) + " Macho Man: " + get_random_quote('./machoManQuotes.json').format(message))
    
    if (payload.emoji.name == "sarcasm"):
      lst = []
      lst.extend(message.content.lower())
      newstr = ''.join(list(map(self.sarcasm, lst)))
      await message.reply(newstr + " " + str(payload.emoji))
      
  @commands.Cog.listener()
  async def on_raw_reaction_remove(self, payload):      
    client = self.bot
    user = await client.fetch_user(payload.user_id)    
    db.messages.remove_reaction(payload, user)


async def setup(bot: commands.Bot):
  await bot.add_cog(Quotes(bot))
