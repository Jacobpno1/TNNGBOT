import discord
import requests
from discord.ui import View, Button

class EvolveConfirmView(View):
  def __init__(self, base_pokemon, evolve_no, db, interaction: discord.Interaction, user: discord.User | discord.Member):
    super().__init__(timeout=30)
    self.base_pokemon = base_pokemon
    self.evolve_no = evolve_no
    self.db = db
    self.interaction = interaction
    self.confirmed = False
    self.user = user

  @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
  async def confirm(self, interaction: discord.Interaction, button: Button):
    # Prevent other users from clicking
    if interaction.user.id != self.user.id:
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
    
    channel = None
    if interaction.guild is not None:
      channel = discord.utils.get(interaction.guild.channels, name="tall-grass")      
    if channel is not None and isinstance(channel, discord.TextChannel) and interaction.channel is not None and channel.id == interaction.channel.id:
      await interaction.response.edit_message(view=None)
      await channel.send(embed=embed)        
    else:
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
