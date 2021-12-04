import discord
import os
import json
import random

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
        await message.channel.send("BobbyB Says: " + msg)
  if client.user.mentioned_in(message) and message.author not in blocked_users and message.content.lower().find('gandalf') != -1:
        print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
        msg = get_random_quote('./gandalfQuotes.json').format(message)
        await message.channel.send("Gandalf Says: " + msg)

client.run(os.environ['TOKEN'])


