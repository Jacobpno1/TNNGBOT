import os
from bson import ObjectId
import discord
import random
from discord import app_commands 
from discord.ext import commands
from tnngbot.db.manager import MongoDBManager
from tnngbot.utils.exponential_probability import exponential_probability
import requests
import json
from datetime import timezone

from tnngbot.utils.type import get_type_emoji_str

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
    last_spawn = db.game_state.get_last_pokemon_spawn()
    if last_spawn and last_spawn['last_pokemon_spawn_datetime']:
      last_spawn_time = last_spawn['last_pokemon_spawn_datetime']     
      current_time = discord.utils.utcnow()
      # return if within one minute of last spawn
      if (current_time - last_spawn_time).total_seconds() < 60:        
        return      
      # ensure DB timestamp is timezone-aware before subtracting
      if getattr(last_spawn_time, "tzinfo", None) is None:
        last_spawn_time = last_spawn_time.replace(tzinfo=timezone.utc)
      elapsed_minutes = (current_time - last_spawn_time).total_seconds() / 60
      max_minutes = int(os.environ['pokemonMaxMinutes'])    
      probability = 1/int(os.environ['pokemonSpawnRate'])
      if not exponential_probability(int(elapsed_minutes), max_minutes, probability):        
        return
    # Fallback to random spawn if no last spawn time found or probability check fails
    elif not random.randrange(1, int(os.environ['pokemonSpawnRate'])) == 1:      
      return
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

  ### Pokemon Commands          
  @app_commands.command(name="pokemon", description="Summon a Pokemon you've caught!")
  @app_commands.describe(pokemon_number="The number of the Pokemon you want to summon (1-151)", level="The level of the pokemon.")
  async def pokemon(self, interaction: discord.Interaction, pokemon_number: str, level:int|None = None):
    if level:
      caught_pokemon = db.pokemon.get_pokemon_lvl( interaction.user, int(pokemon_number), level)
    else:
      caught_pokemon = db.pokemon.get_pokemon( interaction.user, int(pokemon_number))  
    level = 1 if caught_pokemon is None or 'level' not in caught_pokemon else caught_pokemon['level']
    if caught_pokemon:      
      embed = discord.Embed(title=f"I choose you... <:pokeball:1419845300742520964> {caught_pokemon['name'].capitalize()}!")  
      embed.set_thumbnail(url=caught_pokemon['image_url'])  
      embed.set_footer(text=f"Lvl: {level}     No: {caught_pokemon['number']}     Type: {get_type_emoji_str(caught_pokemon['name'])}")  
      await interaction.response.send_message(embed=embed)
    else:
      await interaction.response.send_message("You haven't caught that pokemon.", ephemeral=True) 

  @app_commands.command(name="spawn_pokemon", description="[Admin Only] Spawn a pokemon by number")
  @app_commands.describe(pokemon_number="The number of the Pokemon you want to spawn (1-151)", catch_count="How many attempts before catching", level="Pokemon level", flees="Pokemon flees.")
  async def spawn_pokemon(self, interaction: discord.Interaction, pokemon_number: int | None = None, catch_count:int|None = None, level:int = 1, flees:bool=False):  
    if not isinstance(interaction.user, discord.Member):
      await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
      return
    if interaction.user is not None and interaction.user.guild_permissions.administrator:
      if pokemon_number is None:
        await self.spawnPokemon(interaction, catch_count=catch_count, level=level, flees=flees)
      else:
        await self.spawnPokemon(interaction, pokemon_number, catch_count=catch_count, level=level, flees=flees)
      await interaction.response.send_message(f"Spawned pokemon number {pokemon_number}!", ephemeral=True) 
    else:
      await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)        
  
  async def spawnPokemon(self, message, pokemon_number=None, catch_count=None, level=None, flees=None):  
    if pokemon_number is None:    
      fled_pokemon = db.game_state.retrieve_fled_pokemon()  
      if fled_pokemon:
        pokeNo = fled_pokemon.get("number")     
        level = fled_pokemon.get("level", 1)   
      else:
        pokePool: list[int] = []
        with open('tnngbot/static/pokemonPool.json', 'r') as pokePoolJson:
          pokePool = json.load(pokePoolJson)
        poolNo = random.randrange(0, len(pokePool))
        pokeNo = pokePool[poolNo]
    else:
      pokeNo = pokemon_number
    
    if catch_count is None:
      catch_count = random.randint(0, int(os.environ['pokemonMaxAttempts'])) 
      
    if level is None:
      level = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
   
    if flees is None:
      flees = random.choices([True, False], weights=[1, 20])[0]    
      
    r = requests.get("https://pokeapi.co/api/v2/pokemon/" + str(pokeNo)) 
    pokemon = r.json()
    embed = discord.Embed(title=f"A wild {pokemon['name']} appears!")
    embed.set_thumbnail(url=pokemon['sprites']['front_default'])  
    embed.set_footer(text=f"Lvl: {level}     No: {pokeNo}     Type: {get_type_emoji_str(pokemon['name'])}")  
    channel = discord.utils.get(message.guild.channels, name="tall-grass")
    new_message = await channel.send(embed=embed)
   
    name = pokemon["name"]
    image_url = pokemon["sprites"]["front_default"]
    
    pokemon_doc = db.pokemon.create_pokemon(pokeNo, name, image_url, str(new_message.id), catch_count, level, flees)
    db.game_state.set_last_pokemon_spawn({
      "last_pokemon_spawn_datetime": discord.utils.utcnow(),
      "pokemon": pokemon_doc
    })
  
async def setup(bot: commands.Bot):
  await bot.add_cog(Pokemon(bot))