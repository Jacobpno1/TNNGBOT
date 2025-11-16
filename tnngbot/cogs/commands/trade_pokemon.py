from datetime import datetime
import discord
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands
import os
from typing import Optional
from tnngbot.classes.evolve_view import EvolveConfirmView
from tnngbot.db.manager import MongoDBManager
from tnngbot.schemas.pokemon import PokemonDoc
from tnngbot.utils.evolve import can_pokemon_evolve, get_next_evolution_number

# Database setup
MONGO_DBNAME = os.environ["MONGO_DBNAME"]
MONGO_URI = os.environ["MONGO_URI"]
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)
guild_name = os.environ["guildName"]


# --- Trade confirmation view ---
class TradeConfirmView(View):
  def __init__(self, allowed_user: discord.Member, i_user: discord.User | discord.Member, my_pokemon: PokemonDoc, for_pokemon: PokemonDoc):
    # persistent view: set timeout to None so the view does not expire during the bot's runtime
    super().__init__(timeout=None)
    # persistent view: set timeout to None so the view does not expire during the bot's runtime
    super().__init__(timeout=None)
    self.allowed_user = allowed_user
    self.i_user = i_user
    self.my_pokemon = my_pokemon
    self.for_pokemon = for_pokemon

  def _get_pokemon_for_trade(self, pokemon_doc: PokemonDoc, owner: discord.User | discord.Member) -> Optional[PokemonDoc]:
    pokemon_id = pokemon_doc.get("_id") if pokemon_doc else None
    if pokemon_id is None:
      return None
    latest = db.pokemon.get_pokemon_by_id(pokemon_id)
    if latest is None or latest.get("caught_by") != owner.id or latest.get("caught") is False:
      return None
    return latest

  def _get_pokemon_for_trade(self, pokemon_doc: PokemonDoc, owner: discord.User | discord.Member) -> Optional[PokemonDoc]:
    pokemon_id = pokemon_doc.get("_id") if pokemon_doc else None
    if pokemon_id is None:
      return None
    latest = db.pokemon.get_pokemon_by_id(pokemon_id)
    if latest is None or latest.get("caught_by") != owner.id or latest.get("caught") is False:
      return None
    return latest

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    """Ensure only the target user can interact."""
    if interaction.user.id != self.allowed_user.id:
      await interaction.response.send_message("This trade isn't for you!", ephemeral=True)
      return False
    return True

  async def disable_and_update(self, interaction: discord.Interaction, message: str, color: discord.Color, notify_user: discord.User | discord.Member | None = None):
    """Helper to clear buttons and update the original message."""
    embed = discord.Embed(description=message, color=color)
    if interaction.message is not None:
      await interaction.message.edit(content=None, embeds=[embed], view=None)
    if notify_user is not None:
      await notify_user.send(embed=embed)
    self.stop()

  @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
  async def accept(self, interaction: discord.Interaction, button: Button):
    if not await self.interaction_check(interaction):
      return
    
    if not await self.interaction_check(interaction):
      return
    
    print(f"[TRADE] {interaction.user.display_name} pressed ACCEPT")

    # Confirmation message with trade details
    user1 = self.i_user
    user2 = self.allowed_user    
    
    user1_pokemon = self._get_pokemon_for_trade(self.my_pokemon, user1)
    if not user1_pokemon:
      pokemon_name = self.my_pokemon.get('name', 'that Pokémon') if isinstance(self.my_pokemon, dict) else 'that Pokémon'
      confirmation_msg = f"[TRADE FAILED] **{user1.display_name}** does not own **{pokemon_name}** anymore."
      await self.disable_and_update(interaction, confirmation_msg, discord.Color.red(), notify_user=user1)  
      return
    user2_pokemon = self._get_pokemon_for_trade(self.for_pokemon, user2)
    if not user2_pokemon:
      pokemon_name = self.for_pokemon.get('name', 'that Pokémon') if isinstance(self.for_pokemon, dict) else 'that Pokémon'
      confirmation_msg = f"[TRADE FAILED] **{user2.display_name}** does not own **{pokemon_name}** anymore."
      await self.disable_and_update(interaction, confirmation_msg, discord.Color.red(), notify_user=user1)   
      return 

    self.my_pokemon = user1_pokemon
    self.for_pokemon = user2_pokemon

    self.my_pokemon = user1_pokemon
    self.for_pokemon = user2_pokemon
    
    #Update Pokemon 1
    prev1 = user1_pokemon.get("previous_owners", [])
    if str(user1.id) not in prev1:
      prev1.append(str(user1.id))
    user1_pokemon['caught_by'] = user2.id
    user1_pokemon['traded_at'] = datetime.now().isoformat()
    user1_pokemon['previous_owners'] = prev1     
    result = db.pokemon.update_pokemon(user1_pokemon)
    
    if result is False:      
      confirmation_msg = f"[TRADE FAILED] Something went wrong with the trade between **{user1.display_name}** and **{user2.display_name}**."
      await self.disable_and_update(interaction, confirmation_msg, discord.Color.red(), notify_user=user1)  
    
    #Update Pokemon 2
    prev2 = user2_pokemon.get("previous_owners", [])
    if str(user2.id) not in prev2:
      prev2.append(str(user2.id))
    user2_pokemon['caught_by'] = user1.id
    user2_pokemon['traded_at'] = datetime.now().isoformat()
    user2_pokemon['previous_owners'] = prev2     
    result = db.pokemon.update_pokemon(user2_pokemon)
    
    if result is False:      
      confirmation_msg = f"[TRADE FAILED] Something went wrong with the trade between **{user1.display_name}** and **{user2.display_name}**."
      await self.disable_and_update(interaction, confirmation_msg, discord.Color.red(), notify_user=user1) 
    guild = discord.utils.get(interaction.client.guilds, name=guild_name)    
    # result = db.pokemon.trade_pokemon(user1, user2, user1_pokemon, user2_pokemon)      
    pokeball_emoji = "<:pokeball:1419845300742520964>"
    if guild is not None:
      pokeball_emoji = str(discord.utils.get(guild.emojis, name="pokeball") or "<:pokeball:1419845300742520964>")
    confirmation_msg = (
    f"✅ **Trade completed!**\n"
    f"**{self.i_user.display_name}** traded {pokeball_emoji} **{self.my_pokemon['name'].capitalize()} (Lvl: {self.my_pokemon.get('level', 1)})** "
    f"for **{self.allowed_user.display_name}'s** {pokeball_emoji} **{self.for_pokemon['name'].capitalize()} (Lvl: {self.for_pokemon.get('level', 1)})**."
    )
    # send confirmation to the "tall-grass" channel in the guild named "Jacobpno1"
    embed = discord.Embed(description=confirmation_msg, color=discord.Color.green())
    if guild is not None:
      channel = discord.utils.get(guild.channels, name="tall-grass")
      if channel is not None and isinstance(channel, discord.TextChannel):
        await channel.send(embed=embed)
    
    await self.disable_and_update(interaction, confirmation_msg, discord.Color.green(), notify_user=user1)
    # --- Evolution Check ---
    evolve_no = get_next_evolution_number(
    pokemon_name=user1_pokemon["name"],
    allow_trade=True
    )
    
    if evolve_no > 0:
      evolve_embed = discord.Embed(
        title=f"{user1_pokemon['name'].capitalize()} is starting to evolve!",
        color=discord.Color.orange()
      )
      evolve_embed.set_thumbnail(url=user1_pokemon["image_url"])
      
      view = EvolveConfirmView(user1_pokemon, evolve_no, db, interaction, user2)
      await user2.send(embed=evolve_embed, view=view)
      
    evolve_no = get_next_evolution_number(
    pokemon_name=user2_pokemon["name"],
    allow_trade=True
    )
    
    if evolve_no > 0:
      evolve_embed = discord.Embed(
        title=f"{user2_pokemon['name'].capitalize()} is starting to evolve!",
        color=discord.Color.orange()
      )
      evolve_embed.set_thumbnail(url=user2_pokemon["image_url"])

      view = EvolveConfirmView(user2_pokemon, evolve_no, db, interaction, user1)        
      await user1.send(embed=evolve_embed, view=view)        
      
    self.stop()           

  @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
  async def reject(self, interaction: discord.Interaction, button: Button):
    print(f"[TRADE] **{interaction.user.display_name}** pressed REJECT")
    self.my_pokemon
    await self.disable_and_update(
      interaction,
      f"❌ Trade Rejected: **{self.i_user.display_name}'s {self.my_pokemon['name'].capitalize()} (Lvl: {self.my_pokemon.get('level', 1)})** for **{self.allowed_user.display_name}'s {self.for_pokemon['name'].capitalize()} (Lvl: {self.for_pokemon.get('level', 1)})**.",
      discord.Color.red(),
      notify_user=self.i_user
    )


# --- Cog setup ---
class TradePokemon(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(name="trade", description="Trade a Pokémon with another user")
  @app_commands.describe(
    user="User to trade with.",
    my_pokemon_number="Your Pokémon number (1-151)",
    my_pokemon_level="Your Pokémon level",
    for_pokemon_number="Their Pokémon number (1-151)",
    for_pokemon_level="Their Pokémon level",
  )
  async def trade_pokemon(
    self,
    interaction: discord.Interaction,
    user: discord.Member,
    my_pokemon_number: int,
    my_pokemon_level: int,
    for_pokemon_number: int,    
    for_pokemon_level: int
  ):
    i_user = interaction.user
    my_pokemon = db.pokemon.get_pokemon_lvl(i_user, int(my_pokemon_number), my_pokemon_level)
    for_pokemon = db.pokemon.get_pokemon_lvl(user, int(for_pokemon_number), for_pokemon_level)

    if not my_pokemon:
      await interaction.response.send_message(
        f"❗ You do not own a Pokémon with number {my_pokemon_number}.",
        ephemeral=True,
      )
      return
    if not for_pokemon:
      await interaction.response.send_message(
        f"❗ {user.display_name} does not own a Pokémon with number {for_pokemon_number}.",
        ephemeral=True,
      )
      return

    # Build embeds showing both Pokémon
    # Resolve pokeball emoji by name (fallback to the original literal if not found)
    pokeball_emoji = str(discord.utils.get(self.bot.emojis, name="pokeball") or "<:pokeball:1419845300742520964>")
    my_pokemon_embed = discord.Embed(      
      title=f"{i_user.display_name} offers: {pokeball_emoji} {my_pokemon['name'].capitalize()} [#{my_pokemon['number']}]"
    )
    if 'level' in my_pokemon:
      my_pokemon_embed.set_footer(text=f"Lvl: {my_pokemon['level']}")  
    my_pokemon_embed.set_thumbnail(url=my_pokemon["image_url"])

    for_pokemon_embed = discord.Embed(      
      title=f"For {user.display_name}'s: {pokeball_emoji} {for_pokemon['name'].capitalize()} [#{for_pokemon['number']}]"
    )
    if 'level' in for_pokemon:
      for_pokemon_embed.set_footer(text=f"Lvl: {for_pokemon['level']}")  
    for_pokemon_embed.set_thumbnail(url=for_pokemon["image_url"])

    # Create confirmation view (buttons visible only to target user)    
    view = TradeConfirmView(
      allowed_user=user,
      i_user=i_user,
      my_pokemon=my_pokemon,
      for_pokemon=for_pokemon,
    )

    # Send trade offer
    await user.send(
      f"**{i_user.display_name} wants to trade Pokémon!**",
      embeds=[my_pokemon_embed, for_pokemon_embed],
      view=view
    )
    interaction_msg = (
      f"Trade offer sent to {user.display_name} to trade "
      f"{pokeball_emoji} **{my_pokemon['name'].capitalize()} (lvl: {my_pokemon.get('level', 1)})** "
      f"for their {pokeball_emoji} **{for_pokemon['name'].capitalize()} (lvl: {for_pokemon.get('level', 1)})**."
    )
    await interaction.response.send_message(interaction_msg, ephemeral=True)

async def setup(bot: commands.Bot):
  await bot.add_cog(TradePokemon(bot))
