import discord
import os
import json
import random
import requests

from keep_alive import keep_alive

client = discord.Client()

# for emoji in client.guild.emojis:
#   print(emoji.id)

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

def get_random_quote(file):
    """ Returns random quote from quotes file"""

    with open(file, 'r') as quotes:
        bobbyb_quotes = json.load(quotes)
    
    return random.choice(bobbyb_quotes)

@client.event
async def on_message(message):
  # Do not reply to comments from these users, including itself (client.user)
  blocked_users = [ client.user ]

  if message.author in blocked_users:
    return

  if client.user.mentioned_in(message):
    if message.content.lower().find('bobbyb') != -1:
      print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
      msg = get_random_quote('./bobbyBquotes.json').format(message)
      await message.channel.send(str(client.get_emoji(917134295225741313)) + " BobbyB: " + msg)

    if message.content.lower().find('gandalf') != -1:
      print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
      msg = get_random_quote('./gandalfQuotes.json').format(message)
      await message.channel.send(str(client.get_emoji(917135652171161681)) + " Gandalf: " + msg)
    
    if message.content.lower().find('pokemon') != -1:
      r = requests.get("https://pokeapi.co/api/v2/pokemon/" + str(random.randrange(1, 151))) 
      pokemon = r.json()
      embed = discord.Embed(title=f"A wild {pokemon['name']} appears!")
      embed.set_thumbnail(url=pokemon['sprites']['front_default'])  
      await message.channel.send(embed=embed)

# @client.command()
async def getmsg(ctx, msgID: int):
  return await ctx.fetch_message(msgID)

def sarcasm(char):  
  if bool(random.getrandbits(1)):
    char = char.capitalize()
  return char

@client.event
async def on_raw_reaction_add(payload):  
  guild = client.get_guild(payload.guild_id)
  channel = guild.get_channel(payload.channel_id)
  message = await channel.fetch_message(payload.message_id)

  # if (payload.emoji.name == "ringwhispers"):    
  #   await message.reply(str(client.get_emoji(917135652171161681)) + " Gandalf: Keep it secret, Keep it safe.")
  
  # :bobbyb:917134295225741313
  if (payload.emoji.name == "bobbyb"):    
    await message.reply(str(payload.emoji) + " BobbyB: " + get_random_quote('./bobbyBquotes.json').format(message))    
  
  # :gandalf:917135652171161681
  if (payload.emoji.name == "gandalf"):    
    await message.reply(str(payload.emoji) + " Gandalf: " + get_random_quote('./gandalfQuotes.json').format(message))
    # print(f"gandalf emoji_id: {str(payload.emoji)}")
  
  if (payload.emoji.name == "sarcasm"):
    lst = []
    lst.extend(message.content)
    newstr = ''.join(list(map(sarcasm, lst)))
    await message.reply(newstr + " " + str(payload.emoji))

keep_alive()
client.run(os.environ['TOKEN'])


