from collections import Counter
from datetime import datetime, timedelta
import os
from typing import Union
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
    if random.randrange(1, int(os.environ['pokemonSpawnRate'])) == 1:
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
    
    if (payload.emoji.name == "greatball"):  
      await self.throw_pokeball(payload, user, ball_type="greatball") 
      
    if (payload.emoji.name == "ultraball"):  
      await self.throw_pokeball(payload, user, ball_type="ultraball") 

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
      embed.set_footer(text=f"Lvl: {level}")  
      await interaction.response.send_message(embed=embed)
    else:
      await interaction.response.send_message("You haven't caught that pokemon.", ephemeral=True) 

  @app_commands.command(name="spawn_pokemon", description="[Admin Only] Spawn a pokemon by number")
  @app_commands.describe(pokemon_number="The number of the Pokemon you want to spawn (1-151)", catch_count="How many attempts before catching", level="Pokemon level")
  async def spawn_pokemon(self, interaction: discord.Interaction, pokemon_number: str, catch_count:int = 0, level:int = 1):  
    if not isinstance(interaction.user, discord.Member):
      await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
      return
    if interaction.user is not None and interaction.user.guild_permissions.administrator:
      await self.spawnPokemon(interaction, int(pokemon_number), catch_count=int(catch_count), level=level)
      await interaction.response.send_message(f"Spawned pokemon number {pokemon_number}!", ephemeral=True) 
    else:
      await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)        
  
  async def throw_pokeball(self, payload, user: discord.User, ball_type="pokeball"):
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
    emoji = discord.utils.get(guild.emojis, name=ball_type)
    if emoji is None:
      emoji = payload.emoji 
    
    user_doc = None
    ball_cooldowns = None
    now = datetime.now()
    local_tz = pytz.timezone("US/Eastern")
    now.astimezone(local_tz)
    if ball_type != "pokeball":
      user_doc = db.users.get_user(user.id)
      ball_cooldowns = user_doc["ball_cooldowns"]      
      cooldown_time:datetime|None = ball_cooldowns.get(ball_type, None)
      if cooldown_time is not None and now < cooldown_time:
        #private message user that they are still in cooldown
        cooldown_time = cooldown_time + timedelta(seconds=int(os.environ[f'{ball_type}CooldownSeconds']))
        await user.send(f"You have recently used a {str(emoji)}{ball_type}. You can use it again on {cooldown_time.strftime('%m/%d/%y %I:%M %p')} ET.")          
        return  # Still in cooldown
                
    ball_bonus = 0
    match ball_type:
      case "greatball": ball_bonus = int(os.environ[f'{ball_type}Bonus'])
      case "ultraball": ball_bonus = int(os.environ[f'{ball_type}Bonus'])
    
    message = await channel.fetch_message(payload.message_id)   
    if (len(message.embeds) != 0 and message.embeds[0] is not None and message.embeds[0].footer.text is not None):
      # pokeNo = int(message.embeds[0].footer.text)
      try:
        pokemon = db.pokemon.get_pokemon_by_message_id(str(message.id))      
        if pokemon is None:
          print("No pokemon found for message ID " + str(message.id))
          return    
        hasUserAttempted = str(user.id) in pokemon["catch_attempts"]
        catchable = len(pokemon["catch_attempts"]) + ball_bonus >= pokemon["catch_count"]
        
        
        if hasUserAttempted is False and pokemon["caught"] is False:
          if catchable is True:
          # Catch the Pokemon      
            success = db.pokemon.catch_pokemon(str(message.id), pokemon, user)            
            if success is True:                           
              message.embeds[0].add_field(name=f"{str(emoji)} Gotcha! {pokemon['name'].capitalize()} was caught by {user.display_name}!", 
              value="Use /pokedex to see all the Pokemon you've caught and /pokemon to summon them!", inline=False)  
              await message.edit(embed=message.embeds[0]) 
            else :
              await self.throw_pokeball(payload, user); 
            # Update the cooldown
            if ball_type != "pokeball" and user_doc is not None and ball_cooldowns is not None:                
              ball_cooldowns[ball_type] = now + timedelta(seconds=int(os.environ[f'{ball_type}CooldownSeconds']))
              user_doc["ball_cooldowns"] = ball_cooldowns
              db.users.upsert_user(user_doc)     
          else:
            # Track the failed attempt
            # success = await mongoDBAPI.addCatchAttempt("Pokemon", "TNNGBOT", "JacobTEST", str(message.id), user, pokemon)
            success = db.pokemon.add_catch_attempt(str(message.id), user, pokemon, ball_bonus+1)
            if success is True:
              message.embeds[0].add_field(name=f"Oh no {user.display_name}! {pokemon['name'].capitalize()} broke free!", value="", inline=False)
              await message.edit(embed=message.embeds[0])
            else:
              await self.throw_pokeball(payload, user); 
      except Exception as e:
        print(f"Error processing pokeball throw: {e}")  

  async def spawnPokemon(self, message, pokemon_number=None, catch_count=None, level=None):
    if pokemon_number is None:
      pokePool: list[int] = []
      with open('tnngbot/static/pokemonPool.json', 'r') as pokePoolJson:
        pokePool = json.load(pokePoolJson)
      poolNo = random.randrange(0, len(pokePool))
      pokeNo = pokePool[poolNo]
    else:
      pokeNo = pokemon_number
    if level is None:
      level = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
    r = requests.get("https://pokeapi.co/api/v2/pokemon/" + str(pokeNo)) 
    pokemon = r.json()
    embed = discord.Embed(title=f"A wild {pokemon['name']} appears! [{pokeNo}]")
    embed.set_thumbnail(url=pokemon['sprites']['front_default'])  
    embed.set_footer(text=f"Lvl: {level}")
    channel = discord.utils.get(message.guild.channels, name="tall-grass")
    new_message = await channel.send(embed=embed)
    catch_count = catch_count if catch_count is not None else random.randint(0, int(os.environ['pokemonMaxAttempts']))
    name = pokemon["name"]
    image_url = pokemon["sprites"]["front_default"]
    db.pokemon.create_pokemon(pokeNo, name, image_url, str(new_message.id), catch_count, level)
  
async def setup(bot: commands.Bot):
  await bot.add_cog(Pokemon(bot))