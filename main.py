import discord
import os
import json
import random

from keep_alive import keep_alive

client = discord.Client()

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

  if client.user.mentioned_in(message) and message.author not in blocked_users and message.content.lower().find('bobbyb') != -1:
        print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
        msg = get_random_quote('./bobbyBquotes.json').format(message)
        await message.channel.send("BobbyB: " + msg)
  if client.user.mentioned_in(message) and message.author not in blocked_users and message.content.lower().find('gandalf') != -1:
        print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
        msg = get_random_quote('./gandalfQuotes.json').format(message)
        await message.channel.send("Gandalf: " + msg)

# @client.command()
async def getmsg(ctx, msgID: int):
  return await ctx.fetch_message(msgID)

@client.event
async def on_raw_reaction_add(payload):  
  guild = client.get_guild(payload.guild_id)
  channel = guild.get_channel(payload.channel_id)
  message = await channel.fetch_message(payload.message_id)

  if (payload.emoji.name == "ringwhispers"):    
    await message.reply("Gandalf: Keep it secret, Keep it safe.")
  
  if (payload.emoji.name == "bobbyb"):    
    await message.reply("BobbyB: " + get_random_quote('./bobbyBquotes.json').format(message))
  
  if (payload.emoji.name == "gandalf"):    
    await message.reply("Gandalf: " + get_random_quote('./gandalfQuotes.json').format(message))

keep_alive()
client.run(os.environ['TOKEN'])


