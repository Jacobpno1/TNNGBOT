import discord
import os
import json
import random
import requests
import mongoDBAPI
from dotenv import load_dotenv
from keep_alive import keep_alive
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import pytz
from collections import Counter
from typing import List

load_dotenv()

intents = discord.Intents.all()
# client = discord.Client(intents=intents)
client = commands.Bot(command_prefix='!', intents=intents);

# for emoji in client.guild.emojis:
#   print(emoji.id)

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))
  print(f"pokemonSpawnRates = {os.environ['pokemonSpawnRate']}")
  print(f"pokemonMaxAttempts = {os.environ['pokemonMaxAttempts']}")
  try:
    synced = await client.tree.sync()
    print(f'Synced {len(synced)} command(s)')
  except Exception as e:
      print(e)

def get_random_quote(file):
    """ Returns random quote from quotes file"""

    with open(file, 'r') as quotes:
        bobbyb_quotes = json.load(quotes)
    
    return random.choice(bobbyb_quotes)

@client.event
async def on_message(message):
  # Do not reply to comments from these users, including itself (client.user)
  blocked_users = [ client.user ]

  if message.author in blocked_users:
    return
  
  if client.user.mentioned_in(message):
    if message.content.lower().find('bobbyb') != -1:
      print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
      msg = get_random_quote('./bobbyBquotes.json').format(message)
      await message.channel.send(str(client.get_emoji(917134295225741313)) + " BobbyB: " + msg)

    if message.content.lower().find('machoman') != -1:
      print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
      msg = get_random_quote('./machoManQuotes.json').format(message)
      await message.channel.send(str(client.get_emoji(1278457600404623401)) + " Macho Man: " + msg)

    if message.content.lower().find('gandalf') != -1:
      print("Replied to message of user '{}' in guild '{}' / channel '{}'".format(message.author, message.guild, message.channel))
      msg = get_random_quote('./gandalfQuotes.json').format(message)
      await message.channel.send(str(client.get_emoji(917135652171161681)) + " Gandalf: " + msg)

  if random.randrange(1, int(os.environ['pokemonSpawnRate'])) == 1:
    await spawnPokemon(message)     

  await mongoDBAPI.insertMessage("Messages", "TNNGBOT", "JacobTEST", message)

async def spawnPokemon(message, pokemon_number=None, catch_count=None):
  if pokemon_number is None:
    pokePool: list[int] = []
    with open('./pokemonPool.json', 'r') as pokePoolJson:
      pokePool = json.load(pokePoolJson)
    poolNo = random.randrange(0, len(pokePool))
    pokeNo = pokePool[poolNo]
  else:
    pokeNo = pokemon_number
  r = requests.get("https://pokeapi.co/api/v2/pokemon/" + str(pokeNo)) 
  pokemon = r.json()
  embed = discord.Embed(title=f"A wild {pokemon['name']} appears! [{pokeNo}]")
  embed.set_thumbnail(url=pokemon['sprites']['front_default'])  
  embed.set_footer(text=f"{pokeNo}")
  channel = discord.utils.get(message.guild.channels, name="tall-grass")
  new_message = await channel.send(embed=embed)
  catch_count = catch_count if catch_count is not None else random.randint(0, int(os.environ['pokemonMaxAttempts']))
  await mongoDBAPI.createPokemon("Pokemon", "TNNGBOT", "JacobTEST", pokeNo, pokemon, str(new_message.id), catch_count)

# @client.command()
async def getmsg(ctx, msgID: int):
  return await ctx.fetch_message(msgID)

def sarcasm(char):  
  if bool(random.getrandbits(1)):
    char = char.capitalize()
  return char

@client.event
async def on_raw_reaction_add(payload):  
  guild = client.get_guild(payload.guild_id)
  channel = guild.get_channel(payload.channel_id)
  message = await channel.fetch_message(payload.message_id)
  user = await client.fetch_user(payload.user_id)

  # if (payload.emoji.name == "ringwhispers"):    
  #   await message.reply(str(client.get_emoji(917135652171161681)) + " Gandalf: Keep it secret, Keep it safe.")
  
  # :bobbyb:917134295225741313
  if (payload.emoji.name == "bobbyb"):    
    await message.reply(str(payload.emoji) + " BobbyB: " + get_random_quote('./bobbyBquotes.json').format(message))    
  
  # :gandalf:917135652171161681
  if (payload.emoji.name == "gandalf"):    
    await message.reply(str(payload.emoji) + " Gandalf: " + get_random_quote('./gandalfQuotes.json').format(message))
    # print(f"gandalf emoji_id: {str(payload.emoji)}")
    
  if (payload.emoji.name == "laszlo"):    
    await message.reply(str(payload.emoji) + " Laszlo: " + get_random_quote('./laszloQuotes.json').format(message))

  if (payload.emoji.name == "machoman"):    
    await message.reply(str(payload.emoji) + " Macho Man: " + get_random_quote('./machoManQuotes.json').format(message))
  
  if (payload.emoji.name == "sarcasm"):
    lst = []
    lst.extend(message.content.lower())
    newstr = ''.join(list(map(sarcasm, lst)))
    await message.reply(newstr + " " + str(payload.emoji))

  if (payload.emoji.name == "pokeball"):    
    await throw_pokeball(payload, user) 

  if (payload.emoji.name == "👍"):    
    if (message.content is not None and message.content.startswith("[TRADE]")):      
      if (str(user.id) == str(message.mentions[0].id)):
        user1 = message.mentions[1]
        user2 = message.mentions[0]
        embed = message.embeds
        user1_pokemon_number = embed[0].title.split('[')[-1].replace(']','')
        user2_pokemon_number = embed[1].title.split('[')[-1].replace(']','')
        user1_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", user1, int(user1_pokemon_number))
        if user1_pokemon is False or user1_pokemon is None:
          await message.edit(content=f"[TRADE FAILED] {user1.mention} does not own a pokemon with number {user1_pokemon_number}.", embeds=[])
          return
        user2_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", user2, int(user2_pokemon_number))
        if user2_pokemon is False or user2_pokemon is None:
          await message.edit(content=f"[TRADE FAILED] {user2.mention} does not own a pokemon with number {user2_pokemon_number}.", embeds=[])
          return 
        result = await mongoDBAPI.tradePokemon("Pokemon", "TNNGBOT", "JacobTEST", user1, user2, user1_pokemon, user2_pokemon)        
        if result == True:
          await message.edit(content=f"[TRADE COMPLETED] {user1.mention} traded <:pokeball:1419845300742520964> {user1_pokemon['name']} [{user1_pokemon['number']}] for {user2.mention}'s <:pokeball:1419845300742520964> {user2_pokemon['name']} [{user2_pokemon['number']}]!",
                             embeds=[],)                   
        else:
          await message.edit(content=f"[TRADE FAILED] Something went wrong with the trade between {user1.mention} and {user2.mention}.", embeds=[])
  
  await mongoDBAPI.addReaction("Messages", "TNNGBOT", "JacobTEST", payload, user)

async def throw_pokeball(payload, user):
    guild = client.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)    
    message = await channel.fetch_message(payload.message_id)      
    if (len(message.embeds) != 0 and message.embeds[0] is not None and message.embeds[0].footer.text is not None):
      # pokeNo = int(message.embeds[0].footer.text)
      try:
        pokemon = await mongoDBAPI.getPokemonByMessageID("Pokemon", "TNNGBOT", "JacobTEST", str(message.id))
        if pokemon is None:
          print("No pokemon found for message ID " + str(message.id))
          return        
        hasUserAttempted = str(user.id) in pokemon["catch_attempts"]
        catchable = len(pokemon["catch_attempts"]) >= pokemon["catch_count"]
      
        if hasUserAttempted is False and pokemon["caught"] is False:
          if catchable is True:
            # Catch the Pokemon
            success = await mongoDBAPI.catchPokemon("Pokemon", "TNNGBOT", "JacobTEST", str(message.id), pokemon, user)
            if success is True:
              message.embeds[0].add_field(name=f"{str(payload.emoji)} Gotcha! {pokemon['name'].capitalize()} was caught by {user.display_name}!", 
                value="Use /pokedex to see all the Pokemon you've caught and /pokemon to summon them!", inline=False)  
              await message.edit(embed=message.embeds[0]) 
            else :
              await throw_pokeball(payload, user);       
          else:
            # Track the failed attempt
            success = await mongoDBAPI.addCatchAttempt("Pokemon", "TNNGBOT", "JacobTEST", str(message.id), user, pokemon)
            if success is True:
              message.embeds[0].add_field(name=f"Oh no {user.display_name}! {pokemon['name'].capitalize()} broke free!", value="", inline=False)
              await message.edit(embed=message.embeds[0])
            else:
              await throw_pokeball(payload, user); 
      except Exception as e:
        print(f"Error processing pokeball throw: {e}")   
        

@client.event
async def on_raw_reaction_remove(payload):      
  user = await client.fetch_user(payload.user_id)
  await mongoDBAPI.removeReaction("Messages", "TNNGBOT", "JacobTEST", payload, user)

# @client.tree.command(name="pokedex", description="List the Pokemon you've caught!")
# async def pokedex(interaction: discord.Interaction):    
#     caught_pokemon = await mongoDBAPI.getMyCaughtPokemon("Pokemon", "TNNGBOT", "JacobTEST", interaction.user)
#     if caught_pokemon:
#       embed = discord.Embed(title=f"{interaction.user.display_name}'s Pokedex")
#       for p in caught_pokemon:
#         embed.add_field(name=f"<:pokeball:1419845300742520964> #{p['number']} {p['name'].capitalize()}", value=f"Caught on {p['created_at']}", inline=False)
#         # embed.set_thumbnail(url=p['image_url'])  
#       await interaction.response.send_message(embed=embed, ephemeral=True)
#     else:
#       await interaction.response.send_message("You haven't caught any Pokemon yet! React to a Pokemon with a <:pokeball:1419845300742520964> to catch it!", ephemeral=True)

@client.tree.command(name="pokedex", description="List the Pokemon you've caught!")
@app_commands.describe(
    sort_by="Choose how to sort your Pokémon",
    direction="Choose ascending or descending order"
)
@app_commands.choices(
    sort_by=[
        app_commands.Choice(name="Number", value="number"),
        app_commands.Choice(name="Name", value="name"),
        app_commands.Choice(name="Caught Date", value="caught_at"),
    ],
    direction=[
        app_commands.Choice(name="Ascending", value="asc"),
        app_commands.Choice(name="Descending", value="desc"),
    ],
    duplicates=[
        app_commands.Choice(name="Show", value="show"),
        app_commands.Choice(name="Hide", value="hide"),
        app_commands.Choice(name="Only", value="only"),
    ]
)
async def pokedex(
  interaction: discord.Interaction,
  sort_by: str = "number",
  direction: str = "asc",
  duplicates: str = "show"
):
  caught_pokemon = await mongoDBAPI.getMyCaughtPokemon(
    "Pokemon", "TNNGBOT", interaction.user, sort_by=sort_by, ascending=(direction == "asc")
  )

  if caught_pokemon:
    if duplicates == "hide":
      seen = set()
      filtered = []
      for p in caught_pokemon:
        if p["number"] not in seen:
          seen.add(p["number"])
          filtered.append(p)
      caught_pokemon = filtered

    elif duplicates == "only":
      # Count occurrences by number
      counts = Counter(p["number"] for p in caught_pokemon)
      caught_pokemon = [p for p in caught_pokemon if counts[p["number"]] > 1]
    # Build paginated view/UI components
    header = f"   {'No.':<5} {'Name':<15} {'Caught On'}\n" + ("-" * 49) + "\n"
    local_tz = pytz.timezone("US/Eastern")

    prefix = f"**{interaction.user.display_name}'s Pokedex**\n"

    async def fetch_rows(dupe_mode: str = None, sort_key: str = None, ascending_flag: bool = None) -> List[str]:
      effective_sort = sort_key or sort_by
      effective_asc = (direction == "asc") if ascending_flag is None else ascending_flag
      fresh = await mongoDBAPI.getMyCaughtPokemon(
        "Pokemon", "TNNGBOT", interaction.user, sort_by=effective_sort, ascending=effective_asc
      )
      if not fresh:
        return []
      # Apply duplicates filter again
      mode = (dupe_mode or duplicates)
      if mode == "hide":
        seen = set()
        filtered = []
        for p in fresh:
          if p["number"] not in seen:
            seen.add(p["number"])
            filtered.append(p)
        fresh = filtered
      elif mode == "only":
        from collections import Counter as _Counter
        counts = _Counter(p["number"] for p in fresh)
        fresh = [p for p in fresh if counts[p["number"]] > 1]

      rows_local: List[str] = []
      for p in fresh:
        dt = datetime.fromisoformat(p["caught_at"]) if "caught_at" in p and p["caught_at"] else datetime.now()
        dt_local = dt.astimezone(local_tz)
        formatted_date = dt_local.strftime("%m/%d/%Y %I:%M %p")
        rows_local.append(f"◓  {p['number']:<5} {p['name'].capitalize():<15} {formatted_date} EST\n")
      return rows_local

    # Initial rows
    rows: List[str] = await fetch_rows()
    # Initial last-loaded timestamp (Eastern)
    def now_eastern_str() -> str:
      now_local = datetime.now(local_tz)
      return now_local.strftime("%m/%d/%Y %I:%M %p") + " EST"
    initial_last_loaded = now_eastern_str()

    # Helper to render a single page into a code block
    def render_page(current_rows: List[str], page_index: int, page_size: int, last_loaded: str) -> str:
      start = page_index * page_size
      end = start + page_size
      page_rows = current_rows[start:end]
      total_pages = max(1, (len(current_rows) + page_size - 1) // page_size)
      footer = f"\nLast loaded: {last_loaded}\nPage {page_index + 1}/{total_pages}\n"
      return prefix + "```" + header + "".join(page_rows) + footer + "```"

    class PokedexView(discord.ui.View):
      def __init__(self, owner_id: int, rows_data: List[str], fetcher, page_size: int = 15, page_index: int = 0, dupe_mode: str = None, sort_key: str = None, direction_key: str = None, last_loaded: str = ""):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.page_size = page_size
        self.page_index = page_index
        self.rows: List[str] = rows_data
        self.fetch_rows = fetcher
        self.dupe_mode = dupe_mode or duplicates
        self.sort_key = sort_key or sort_by
        self.direction_key = direction_key or direction
        self.last_loaded = last_loaded
        self.total_pages = max(1, (len(self.rows) + page_size - 1) // page_size)
        self.message: discord.Message | None = None
        # Initialize select options if pages are reasonable
        if self.total_pages <= 25:
          options = [discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(self.total_pages)]
          self.add_item(self.PageSelect(self))
          self.children[-1].options = options
        # Duplicates select (always available)
        self.add_item(self.DuplicatesSelect(self))
        # Sort and Direction selects (always available)
        self.add_item(self.SortSelect(self))
        self.add_item(self.DirectionSelect(self))
        self._sync_buttons()

      def _sync_buttons(self):
        for child in self.children:
          if isinstance(child, discord.ui.Button):
            if child.custom_id == "prev":
              child.disabled = self.page_index <= 0
            if child.custom_id == "next":
              child.disabled = self.page_index >= (self.total_pages - 1)
            if child.custom_id == "refresh":
              child.disabled = False

      async def _ensure_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
          await interaction.response.send_message("You can't control someone else's Pokedex.", ephemeral=True)
          return False
        return True

      @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, custom_id="prev")
      async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
          return
        if self.page_index > 0:
          self.page_index -= 1
        self._sync_buttons()
        await interaction.response.edit_message(content=render_page(self.rows, self.page_index, self.page_size, self.last_loaded), view=self)

      @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, custom_id="next")
      async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
          return
        if self.page_index < (self.total_pages - 1):
          self.page_index += 1
        self._sync_buttons()
        await interaction.response.edit_message(content=render_page(self.rows, self.page_index, self.page_size, self.last_loaded), view=self)

      @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, custom_id="refresh")
      async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
          return
        # Fetch latest rows and recreate a fresh view preserving the current page index
        try:
          new_rows = await self.fetch_rows(self.dupe_mode, self.sort_key, self.direction_key == "asc")
        except Exception:
          new_rows = self.rows
        new_last_loaded = now_eastern_str()
        total_pages_new = max(1, (len(new_rows) + self.page_size - 1) // self.page_size)
        new_index = min(self.page_index, total_pages_new - 1)
        new_view = PokedexView(owner_id=self.owner_id, rows_data=new_rows, fetcher=self.fetch_rows, page_size=self.page_size, page_index=new_index, dupe_mode=self.dupe_mode, sort_key=self.sort_key, direction_key=self.direction_key, last_loaded=new_last_loaded)
        await interaction.response.edit_message(content=render_page(new_rows, new_index, self.page_size, new_last_loaded), view=new_view)

      class PageSelect(discord.ui.Select):
        def __init__(self, parent_view: 'PokedexView'):
          super().__init__(placeholder="Jump to page")
          self.parent_view = parent_view

        async def callback(self, interaction: discord.Interaction):
          if not await self.parent_view._ensure_owner(interaction):
            return
          try:
            idx = int(self.values[0])
          except Exception:
            idx = 0
          self.parent_view.page_index = min(max(0, idx), self.parent_view.total_pages - 1)
          self.parent_view.last_loaded = now_eastern_str()
          self.parent_view._sync_buttons()
          await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded), view=self.parent_view)

      class DuplicatesSelect(discord.ui.Select):
        def __init__(self, parent_view: 'PokedexView'):
          options = [
            discord.SelectOption(label="Duplicates: Show", value="show"),
            discord.SelectOption(label="Duplicates: Hide", value="hide"),
            discord.SelectOption(label="Duplicates: Only", value="only"),
          ]
          super().__init__(placeholder="Duplicates", min_values=1, max_values=1, options=options)
          self.parent_view = parent_view
          # Pre-select current mode
          for opt in self.options:
            opt.default = (opt.value == self.parent_view.dupe_mode)

        async def callback(self, interaction: discord.Interaction):
          if not await self.parent_view._ensure_owner(interaction):
            return
          mode = self.values[0]
          try:
            new_rows = await self.parent_view.fetch_rows(mode)
          except Exception:
            new_rows = self.parent_view.rows
          self.parent_view.dupe_mode = mode
          self.parent_view.rows = new_rows
          self.parent_view.page_index = 0
          self.parent_view.total_pages = max(1, (len(new_rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
          self.parent_view.last_loaded = now_eastern_str()
          # Rebuild page selector if present and update selection defaults
          for child in self.parent_view.children:
            if isinstance(child, discord.ui.Select) and child is not self:
              # PageSelect - rebuild options
              if hasattr(child, 'placeholder') and child.placeholder == "Jump to page":
                child.options = [discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(self.parent_view.total_pages)]
          # Update defaults on duplicates select
          for opt in self.options:
            opt.default = (opt.value == mode)
          self.parent_view._sync_buttons()
          await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded), view=self.parent_view)

      class SortSelect(discord.ui.Select):
        def __init__(self, parent_view: 'PokedexView'):
          options = [
            discord.SelectOption(label="Sort: Number", value="number"),
            discord.SelectOption(label="Sort: Name", value="name"),
            discord.SelectOption(label="Sort: Caught Date", value="caught_at"),
          ]
          super().__init__(placeholder="Sort By", min_values=1, max_values=1, options=options)
          self.parent_view = parent_view
          for opt in self.options:
            opt.default = (opt.value == self.parent_view.sort_key)

        async def callback(self, interaction: discord.Interaction):
          if not await self.parent_view._ensure_owner(interaction):
            return
          key = self.values[0]
          try:
            new_rows = await self.parent_view.fetch_rows(self.parent_view.dupe_mode, key, self.parent_view.direction_key == "asc")
          except Exception:
            new_rows = self.parent_view.rows
          self.parent_view.sort_key = key
          self.parent_view.rows = new_rows
          self.parent_view.page_index = 0
          self.parent_view.total_pages = max(1, (len(new_rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
          self.parent_view.last_loaded = now_eastern_str()
          # Update defaults
          for opt in self.options:
            opt.default = (opt.value == key)
          # Update page select options
          for child in self.parent_view.children:
            if isinstance(child, discord.ui.Select) and getattr(child, 'placeholder', '') == "Jump to page":
              child.options = [discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(self.parent_view.total_pages)]
          self.parent_view._sync_buttons()
          await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded), view=self.parent_view)

      class DirectionSelect(discord.ui.Select):
        def __init__(self, parent_view: 'PokedexView'):
          options = [
            discord.SelectOption(label="Direction: Ascending", value="asc"),
            discord.SelectOption(label="Direction: Descending", value="desc"),
          ]
          super().__init__(placeholder="Direction", min_values=1, max_values=1, options=options)
          self.parent_view = parent_view
          for opt in self.options:
            opt.default = (opt.value == self.parent_view.direction_key)

        async def callback(self, interaction: discord.Interaction):
          if not await self.parent_view._ensure_owner(interaction):
            return
          dirv = self.values[0]
          asc_flag = (dirv == "asc")
          try:
            new_rows = await self.parent_view.fetch_rows(self.parent_view.dupe_mode, self.parent_view.sort_key, asc_flag)
          except Exception:
            new_rows = self.parent_view.rows
          self.parent_view.direction_key = dirv
          self.parent_view.rows = new_rows
          self.parent_view.page_index = 0
          self.parent_view.total_pages = max(1, (len(new_rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
          self.parent_view.last_loaded = now_eastern_str()
          for opt in self.options:
            opt.default = (opt.value == dirv)
          # Update page select options
          for child in self.parent_view.children:
            if isinstance(child, discord.ui.Select) and getattr(child, 'placeholder', '') == "Jump to page":
              child.options = [discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(self.parent_view.total_pages)]
          self.parent_view._sync_buttons()
          await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded), view=self.parent_view)

      async def on_timeout(self) -> None:
        # Disable all controls when view times out
        for child in self.children:
          child.disabled = True
        if self.message is not None:
          try:
            await self.message.edit(view=self)
          except Exception:
            pass

    view = PokedexView(owner_id=interaction.user.id, rows_data=rows, fetcher=fetch_rows, page_size=15, dupe_mode=duplicates, sort_key=sort_by, direction_key=direction, last_loaded=initial_last_loaded)
    await interaction.response.send_message(render_page(rows, view.page_index, view.page_size, initial_last_loaded), view=view, ephemeral=True)
    try:
      sent = await interaction.original_response()
      view.message = sent
    except Exception:
      pass
  else:
    await interaction.response.send_message(
      "You haven't caught any Pokemon yet! React to a Pokemon with a <:pokeball:1419845300742520964> to catch it!",
      ephemeral=True
    )


@client.tree.command(name="pokemon", description="Summon a Pokemon you've caught!")
@app_commands.describe(pokemon_number="The number of the Pokemon you want to summon (1-151)")
async def pokedex(interaction: discord.Interaction, pokemon_number: str):    
  caught_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", interaction.user, int(pokemon_number))
  if caught_pokemon:
    embed = discord.Embed(title=f"I choose you... <:pokeball:1419845300742520964> {caught_pokemon['name'].capitalize()}!")    
    embed.set_thumbnail(url=caught_pokemon['image_url'])      
    await interaction.response.send_message(embed=embed)
  else:
    await interaction.response.send_message("You haven't caught that pokemon.", ephemeral=True) 

@client.tree.command(name="spawn_pokemon", description="[Admin Only] Spawn a pokemon by number")
@app_commands.describe(pokemon_number="The number of the Pokemon you want to spawn (1-151)", catch_count="How many attempts before catching")
async def spawn_pokemon(interaction: discord.Interaction, pokemon_number: str, catch_count: str):    
  if interaction.user.guild_permissions.administrator:
    await spawnPokemon(interaction, int(pokemon_number), catch_count=int(catch_count))
    await interaction.response.send_message(f"Spawned pokemon number {pokemon_number}!", ephemeral=True) 
  else:
    await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

@client.tree.command(name="trade", description="Trade a Pokemon with another user")
@app_commands.describe(user="User to trade with.", my_pokemon_number="My PokeNumber (1-151)", for_pokemon_number="Their PokeNumber (1-151)")
async def trade_pokemon(interaction: discord.Interaction, user: discord.Member, my_pokemon_number: int, for_pokemon_number: int):    
  i_user = interaction.user
  my_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", i_user, int(my_pokemon_number))
  for_pokemon = await mongoDBAPI.getPokemon("Pokemon", "TNNGBOT", "JacobTEST", user, int(for_pokemon_number))
  if my_pokemon is False or my_pokemon is None:
    await interaction.response.send_message(f"❗ You do not own a pokemon with number {my_pokemon_number}.", ephemeral=True) 
    return
  if for_pokemon is False or for_pokemon is None:
    await interaction.response.send_message(f"❗ {user.display_name} does not own a pokemon with number {for_pokemon_number}.", ephemeral=True) 
    return
  for_pokemon_embed = discord.Embed(title=f"{user.display_name} trades: <:pokeball:1419845300742520964> {for_pokemon['name']} [{for_pokemon['number']}]")
  for_pokemon_embed.set_thumbnail(url=for_pokemon['image_url'])  
  my_pokemon_embed = discord.Embed(title=f"{i_user.display_name} trades: <:pokeball:1419845300742520964> {my_pokemon['name']} [{my_pokemon['number']}]")
  my_pokemon_embed.set_thumbnail(url=my_pokemon['image_url'])  
  
    
  await interaction.response.send_message(f"[TRADE] {user.mention}, {i_user.mention} wants to trade Pokemon! :thumbsup: to accept the trade.", 
                                          embeds=[my_pokemon_embed,for_pokemon_embed], 
                                          ephemeral=False)
  

keep_alive()
client.run(os.environ['TOKEN'])


