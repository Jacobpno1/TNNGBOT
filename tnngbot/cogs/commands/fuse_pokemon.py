import discord
from discord import app_commands
from discord.ui import View, Button
import requests
import discord
from discord import app_commands 
from discord.ext import commands
import requests
from tnngbot.db.manager import MongoDBManager
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

  @app_commands.command(name="fuse", description="Fuse two of the same Pokemon to create a stronger version! (The fused Pokemon will be lost)")
  @app_commands.describe(
    pokemon_number="Base pokemon number (1-251)",
    base_pokemon_level="Base pokemon level",
    # fused_pokemon_number="Fused pokemon number (1-251)",
    fused_pokemon_level="Fused pokemon level"
  )
  async def fuse_pokemon(
    self,
    interaction: discord.Interaction,
    pokemon_number: int,
    base_pokemon_level: int,
    # fused_pokemon_number: int,
    fused_pokemon_level: int
  ):    

    base_pokemon = db.pokemon.get_pokemon_lvl(interaction.user, pokemon_number, base_pokemon_level)
    
    if not base_pokemon:
      await interaction.response.send_message(
        f"❗ You do not own a pokemon with number {pokemon_number} at level {base_pokemon_level}.",
        ephemeral=True
      )
      return
    if base_pokemon is None or "_id" not in base_pokemon or base_pokemon["_id"] is None:
      await interaction.response.send_message(
        f"❗ There was an error returning the base pokemon.",
        ephemeral=True
      )
      return
    base_id = base_pokemon["_id"]
    fused_pokemon = db.pokemon.get_pokemon_lvl(interaction.user, pokemon_number, fused_pokemon_level, exclude_id=base_id)
    if not fused_pokemon:
      await interaction.response.send_message(
        f"❗ You do not own a pokemon with number {pokemon_number} at level {fused_pokemon_level}.",
        ephemeral=True
      )
      return
    if base_pokemon["number"] != fused_pokemon["number"]:
      await interaction.response.send_message(
        f"❗ You can only fuse two of the same Pokémon.",
        ephemeral=True
      )
      return
    if base_pokemon.get("level", 1) != base_pokemon_level or fused_pokemon.get("level", 1) != fused_pokemon_level:
      await interaction.response.send_message(
        f"❗ One of the Pokémon levels provided does not match the stored level.",
        ephemeral=True
      )
      return
    old_base_level = base_pokemon.get("level", 1)
    base_pokemon["level"] = old_base_level
    fused_pokemon["level"] = fused_pokemon.get("level", 1)
    base_pokemon["level"] += fused_pokemon["level"]

    db.pokemon.update_pokemon(base_pokemon)
    db.pokemon.delete_pokemon(fused_pokemon)

    embed = discord.Embed(
      title=f"{interaction.user.display_name} fused {base_pokemon['name'].capitalize()}!",
      color=discord.Color.blue()
    )
    embed.set_thumbnail(url=base_pokemon["image_url"])
    embed.add_field(
      name=f"{base_pokemon['name'].capitalize()} grew to level {base_pokemon['level']}",
      value="",
      inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- Evolution Check ---
    if can_pokemon_evolve(old_base_level, base_pokemon["level"]):
      evolve_no = get_next_evolution_number(
        pokemon_name=base_pokemon["name"],
        allow_trade=False
      )
      if evolve_no > 0:
        evolve_embed = discord.Embed(
          title=f"{base_pokemon['name'].capitalize()} is starting to evolve!",
          color=discord.Color.orange()
        )
        evolve_embed.set_thumbnail(url=base_pokemon["image_url"])

        view = EvolveConfirmView(base_pokemon, evolve_no, db, interaction, interaction.user)
        await interaction.followup.send(embed=evolve_embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
  await bot.add_cog(PokemonFusion(bot))