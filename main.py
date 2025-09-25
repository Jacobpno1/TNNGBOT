import discord
import os
import json
import random
import requests
import mongoDBAPI
from dotenv import load_dotenv
from keep_alive import keep_alive
from discord.ext import commands
from discord import app_commands

load_dotenv()

intents = discord.Intents.default()
# client = discord.Client(intents=intents)
client = commands.Bot(command_prefix='!', intents=intents);

# for emoji in client.guild.emojis:
#   print(emoji.id)

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))
  try:
    synced = await client.tree.sync()
    print(f'Synced {len(synced)} command(s)')
  except Exception as e:
      print(e)

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

    if message.content.lower().find('machoman') != -1:
      print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
      msg = get_random_quote('./machoManQuotes.json').format(message)
      await message.channel.send(str(client.get_emoji(1278457600404623401)) + " Macho Man: " + msg)

    if message.content.lower().find('gandalf') != -1:
      print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
      msg = get_random_quote('./gandalfQuotes.json').format(message)
      await message.channel.send(str(client.get_emoji(917135652171161681)) + " Gandalf: " + msg)

  if random.randrange(1, 50) == 1:
    await spawnPokemon(message)     

  await mongoDBAPI.insertMessage("Messages", "TNNGBOT", "JacobTEST", message)

async def spawnPokemon(message, pokemon_number=None, catch_count=None):
  if pokemon_number is None:
    pokePool: list[int] = []
    with open('./pokemonPool.json', 'r') as pokePoolJson:
      pokePool = json.load(pokePoolJson)
    poolNo = random.randrange(0, len(pokePool))
    pokeNo = pokePool[poolNo]
  else:
    pokeNo = pokemon_number
  r = requests.get("https://pokeapi.co/api/v2/pokemon/" + str(pokeNo)) 
  pokemon = r.json()
  embed = discord.Embed(title=f"A wild {pokemon['name']} appears! [{pokeNo}]")
  embed.set_thumbnail(url=pokemon['sprites']['front_default'])  
  embed.set_footer(text=f"{pokeNo}")
  channel = discord.utils.get(message.guild.channels, name="tall-grass")
  new_message = await channel.send(embed=embed)
  catch_count = catch_count if catch_count is not None else random.randint(0, 2)
  await mongoDBAPI.createPokemon("Pokemon", "TNNGBOT", "JacobTEST", pokeNo, pokemon, new_message.id, catch_count)

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
  user = await client.fetch_user(payload.user_id)

  # if (payload.emoji.name == "ringwhispers"):    
  #   await message.reply(str(client.get_emoji(917135652171161681)) + " Gandalf: Keep it secret, Keep it safe.")
  
  # :bobbyb:917134295225741313
  if (payload.emoji.name == "bobbyb"):    
    await message.reply(str(payload.emoji) + " BobbyB: " + get_random_quote('./bobbyBquotes.json').format(message))    
  
  # :gandalf:917135652171161681
  if (payload.emoji.name == "gandalf"):    
    await message.reply(str(payload.emoji) + " Gandalf: " + get_random_quote('./gandalfQuotes.json').format(message))
    # print(f"gandalf emoji_id: {str(payload.emoji)}")
    
  if (payload.emoji.name == "laszlo"):    
    await message.reply(str(payload.emoji) + " Laszlo: " + get_random_quote('./laszloQuotes.json').format(message))

  if (payload.emoji.name == "machoman"):    
    await message.reply(str(payload.emoji) + " Macho Man: " + get_random_quote('./machoManQuotes.json').format(message))
  
  if (payload.emoji.name == "sarcasm"):
    lst = []
    lst.extend(message.content.lower())
    newstr = ''.join(list(map(sarcasm, lst)))
    await message.reply(newstr + " " + str(payload.emoji))

  if (payload.emoji.name == "pokeball"):    
    await throw_pokeball(payload, user) 
             
  
  await mongoDBAPI.addReaction("Messages", "TNNGBOT", "JacobTEST", payload, user)

async def throw_pokeball(payload, user):
    guild = client.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)    
    message = await channel.fetch_message(payload.message_id)      
    if (len(message.embeds) != 0 and message.embeds[0] is not None and message.embeds[0].footer.text is not None):
      # pokeNo = int(message.embeds[0].footer.text)
      pokemon = await mongoDBAPI.getPokemonByMessageID("Pokemon", "TNNGBOT", "JacobTEST", message.id)
      # userHasPokemon = await mongoDBAPI.userHasPokemon("Pokemon", "TNNGBOT", "JacobTEST", user.id, pokeNo)
      hasUserAttempted = str(user.id) in pokemon["catch_attempts"]
      catchable = pokemon["caught"] is False and len(pokemon["catch_attempts"]) >= pokemon["catch_count"]
      if hasUserAttempted is False:
        if catchable is True:
          # Catch the Pokemon
          success = await mongoDBAPI.catchPokemon("Pokemon", "TNNGBOT", "JacobTEST", message.id, pokemon, user)
          if success is True:
            message.embeds[0].add_field(name=f"{str(payload.emoji)} Gotcha! {pokemon['name'].capitalize()} was caught by {user.display_name}!", 
              value="Use /pokedex to see all the Pokemon you've caught and /pokemon to summon them!", inline=False)   
          else :
            await throw_pokeball(payload, user);       
        else:
          # Track the failed attempt
          success = await mongoDBAPI.addCatchAttempt("Pokemon", "TNNGBOT", "JacobTEST", message.id, user, pokemon)
          if success is True:
            message.embeds[0].add_field(name=f"Oh no {user.display_name}! {pokemon['name'].capitalize()} broke free!", value="", inline=False)
          else:
            await throw_pokeball(payload, user);          
        await message.edit(embed=message.embeds[0])

@client.event
async def on_raw_reaction_remove(payload):      
  user = await client.fetch_user(payload.user_id)
  await mongoDBAPI.removeReaction("Messages", "TNNGBOT", "JacobTEST", payload, user)

@client.tree.command(name="pokedex", description="List the Pokemon you've caught!")
async def pokedex(interaction: discord.Interaction):    
    caught_pokemon = await mongoDBAPI.getMyCaughtPokemon("Pokemon", "TNNGBOT", "JacobTEST", interaction.user)
    if caught_pokemon:
      embed = discord.Embed(title=f"{interaction.user.display_name}'s Pokedex")
      for p in caught_pokemon:
        embed.add_field(name=f"#{p['number']} {p['name'].capitalize()}", value=f"Caught on {p['created_at']}", inline=False)
        # embed.set_thumbnail(url=p['image_url'])  
      await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
      await interaction.response.send_message("You haven't caught any Pokemon yet! React to a Pokemon with a :pokeball: to catch it!", ephemeral=True)

@client.tree.command(name="pokemon", description="Summon a Pokemon you've caught!")
@app_commands.describe(pokemon_number="The number of the Pokemon you want to summon (1-151)")
async def pokedex(interaction: discord.Interaction, pokemon_number: str):    
  caught_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", interaction.user, int(pokemon_number))
  if caught_pokemon:
    embed = discord.Embed(title=f"I choose you... {caught_pokemon['name'].capitalize()}!")    
    embed.set_thumbnail(url=caught_pokemon['image_url'])      
    await interaction.response.send_message(embed=embed)
  else:
    await interaction.response.send_message("You haven't caught that pokemon.", ephemeral=True) 

@client.tree.command(name="spawn_pokemon", description="[Admin Only] Spawn a pokemon by number")
@app_commands.describe(pokemon_number="The number of the Pokemon you want to spawn (1-151)", catch_count="How many attempts before catching")
async def spawn_pokemon(interaction: discord.Interaction, pokemon_number: str, catch_count: str):    
  if interaction.user.guild_permissions.administrator:
    await spawnPokemon(interaction, int(pokemon_number), catch_count=int(catch_count))
    await interaction.response.send_message(f"Spawned pokemon number {pokemon_number}!", ephemeral=True) 
  else:
    await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

keep_alive()
client.run(os.environ['TOKEN'])


