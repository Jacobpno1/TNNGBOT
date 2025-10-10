from collections import Counter
from datetime import datetime
import os
import discord
import random
from discord import app_commands 
from discord import Interaction
from discord.ext import commands
import pytz
from tnngbot.db.manager import MongoDBManager
import requests
import json

# Database setup
MONGO_DBNAME = os.environ['MONGO_DBNAME']
MONGO_URI = os.environ['MONGO_URI']
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)

class Pokemon(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot
    
  ### pokemon event listeners
  @commands.Cog.listener()
  async def on_message(self, message: discord.Message):    
    # make sure the bot user is ready
    if not self.bot.user:  
      return             
    # Do not reply if the message is from the bot itself
    if message.author == self.bot.user:
      return 
    # if random.randrange(1, int(os.environ['pokemonSpawnRate'])) == 1:
    await self.spawnPokemon(message)   
      
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
    user = await client.fetch_user(payload.user_id)
    
    if (payload.emoji.name == "pokeball"):  
      await self.throw_pokeball(payload, user) 

    if (payload.emoji.name == "👍"):  
      if (message.content is not None and message.content.startswith("[TRADE]")):    
        if (str(user.id) == str(message.mentions[0].id)):
          user1 = message.mentions[1]
          user2 = message.mentions[0]
          embed = message.embeds
          if embed[0].title is None or embed[1].title is None:
            await message.edit(content=f"[TRADE FAILED] {user.mention} something went wrong with the trade between {user1.mention} and {user2.mention}.", embeds=[])
            return
          user1_pokemon_number = embed[0].title.split('[')[-1].replace(']','')
          user2_pokemon_number = embed[1].title.split('[')[-1].replace(']','')
          user1_pokemon = db.pokemon.get_pokemon(user1, int(user1_pokemon_number))
          if user1_pokemon is False or user1_pokemon is None:
            await message.edit(content=f"[TRADE FAILED] {user1.mention} does not own a pokemon with number {user1_pokemon_number}.", embeds=[])
            return
          user2_pokemon = db.pokemon.get_pokemon( user2, int(user2_pokemon_number))
          if user2_pokemon is False or user2_pokemon is None:
            await message.edit(content=f"[TRADE FAILED] {user2.mention} does not own a pokemon with number {user2_pokemon_number}.", embeds=[])
            return 
          result = db.pokemon.trade_pokemon(user1, user2, user1_pokemon, user2_pokemon)    
          if result == True:
            await message.edit(content=f"[TRADE COMPLETED] {user.mention} traded <:pokeball:1419845300742520964> {user1_pokemon['name']} [{user1_pokemon['number']}] for {message.mentions[0].mention}'s <:pokeball:1419845300742520964> {user2_pokemon['name']} [{user2_pokemon['number']}]!",
                      embeds=[],)           
          else:
            await message.edit(content=f"[TRADE FAILED] Something went wrong with the trade between {user1.mention} and {user2.mention}.", embeds=[])
  
  ### Pokemon Commands    
  @app_commands.command(name="pokedex", description="List the Pokemon you've caught!")  
  @app_commands.describe(
      sort_by="Choose how to sort your Pokémon",
      direction="Choose ascending or descending order"
  )
  @app_commands.choices(
      sort_by=[
          app_commands.Choice(name="Number", value="number"),
          app_commands.Choice(name="Name", value="name"),
          app_commands.Choice(name="Caught Date", value="caught_at"),
      ],
      direction=[
          app_commands.Choice(name="Ascending", value="asc"),
          app_commands.Choice(name="Descending", value="desc"),
      ],
      duplicates=[
          app_commands.Choice(name="Show", value="show"),
          app_commands.Choice(name="Hide", value="hide"),
          app_commands.Choice(name="Only", value="only"),
      ]
  )
  async def pokedex(
    self,
    interaction: Interaction,
    sort_by: str = "number",
    direction: str = "asc",
    duplicates: str = "show"
  ):
    caught_pokemon = db.pokemon.get_my_caught_pokemon(
      interaction.user, sort_by=sort_by, ascending=(direction == "asc")
    )

    if caught_pokemon:
      if duplicates == "hide":
        seen = set()
        filtered = []
        for p in caught_pokemon:
          if p["number"] not in seen:
            seen.add(p["number"])
            filtered.append(p)
        caught_pokemon = filtered

      elif duplicates == "only":
        # Count occurrences by number
        counts = Counter(p["number"] for p in caught_pokemon)
        caught_pokemon = [p for p in caught_pokemon if counts[p["number"]] > 1]
      # Build a table header
      table = "```"
      table += f"   {'No.':<5} {'Name':<15} {'Caught On'}\n"
      table += "-" * 49 + "\n"
      local_tz = pytz.timezone("US/Eastern")

      # Fill rows
      for p in caught_pokemon:
        if p["caught_at"] is None:
          continue
        dt = datetime.fromisoformat(p["caught_at"])
        dt_local = dt.astimezone(local_tz)
        formatted_date = dt_local.strftime("%m/%d/%Y %I:%M %p")

        table += f"◓  {p['number']:<5} {p['name'].capitalize():<15} {formatted_date} EST\n"        

      table += "```"

      await interaction.response.send_message(
        f"**{interaction.user.display_name}'s Pokedex**\n{table}",
        ephemeral=True
      )
    else:
      await interaction.response.send_message(
        "You haven't caught any Pokemon yet! React to a Pokemon with a <:pokeball:1419845300742520964> to catch it!",
        ephemeral=True
      )
        
  @app_commands.command(name="pokemon", description="Summon a Pokemon you've caught!")
  @app_commands.describe(pokemon_number="The number of the Pokemon you want to summon (1-151)")
  async def pokemon(self, interaction: discord.Interaction, pokemon_number: str):  
    caught_pokemon = db.pokemon.get_pokemon( interaction.user, int(pokemon_number))
    if caught_pokemon:
      embed = discord.Embed(title=f"I choose you... <:pokeball:1419845300742520964> {caught_pokemon['name'].capitalize()}!")  
      embed.set_thumbnail(url=caught_pokemon['image_url'])    
      await interaction.response.send_message(embed=embed)
    else:
      await interaction.response.send_message("You haven't caught that pokemon.", ephemeral=True) 

  @app_commands.command(name="spawn_pokemon", description="[Admin Only] Spawn a pokemon by number")
  @app_commands.describe(pokemon_number="The number of the Pokemon you want to spawn (1-151)", catch_count="How many attempts before catching")
  async def spawn_pokemon(self, interaction: discord.Interaction, pokemon_number: str, catch_count: str):  
    if not isinstance(interaction.user, discord.Member):
      await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
      return
    if interaction.user is not None and interaction.user.guild_permissions.administrator:
      await self.spawnPokemon(interaction, int(pokemon_number), catch_count=int(catch_count))
      await interaction.response.send_message(f"Spawned pokemon number {pokemon_number}!", ephemeral=True) 
    else:
      await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

  @app_commands.command(name="trade", description="Trade a Pokemon with another user")
  @app_commands.describe(user="User to trade with.", my_pokemon_number="My PokeNumber (1-151)", for_pokemon_number="Their PokeNumber (1-151)")
  async def trade_pokemon(self, interaction: discord.Interaction, user: discord.Member, my_pokemon_number: int, for_pokemon_number: int):  
    i_user = interaction.user
    my_pokemon = db.pokemon.get_pokemon( i_user, int(my_pokemon_number))
    for_pokemon =  db.pokemon.get_pokemon( user, int(for_pokemon_number))
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
  
  async def throw_pokeball(self, payload, user):
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
    if (len(message.embeds) != 0 and message.embeds[0] is not None and message.embeds[0].footer.text is not None):
      # pokeNo = int(message.embeds[0].footer.text)
      try:
        pokemon = db.pokemon.get_pokemon_by_message_id(str(message.id))      
        if pokemon is None:
          print("No pokemon found for message ID " + str(message.id))
          return    
        hasUserAttempted = str(user.id) in pokemon["catch_attempts"]
        catchable = len(pokemon["catch_attempts"]) >= pokemon["catch_count"]
        
        if hasUserAttempted is False and pokemon["caught"] is False:
          if catchable is True:
          # Catch the Pokemon      
            success = db.pokemon.catch_pokemon(str(message.id), pokemon, user)
            if success is True:
              message.embeds[0].add_field(name=f"{str(payload.emoji)} Gotcha! {pokemon['name'].capitalize()} was caught by {user.display_name}!", 
              value="Use /pokedex to see all the Pokemon you've caught and /pokemon to summon them!", inline=False)  
              await message.edit(embed=message.embeds[0]) 
            else :
              await self.throw_pokeball(payload, user);     
          else:
            # Track the failed attempt
            # success = await mongoDBAPI.addCatchAttempt("Pokemon", "TNNGBOT", "JacobTEST", str(message.id), user, pokemon)
            success = db.pokemon.add_catch_attempt(str(message.id), user, pokemon)
            if success is True:
              message.embeds[0].add_field(name=f"Oh no {user.display_name}! {pokemon['name'].capitalize()} broke free!", value="", inline=False)
              await message.edit(embed=message.embeds[0])
            else:
              await self.throw_pokeball(payload, user); 
      except Exception as e:
        print(f"Error processing pokeball throw: {e}")  

  async def spawnPokemon(self, message, pokemon_number=None, catch_count=None):
    if pokemon_number is None:
      pokePool: list[int] = []
      with open('tnngbot/static/pokemonPool.json', 'r') as pokePoolJson:
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
    catch_count = catch_count if catch_count is not None else random.randint(0, int(os.environ['pokemonMaxAttempts']))
    name = pokemon["name"]
    image_url = pokemon["sprites"]["front_default"]
    db.pokemon.create_pokemon(pokeNo, name, image_url, str(new_message.id), catch_count)
  
async def setup(bot: commands.Bot):
  await bot.add_cog(Pokemon(bot))
