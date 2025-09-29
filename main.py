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

  if message.channel.type == discord.ChannelType.public_thread and message.channel.name.startswith("Battle:"): 
    await handle_battle_message(message)

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
  await mongoDBAPI.createPokemon("Pokemon", "TNNGBOT", "JacobTEST", pokeNo, pokemon, str(new_message.id), catch_count)

# async def handle_attle_message(message):
  #doo stuf

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

  if (payload.emoji.name == "👍"):    
    if (message.content is not None and message.content.startswith("[TRADE]")):      
      if (str(user.id) == str(message.mentions[0].id)):
        user1 = message.mentions[1]
        user2 = message.mentions[0]
        embed = message.embeds
        user1_pokemon_number = embed[0].title.split('[')[-1].replace(']','')
        user2_pokemon_number = embed[1].title.split('[')[-1].replace(']','')
        user1_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", user1, int(user1_pokemon_number))
        if user1_pokemon is False or user1_pokemon is None:
          await message.edit(content=f"[TRADE FAILED] {user1.mention} does not own a pokemon with number {user1_pokemon_number}.", embeds=[])
          return
        user2_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", user2, int(user2_pokemon_number))
        if user2_pokemon is False or user2_pokemon is None:
          await message.edit(content=f"[TRADE FAILED] {user2.mention} does not own a pokemon with number {user2_pokemon_number}.", embeds=[])
          return 
        result = await mongoDBAPI.tradePokemon("Pokemon", "TNNGBOT", "JacobTEST", user1, user2, user1_pokemon, user2_pokemon)        
        if result == True:
          await message.edit(content=f"[TRADE COMPLETED] {user.mention} traded <:pokeball:1419845300742520964> {user1_pokemon['name']} [{user1_pokemon['number']}] for {message.mentions[0].mention}'s <:pokeball:1419845300742520964> {user2_pokemon['name']} [{user2_pokemon['number']}]!",
                             embeds=[],)                   
        else:
          await message.edit(content=f"[TRADE FAILED] Something went wrong with the trade between {user1.mention} and {user2.mention}.", embeds=[])
  
  await mongoDBAPI.addReaction("Messages", "TNNGBOT", "JacobTEST", payload, user)

async def throw_pokeball(payload, user):
    guild = client.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)    
    message = await channel.fetch_message(payload.message_id)      
    if (len(message.embeds) != 0 and message.embeds[0] is not None and message.embeds[0].footer.text is not None):
      # pokeNo = int(message.embeds[0].footer.text)
      try:
        pokemon = await mongoDBAPI.getPokemonByMessageID("Pokemon", "TNNGBOT", "JacobTEST", str(message.id))
        if pokemon is None:
          print("No pokemon found for message ID " + str(message.id))
          return        
        hasUserAttempted = str(user.id) in pokemon["catch_attempts"]
        catchable = len(pokemon["catch_attempts"]) >= pokemon["catch_count"]
      
        if hasUserAttempted is False and pokemon["caught"] is False:
          if catchable is True:
            # Catch the Pokemon
            success = await mongoDBAPI.catchPokemon("Pokemon", "TNNGBOT", "JacobTEST", str(message.id), pokemon, user)
            if success is True:
              message.embeds[0].add_field(name=f"{str(payload.emoji)} Gotcha! {pokemon['name'].capitalize()} was caught by {user.display_name}!", 
                value="Use /pokedex to see all the Pokemon you've caught and /pokemon to summon them!", inline=False)  
              await message.edit(embed=message.embeds[0]) 
            else :
              await throw_pokeball(payload, user);       
          else:
            # Track the failed attempt
            success = await mongoDBAPI.addCatchAttempt("Pokemon", "TNNGBOT", "JacobTEST", str(message.id), user, pokemon)
            if success is True:
              message.embeds[0].add_field(name=f"Oh no {user.display_name}! {pokemon['name'].capitalize()} broke free!", value="", inline=False)
              await message.edit(embed=message.embeds[0])
            else:
              await throw_pokeball(payload, user); 
      except Exception as e:
        print(f"Error processing pokeball throw: {e}")   
        

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
        embed.add_field(name=f"<:pokeball:1419845300742520964> #{p['number']} {p['name'].capitalize()}", value=f"Caught on {p['created_at']}", inline=False)
        # embed.set_thumbnail(url=p['image_url'])  
      await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
      await interaction.response.send_message("You haven't caught any Pokemon yet! React to a Pokemon with a <:pokeball:1419845300742520964> to catch it!", ephemeral=True)

@client.tree.command(name="pokemon", description="Summon a Pokemon you've caught!")
@app_commands.describe(pokemon_number="The number of the Pokemon you want to summon (1-151)")
async def pokedex(interaction: discord.Interaction, pokemon_number: str):    
  caught_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", interaction.user, int(pokemon_number))
  if interaction.channel.type == discord.ChannelType.public_thread and interaction.channel.name.startswith("Battle:"):
    battle = await mongoDBAPI.getActiveBattleByThreadID(interaction.channel.id)
    if battle is not False and battle is not None:
      my_pokemon_arr = [pokemon for pokemon in battle["pokemon"] if pokemon["owner_id"] == str(interaction.user.id)]
      #if my pokemon does not exist in battle pokemon list and max participants reached
      is_pokemon_in_battle = next((pokemon for pokemon in my_pokemon_arr if pokemon["owner_id"] == str(interaction.user.id) and caught_pokemon["message_id"] == pokemon["message_id"]), None)
      current_turn_pokemon_message_id = next((turn["pokemon_message_id"] for turn in battle["current_round"] if turn["user_id"] == str(interaction.user.id)), None)
      if len(my_pokemon_arr) >= battle["number_of_pokemon"] and is_pokemon_in_battle is None:
        await interaction.response.send_message(f"❗ You can only summon up to {battle['max_pokemons_per_user']} Pokemon in this battle.", ephemeral=True)
        return
      #if pokemon is not current pokemon, dimiss current
      if current_turn_pokemon_message_id is not None and current_turn_pokemon_message_id != caught_pokemon["message_id"]:
        current_pokemon = next(pokemon for pokemon in battle["pokemon"] if pokemon["message_id"] == current_turn_pokemon_message_id)
        await interaction.response.send_message(f"❗ You can only command your current Pokemon in battle. Dismissing {interaction.user.display_name}'s current Pokemon.", ephemeral=True)
        return
      #if pokemon is not already in battle, summon it
      if is_pokemon_in_battle is False:
        pokemon_r = await requests.get("https://pokeapi.co/api/v2/pokemon/" + str(pokeNo)) 
        pokemon = pokemon_r.json()
        result = await mongoDBAPI.summonPokemonToBattle(battle, pokemon, interaction.user)
        if result is True:
          embed = discord.Embed(title=f"{interaction.user.display_name} summons: <:pokeball:1419845300742520964> {pokemon['name'].capitalize()}!")    
          embed.set_thumbnail(url=pokemon['sprites']['front_default'])      
          await interaction.response.send_message(embed=embed)
        else:
          await interaction.response.send_message("❗ Something went wrong while summoning your Pokemon to the battle.", ephemeral=True)
        return       
  
  if caught_pokemon:
    embed = discord.Embed(title=f"I choose you... <:pokeball:1419845300742520964> {caught_pokemon['name'].capitalize()}!")    
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

@client.tree.command(name="trade", description="Trade a Pokemon with another user")
@app_commands.describe(user="User to trade with.", my_pokemon_number="My PokeNumber (1-151)", for_pokemon_number="Their PokeNumber (1-151)")
async def trade_pokemon(interaction: discord.Interaction, user: discord.Member, my_pokemon_number: int, for_pokemon_number: int):    
  i_user = interaction.user
  my_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", i_user, int(my_pokemon_number))
  for_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", user, int(for_pokemon_number))
  if my_pokemon is False or my_pokemon is None:
    await interaction.response.send_message(f"❗ You do not own a pokemon with number {my_pokemon_number}.", ephemeral=True) 
    return
  if for_pokemon is False or for_pokemon is None:
    await interaction.response.send_message(f"❗ {user.display_name} does not own a pokemon with number {for_pokemon_number}.", ephemeral=True) 
    return
  for_pokemon_embed = discord.Embed(title=f"{user.display_name} trades: <:pokeball:1419845300742520964> {for_pokemon['name']} [{for_pokemon['number']}]")
  for_pokemon_embed.set_thumbnail(url=for_pokemon['image_url'])  
  my_pokemon_embed = discord.Embed(title=f"{i_user.display_name} trades: <:pokeball:1419845300742520964> {my_pokemon['name']} [{my_pokemon['number']}]")
  my_pokemon_embed.set_thumbnail(url=my_pokemon['image_url'])  
  
    
  await interaction.response.send_message(f"[TRADE] {user.mention}, {i_user.mention} wants to trade Pokemon! :thumbsup: to accept the trade.", 
                                          embeds=[my_pokemon_embed,for_pokemon_embed], 
                                          ephemeral=False)
  
@client.tree.command(name="battle", description="Battle Pokemon with another user")
@app_commands.describe(user="User to battle with.", number_of_pokemon="Number of Pokemon to battle with(1-3)")
async def battle_pokemon(interaction: discord.Interaction, user: discord.Member, number_of_pokemon: int):    
  # Create a thread to battle in
  if number_of_pokemon < 1 or number_of_pokemon > 3:
    await interaction.response.send_message(f"❗ You can only battle with 1 to 3 Pokemon.", ephemeral=True) 
    return
  i_user = interaction.user
  battle = await mongoDBAPI.createBattle(thread.id, i_user, user, number_of_pokemon)
  thread = await interaction.channel.create_thread(name=f"Battle: {i_user.display_name} vs {user.display_name}", type=discord.ChannelType.public_thread)
  await thread.send(f"{i_user.mention} has challenged {user.mention} to a Pokemon battle! The winner takes all!")
  await interaction.response.send_message(f"✅ Battle thread created: {thread.mention}", ephemeral=True)
  
  
@client.tree.command(name="command", description="Give a command to your Pokemon in a battle")
@app_commands.describe(command="Command to give your Pokemon")
async def battle_pokemon(interaction: discord.Interaction, command: str):    
  # If user is in a battle thread, process the command
  if interaction.channel.type == discord.ChannelType.public_thread and interaction.channel.name.startswith("Battle:"): 
    await interaction.response.send_message(f"{interaction.user.mention} commands their Pokemon to '{command}'!", ephemeral=False)
  else:
    await interaction.response.send_message(f"❗ You can only command Pokemon in a battle.", ephemeral=True)
  

keep_alive()
client.run(os.environ['TOKEN'])


