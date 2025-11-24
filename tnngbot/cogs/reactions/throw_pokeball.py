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

from tnngbot.schemas.pokemon import PokemonDoc

# Database setup
MONGO_DBNAME = os.environ['MONGO_DBNAME']
MONGO_URI = os.environ['MONGO_URI']
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)

class ThrowPokeball(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot  
    
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
    user = await client.fetch_user(payload.user_id)
    
    if (payload.emoji.name == "pokeball"):  
      await self.throw_pokeball(payload, user) 
    
    if (payload.emoji.name == "greatball"):  
      await self.throw_pokeball(payload, user, ball_type="greatball") 
      
    if (payload.emoji.name == "ultraball"):  
      await self.throw_pokeball(payload, user, ball_type="ultraball")

  async def build_embed_from_pokemon(self, pokemon_doc: PokemonDoc) -> discord.Embed:
    """
    Build a brand-new embed representing the current state of the pokemon doc.
    This prevents embedding race conditions where multiple edits mutate the same in-memory embed.
    """
    # embed = discord.Embed(title=pokemon_doc.get("name", "Unknown").capitalize())
    # embed.set_thumbnail(url=pokemon_doc.get("image_url", ""))
    embed = discord.Embed(title=f"A wild {pokemon_doc['name']} appears! [{pokemon_doc['number']}]")
    embed.set_thumbnail(url=pokemon_doc.get("image_url", ""))  
    embed.set_footer(text=f"Lvl: {pokemon_doc.get('level', 1)}")
    # add fields that you previously used: e.g. attempts, footer as pokeNo, status etc.    
    for attempt_user_id in list(pokemon_doc.get("catch_attempts", [])):
      user = self.bot.get_user(int(attempt_user_id))
      if user:
        embed.add_field(name=f"Oh no {user.display_name}! {pokemon_doc['name'].capitalize()} broke free!", value="", inline=False)
    # if pokemon_doc.get("caught", False):
    #   caught_by = pokemon_doc.get("caught_by", "Someone")
    #   embed.set_footer(text=f"#{pokemon_doc.get('poke_no','?')} - caught by {caught_by}")
    # else:
    
    # Add additional fields as you need
    return embed

  async def throw_pokeball(self, payload, user: discord.User, ball_type="pokeball"):
    client = self.bot
    if not client.user:
      return
    if payload.user_id == client.user.id:
      return
    if payload.guild_id is None:
      return
    guild = client.get_guild(payload.guild_id)
    if guild is None:
      return
    channel = guild.get_channel(payload.channel_id)
    if not isinstance(channel, discord.TextChannel):
      return
    emoji = discord.utils.get(guild.emojis, name=ball_type) or getattr(payload, "emoji", None)

    now = datetime.now()
    local_tz = pytz.timezone("US/Eastern")
    now.astimezone(local_tz)
    if ball_type != "pokeball":
      user_doc = db.users.get_user(user.id)
      ball_cooldowns = user_doc["ball_cooldowns"]      
      cooldown_time:datetime|None = ball_cooldowns.get(ball_type, None)
      if cooldown_time is not None and now < cooldown_time:
        #private message user that they are still in cooldown        
        await user.send(f"You have recently used a {str(emoji)} {ball_type}. You can use it again on {cooldown_time.strftime('%m/%d/%y %I:%M %p')} ET.")          
        return  # Still in cooldown

    ball_bonus = 0
    if ball_type in ("greatball", "ultraball"):
      ball_bonus = int(os.environ.get(f"{ball_type}Bonus", "0"))

    # fetch the message and the pokemon
    try:
      message = await channel.fetch_message(payload.message_id)
    except Exception as e:
      # message may be deleted or fetch failed
      print(f"Failed to fetch message {payload.message_id}: {e}")
      return

    # quick validation: ensure it's a pokemon message by checking footer/pokeNo
    if not message.embeds:
      return

    # Attempt the DB operation (try_catch). The DB function handles retries.
    result = db.pokemon.try_catch(str(message.id), user.id, ball_bonus)

    status = result.get("status")
    fresh_pokemon = result.get("pokemon")
    if fresh_pokemon is None:
      print(f"Failed to fetch fresh pokemon after try_catch for message {message.id}")
      return

    # React depending on status
    try:
      if status == "caught":
        # Build a fresh embed from DB and add Gotcha field
        embed = await self.build_embed_from_pokemon(fresh_pokemon)
        embed.add_field(
          name=f"{str(emoji)} Gotcha! {fresh_pokemon['name'].capitalize()} was caught by {user.display_name}!",
          value="Use /pokedex to see all the Pokemon you've caught and /pokemon to summon them!",
          inline=False,
        )
        await message.edit(embed=embed)

        # Update player's cooldown only after a successful non-pokeball catch
        if ball_type != "pokeball":
          expiry = now + timedelta(seconds=int(os.environ.get(f"{ball_type}CooldownSeconds", "0")))
          db.users.set_ball_cooldown(user.id, ball_type, expiry)

      elif status == "attempted":
        embed = await self.build_embed_from_pokemon(fresh_pokemon)
        await message.edit(embed=embed)

        if ball_type != "pokeball":
          expiry = now + timedelta(seconds=int(os.environ.get(f"{ball_type}CooldownSeconds", "0")))
          db.users.set_ball_cooldown(user.id, ball_type, expiry)
      
      elif status == "fled":
        embed = await self.build_embed_from_pokemon(fresh_pokemon)
        embed.set_thumbnail(url=None)
        embed.add_field(name=f"Oh no {user.display_name}! {fresh_pokemon['name'].capitalize()} fled before it could be caught!", value="", inline=False)  
        await message.edit(embed=embed)    

      else:
        # unexpected error
        print("Unexpected try_catch status:", status, result.get("error"))
    except Exception as e:
      print(f"Error processing pokeball outcome: {e}")

async def setup(bot: commands.Bot):
  await bot.add_cog(ThrowPokeball(bot))