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
import os

# Database setup
MONGO_DBNAME = os.environ['MONGO_DBNAME']
MONGO_URI = os.environ['MONGO_URI']
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)

class EvolveConfirmView(View):
  def __init__(self, base_pokemon, evolve_no, db, interaction):
    super().__init__(timeout=30)
    self.base_pokemon = base_pokemon
    self.evolve_no = evolve_no
    self.db = db
    self.interaction = interaction
    self.confirmed = False

  @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
  async def confirm(self, interaction: discord.Interaction, button: Button):
    # Prevent other users from clicking
    if interaction.user.id != self.interaction.user.id:
      await interaction.response.send_message("This isn't your evolution!", ephemeral=True)
      return

    # Get new Pokémon info from PokeAPI
    evo_data = requests.get(f"https://pokeapi.co/api/v2/pokemon/{self.evolve_no}").json()
    new_name = evo_data["name"].capitalize()
    embed_image = evo_data["sprites"]["other"]["official-artwork"]["front_default"]
    new_image = evo_data["sprites"]["front_default"]

    # Update the Pokémon in the database
    old_name = self.base_pokemon["name"]
    self.base_pokemon["name"] = new_name
    self.base_pokemon["number"] = self.evolve_no
    self.base_pokemon["image_url"] = new_image
    self.db.pokemon.update_pokemon(self.base_pokemon)

    # Update the embed
    embed = discord.Embed(
      title=f"✨ {self.interaction.user.display_name}'s Pokémon evolved!",
      description=f"**{old_name.capitalize()} evolved into {new_name}!**",
      color=discord.Color.gold()
    )
    embed.set_image(url=embed_image)

    await interaction.response.edit_message(embed=embed, view=None)
    self.confirmed = True
    self.stop()

  @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
  async def cancel(self, interaction: discord.Interaction, button: Button):
    if interaction.user.id != self.interaction.user.id:
      await interaction.response.send_message("This isn't your evolution!", ephemeral=True)
      return
    embed = discord.Embed(
      title=f"{self.base_pokemon['name'].capitalize()} stopped evolving.",
      color=discord.Color.dark_grey()
    )
    embed.set_thumbnail(url=self.base_pokemon["image_url"])
    await interaction.response.edit_message(embed=embed, view=None)
    self.stop()


class PokemonFusion(commands.Cog):
  def __init__(self, bot):
    self.bot = bot    

  @app_commands.command(name="fuse", description="Fuse two of the same Pokemon to create a stronger version! (The fused Pokemon will be lost)")
  @app_commands.describe(
    base_pokemon_number="Base pokemon number (1-151)",
    base_pokemon_level="Base pokemon level",
    fused_pokemon_number="Fused pokemon number (1-151)",
    fused_pokemon_level="Fused pokemon level"
  )
  async def fuse_pokemon(
    self,
    interaction: discord.Interaction,
    base_pokemon_number: int,
    base_pokemon_level: int,
    fused_pokemon_number: int,
    fused_pokemon_level: int
  ):    

    base_pokemon = db.pokemon.get_pokemon_lvl(interaction.user, base_pokemon_number, base_pokemon_level)
    if base_pokemon is None or "_id" not in base_pokemon or base_pokemon["_id"] is None:
      await interaction.response.send_message(
        f"❗ There was an error returning the base pokemon.",
        ephemeral=True
      )
      return
    base_id = base_pokemon["_id"]
    fused_pokemon = db.pokemon.get_pokemon_lvl(interaction.user, fused_pokemon_number, fused_pokemon_level, exclude_id=base_id)
    if not base_pokemon:
      await interaction.response.send_message(
        f"❗ You do not own a pokemon with number {base_pokemon_number} at level {base_pokemon_level}.",
        ephemeral=True
      )
      return
    if not fused_pokemon:
      await interaction.response.send_message(
        f"❗ You do not own a pokemon with number {fused_pokemon_number} at level {fused_pokemon_level}.",
        ephemeral=True
      )
      return
    if base_pokemon["number"] != fused_pokemon["number"]:
      await interaction.response.send_message(
        f"❗ You can only fuse two of the same Pokémon.",
        ephemeral=True
      )
      return

    base_pokemon["level"] = base_pokemon.get("level", 1)
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
    if can_pokemon_evolve(base_pokemon["level"]):
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

        view = EvolveConfirmView(base_pokemon, evolve_no, db, interaction)
        await interaction.followup.send(embed=evolve_embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
  await bot.add_cog(PokemonFusion(bot))