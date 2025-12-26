import discord
from discord import app_commands
from discord.ui import View, Button
import requests
import discord
from discord import app_commands 
from discord.ext import commands
import requests
from tnngbot.db.manager import MongoDBManager
from tnngbot.utils.type import get_emoji_for_types, get_type_emoji_str, get_type_list
from utils.evolve import can_pokemon_evolve, get_next_evolution_number
from classes.evolve_view import EvolveConfirmView
import os
from datetime import timezone
from zoneinfo import ZoneInfo
import pytz as _pytz
import logging

# Database setup
MONGO_DBNAME = os.environ['MONGO_DBNAME']
MONGO_URI = os.environ['MONGO_URI']
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)

class SacrificePokemon(commands.Cog):
  def __init__(self, bot):
    self.bot = bot    

  @app_commands.command(name="sacrifice", description="Sacrifice a pokemon on the altar! (The Pokemon will be lost.)")
  @app_commands.describe(
    pokemon_number="Pokemon number (1-251)",
    pokemon_level="Pokemon level",    
    type="Specify the type if the pokemon has multiple types. (If not specified, the first type will be used.)"
  )
  @app_commands.choices(
    type=[
      app_commands.Choice(name="Normal", value="normal"),
      app_commands.Choice(name="Fire", value="fire"),
      app_commands.Choice(name="Water", value="water"),
      app_commands.Choice(name="Electric", value="electric"),
      app_commands.Choice(name="Grass", value="grass"),
      app_commands.Choice(name="Ice", value="ice"),
      app_commands.Choice(name="Fighting", value="fighting"),
      app_commands.Choice(name="Poison", value="poison"),
      app_commands.Choice(name="Ground", value="ground"),
      app_commands.Choice(name="Flying", value="flying"),
      app_commands.Choice(name="Psychic", value="psychic"),
      app_commands.Choice(name="Bug", value="bug"),
      app_commands.Choice(name="Rock", value="rock"),
      app_commands.Choice(name="Ghost", value="ghost"),
      app_commands.Choice(name="Dragon", value="dragon"),      
    ]
  )
  async def sacrifice_pokemon(
    self,
    interaction: discord.Interaction,
    pokemon_number: int,
    pokemon_level: int,
    type: str | None = None
  ):   
    try: 
    
      pokemon = db.pokemon.get_pokemon_lvl(interaction.user, pokemon_number, pokemon_level)
      
      pokeball_emoji = str(discord.utils.get(interaction.guild.emojis, name="pokeball") or "<:pokeball:1419845300742520964>") if interaction.guild is not None else "<:pokeball:1419845300742520964>"
      
      # validate pokemon ownership
      if not pokemon:
        await interaction.response.send_message(
          f"❗ You do not own a pokemon with number {pokemon_number} at level {pokemon_level}.",
          ephemeral=True
        )
        return
      if pokemon is None or "_id" not in pokemon or pokemon["_id"] is None:
        await interaction.response.send_message(
          f"❗ There was an error returning the base pokemon.",
          ephemeral=True
        )
        return
      
      # check pokemon type(s)
      types = get_type_list(pokemon["name"].lower())
      if type:
        if type.lower() not in [t.lower() for t in types]:
          await interaction.response.send_message(
            f"❗ The specified type '{type}' is not valid for {pokemon['name'].capitalize()}. Valid types: {', '.join(types)}.",
            ephemeral=True
          )
          return
      else:
        type = types[0]  # default to first type if none specified
      previous_altar_state = db.game_state.get_altar_state()
      altar_update_result = db.game_state.altar_sacrifice(type.lower(), pokemon.get("level", 1)) 
      
      if altar_update_result["status"] == "error":
        await interaction.response.send_message(f"Error: {altar_update_result.get('error', 'Unknown error.')}", ephemeral=True)
        return
      elif altar_update_result["status"] == "max_buffs_reached":
        await interaction.response.send_message("You cannot sacrifice more pokemon at this time.", ephemeral=True)
        return
      elif altar_update_result["status"] == "version_mismatch":
        await interaction.response.send_message("There was a version mismatch while updating the altar. Please try again.", ephemeral=True)
        return  
      pokemon_altar = altar_update_result.get("pokemon_altar", None)   
      
      if not pokemon_altar:
        await interaction.response.send_message(
          f"❗ There was an error retrieving the updated altar state.",
          ephemeral=True
        )
        return 
                  
      embed = discord.Embed(        
        title=f"{interaction.user.display_name} sacrificed {pokeball_emoji} {pokemon['name'].capitalize()} (Lvl: {pokemon.get('level', 1)}) on the altar!",
        color=discord.Color.onyx_embed()
      )
      embed.set_thumbnail(url="https://i.ibb.co/VW9W9sNZ/Altar.png")
      type_buffs = pokemon_altar.get("type_buffs", [])
      type_emoji_str = get_emoji_for_types(type_buffs)
    
      ZoneInfo = lambda tz: _pytz.timezone(tz)
      previous_active_until = previous_altar_state["active_until"] if previous_altar_state and "active_until" in previous_altar_state else None
      if previous_active_until and previous_active_until.tzinfo is None:
        previous_active_until = previous_active_until.replace(tzinfo=timezone.utc)
      active_until = pokemon_altar["active_until"]
      if active_until.tzinfo is None:
        active_until = active_until.replace(tzinfo=timezone.utc)
      eastern = ZoneInfo("America/New_York")
      active_until_est = active_until.astimezone(eastern)    
      if not previous_altar_state or (previous_active_until and previous_active_until <= discord.utils.utcnow()):
        embed.add_field(
          name=f"The tall grass begins to rustle ominously...",     
          value="",
          inline=False
        )
      alter_descripion = f"The altar is softly glowing with energy"
      if len(type_buffs) >= 5:
        alter_descripion = f"The altar is radiating with energy!"
      if len(type_buffs) >= 10:
        alter_descripion = f"The altar is pulsing with overwhelming energy!"
      embed.add_field(
        name=alter_descripion,
        value="",
        inline=False
      )
      embed.add_field(
        name=f"{type_emoji_str}",
        value="Effect expires at " + active_until_est.strftime("%m/%d/%y %I:%M %p") + " ET",
        inline=False
      )
                          
      await interaction.response.send_message(
        f"✅ Your sacrifice was accepted!",
        ephemeral=True
      )
      
      guild = discord.utils.get(interaction.client.guilds, name=os.environ["guildName"]) 
      channel = None
      if interaction.guild is not None:
        channel = discord.utils.get(interaction.guild.channels, name="tall-grass") 
      elif guild is not None:
        channel = discord.utils.get(guild.channels, name="tall-grass")    
      if channel is not None and isinstance(channel, discord.TextChannel):    
        await channel.send(embed=embed)   
            
      # Finally, delete the sacrificed pokemon
      db.pokemon.delete_pokemon(pokemon) 
    except Exception as e:
      logging.exception("Unexpected error while trying to sacrifice the pokemon: %s", e)
      await interaction.response.send_message(
        "❗ An unexpected error occurred while trying to sacrifice the pokemon.",
        ephemeral=True
      )
      return
    
async def setup(bot: commands.Bot):
  await bot.add_cog(SacrificePokemon(bot))