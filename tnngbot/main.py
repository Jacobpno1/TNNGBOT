import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

load_dotenv()

intents = discord.Intents.all()
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
  await client.load_extension("tnngbot.cogs.pokemon")  
  await client.load_extension("tnngbot.cogs.commands.whohas_pokemon")
  await client.load_extension("tnngbot.cogs.commands.pokedex")
  await client.load_extension("tnngbot.cogs.commands.fuse_pokemon")
  await client.load_extension("tnngbot.cogs.commands.trade_pokemon")
  
  await client.load_extension("tnngbot.cogs.quotes")

async def _main():
  async with client:
    await load_cogs()
    # keep_alive()
    await client.start(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":  
  asyncio.run(_main())
  
def main():
  asyncio.run(_main())
