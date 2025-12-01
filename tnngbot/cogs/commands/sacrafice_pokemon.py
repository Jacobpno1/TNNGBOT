import discord
from discord import app_commands
from discord.ui import View, Button
import requests
import discord
from discord import app_commands 
from discord.ext import commands
import requests
from tnngbot.db.manager import MongoDBManager
from tnngbot.utils.type import get_type_list
from utils.evolve import can_pokemon_evolve, get_next_evolution_number
from classes.evolve_view import EvolveConfirmView
import os

# Database setup
MONGO_DBNAME = os.environ['MONGO_DBNAME']
MONGO_URI = os.environ['MONGO_URI']
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)

class PokemonFusion(commands.Cog):
  def __init__(self, bot):
    self.bot = bot    

  @app_commands.command(name="sacrafice", description="Sacrafice a pokemon to the altar! (The Pokemon will be lost.)")
  @app_commands.describe(
    pokemon_number="Pokemon number (1-151)",
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
  async def fuse_pokemon(
    self,
    interaction: discord.Interaction,
    pokemon_number: int,
    pokemon_level: int,
    type: str | None = None
  ):    
    # await interaction.response.defer(ephemeral=True)       
    pokemon = db.pokemon.get_pokemon_lvl(interaction.user, pokemon_number, pokemon_level)
    
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
    types = get_type_list(pokemon["name"])
    if type:
      if type.lower() not in [t.lower() for t in types]:
        await interaction.response.send_message(
          f"❗ The specified type '{type}' is not valid for {pokemon['name'].capitalize()}. Valid types: {', '.join(types)}.",
          ephemeral=True
        )
        return
    else:
      type = types[0]  # default to first type if none specified
    
    altar_update_result = db.game_state.altar_sacrifice(type.lower())       
    
    if altar_update_result["status"] == "error":
      await interaction.followup.send(f"Error: {altar_update_result.get('error', 'Unknown error.')}", ephemeral=True)
      return
    elif altar_update_result["status"] == "max_buffs_reached":
      await interaction.followup.send("The altar has already reached the maximum number of buffs (10). You cannot sacrafice more pokemon at this time.", ephemeral=True)
      return
    elif altar_update_result["status"] == "version_mismatch":
      await interaction.followup.send("There was a version mismatch while updating the altar. Please try again.", ephemeral=True)
      return
    
    await interaction.followup.send(f"You have successfully sacraficed a level {pokemon_level} Pokemon #{pokemon_number} to the altar for type '{type}'.", ephemeral=True)