import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
# from keep_alive import keep_alive
from db.manager import MongoDBManager

load_dotenv()

intents = discord.Intents.default()
client = commands.Bot(command_prefix="!", intents=intents)

@client.event
async def on_ready():
  print(f"✅ Logged in as {client.user}")
  try:
    synced = await client.tree.sync()
    print(f"🔗 Synced {len(synced)} slash command(s).")
  except Exception as e:
    print(f"⚠️ Sync failed: {e}")

# Load all cogs
async def load_cogs():  
  await client.load_extension("cogs.pokemon")
  await client.load_extension("cogs.quotes")

async def main():
  async with client:
    await load_cogs()
    # keep_alive()
    await client.start(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
  import asyncio
  asyncio.run(main())
