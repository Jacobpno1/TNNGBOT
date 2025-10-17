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

  # @app_commands.command(name="battle", description="Challenge another trainer to a battle with your Pokemon.")
  # @app_commands.describe(user="User to challenge.", number_of_pokemon="Number of Pokemon to battle with(1-3)")
  # async def trade_pokemon(self, interaction: discord.Interaction, user: discord.Member, number_of_pokemon: int):  
  #   # Create a thread to battle in
  #   if number_of_pokemon < 1 or number_of_pokemon > 3:
  #     await interaction.response.send_message(f"❗ You can only battle with 1 to 3 Pokemon.", ephemeral=True) 
  #     return
  #   i_user = interaction.user
  #   battle = await mongoDBAPI.createBattle(thread.id, i_user, user, number_of_pokemon)
  #   thread = await interaction.channel.create_thread(name=f"Battle: {i_user.display_name} vs {user.display_name}", type=discord.ChannelType.public_thread)
  #   await thread.send(f"{i_user.mention} has challenged {user.mention} to a Pokemon battle! The winner takes all!")
  #   await interaction.response.send_message(f"✅ Battle thread created: {thread.mention}", ephemeral=True)
    
  