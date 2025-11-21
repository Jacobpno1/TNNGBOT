from collections import Counter
from datetime import datetime
import os
from typing import List, Optional
import discord
import random
from discord import app_commands 
from discord import Interaction
from discord.ext import commands
from discord.ui import Select
import pytz
from tnngbot.db.manager import MongoDBManager
import requests
import json

# Database setup
MONGO_DBNAME = os.environ['MONGO_DBNAME']
MONGO_URI = os.environ['MONGO_URI']
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)

class PokedexCog(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot
    
  @app_commands.command(name="pokedex", description="List the Pokemon you've caught!")    
  @app_commands.describe(
      sort_by="Choose how to sort your Pokémon",
      direction="Choose ascending or descending order",
      user="User's pokedex to view."
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
    self,
    interaction: discord.Interaction,
    sort_by: str = "number",
    direction: str = "asc",
    duplicates: str = "show",
    user: discord.Member | None = None
  ):
    caught_pokemon = db.pokemon.get_caught_pokemon(
      user if user is not None else interaction.user, sort_by=sort_by, ascending=(direction == "asc")
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
      # header = f"   {'No.':<5} {'Name':<15} {'Caught On'}\n" + ("-" * 49) + "\n"
      # Shrink the table width for mobile users
      header = f"{'No.':<3} {'Name':<11} {'Lvl':<3} {'Caught On'}\n" + ("-" * 40) + "\n"
      local_tz = pytz.timezone("US/Eastern")

      prefix = f"**{user.display_name if user is not None else interaction.user.display_name}'s Pokedex**\n"

      async def fetch_rows(dupe_mode: Optional[str] = None, sort_key: Optional[str] = None, ascending_flag: Optional[bool] = None):
        effective_sort = sort_key or sort_by
        effective_asc = (direction == "asc") if ascending_flag is None else ascending_flag
        fresh = db.pokemon.get_caught_pokemon(
          user if user is not None else interaction.user, sort_by=effective_sort, ascending=effective_asc
        )
        if not fresh:
          return [], "Total Caught: 0, Unique: 0, Duplicates: 0"
        # Compute totals from full list (by name)
        from collections import Counter as _Counter
        name_counts = _Counter(p["name"] for p in fresh)
        total_caught = len(fresh)
        unique_count = len(name_counts.keys())
        duplicates_total = sum(max(0, c - 1) for c in name_counts.values())
        totals_line = f"Total Caught: `{total_caught}`, Unique: `{unique_count}`, Duplicates: `{duplicates_total}`"
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
          formatted_date = dt_local.strftime("%m/%d/%y %I:%M %p")
          # rows_local.append(f"◓  {p['number']:<5} {p['name'].capitalize():<15} {formatted_date} EST\n")
          # Shrink the table width for mobile users
          level = p['level'] if 'level' in p else 1
          rows_local.append(f"{p['number']:<3} {p['name'].capitalize():<11} {level:<3} {formatted_date} ET\n")
        return rows_local, totals_line

      # Initial rows
      rows, totals_line = await fetch_rows()
      # Initial last-loaded timestamp (Eastern)
      def now_eastern_str() -> str:
        now_local = datetime.now(local_tz)
        return now_local.strftime("%m/%d/%y %I:%M %p") + " ET"
      initial_last_loaded = now_eastern_str()

      # Helper to render a single page into a code block
      def render_page(current_rows: List[str], page_index: int, page_size: int, last_loaded: str, totals: str) -> str:
        start = page_index * page_size
        end = start + page_size
        page_rows = current_rows[start:end]
        total_pages = max(1, (len(current_rows) + page_size - 1) // page_size)
        footer = f"\nLast loaded: {last_loaded}\nPage {page_index + 1}/{total_pages}\n"
        return prefix + totals + "\n" + "```" + header + "".join(page_rows) + footer + "```"

      class PokedexView(discord.ui.View):
        def __init__(self, 
                     owner_id: int, 
                     rows_data: List[str], 
                     fetcher, 
                     page_size: int = 15, 
                     page_index: int = 0, 
                     dupe_mode: Optional[str] = None, 
                     sort_key: Optional[str] = None, 
                     direction_key: Optional[str] = None, 
                     last_loaded: str = "", 
                     totals: str = "Total Caught: 0, Unique: 0, Duplicates: 0"                     
                     ):
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
          self.totals_line = totals
          self.total_pages = max(1, (len(self.rows) + page_size - 1) // page_size)
          self.message: discord.Message | None = None
          # Initialize select options if pages are reasonable
          if self.total_pages <= 25 and isinstance(self.children[-1], Select):
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
          await interaction.response.edit_message(content=render_page(self.rows, self.page_index, self.page_size, self.last_loaded, self.totals_line), view=self)

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, custom_id="next")
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
          if not await self._ensure_owner(interaction):
            return
          if self.page_index < (self.total_pages - 1):
            self.page_index += 1
          self._sync_buttons()
          await interaction.response.edit_message(content=render_page(self.rows, self.page_index, self.page_size, self.last_loaded, self.totals_line), view=self)

        @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, custom_id="refresh")
        async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
          if not await self._ensure_owner(interaction):
            return
          # Fetch latest rows and recreate a fresh view preserving the current page index
          try:
            new_rows, new_totals = await self.fetch_rows(self.dupe_mode, self.sort_key, self.direction_key == "asc")
          except Exception:
            new_rows, new_totals = self.rows, self.totals_line
          new_last_loaded = now_eastern_str()
          total_pages_new = max(1, (len(new_rows) + self.page_size - 1) // self.page_size)
          new_index = min(self.page_index, total_pages_new - 1)
          new_view = PokedexView(owner_id=self.owner_id, rows_data=new_rows, fetcher=self.fetch_rows, page_size=self.page_size, page_index=new_index, dupe_mode=self.dupe_mode, sort_key=self.sort_key, direction_key=self.direction_key, last_loaded=new_last_loaded, totals=new_totals)
          await interaction.response.edit_message(content=render_page(new_rows, new_index, self.page_size, new_last_loaded, new_totals), view=new_view)

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
            await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded, self.parent_view.totals_line), view=self.parent_view)

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
              new_rows, new_totals = await self.parent_view.fetch_rows(mode, self.parent_view.sort_key, self.parent_view.direction_key == "asc")
            except Exception:
              new_rows, new_totals = self.parent_view.rows, self.parent_view.totals_line
            self.parent_view.dupe_mode = mode
            self.parent_view.rows = new_rows
            self.parent_view.page_index = 0
            self.parent_view.total_pages = max(1, (len(new_rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
            self.parent_view.last_loaded = now_eastern_str()
            self.parent_view.totals_line = new_totals
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
            await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded, self.parent_view.totals_line), view=self.parent_view)

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
              new_rows, new_totals = await self.parent_view.fetch_rows(self.parent_view.dupe_mode, key, self.parent_view.direction_key == "asc")
            except Exception:
              new_rows, new_totals = self.parent_view.rows, self.parent_view.totals_line
            self.parent_view.sort_key = key
            self.parent_view.rows = new_rows
            self.parent_view.page_index = 0
            self.parent_view.total_pages = max(1, (len(new_rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
            self.parent_view.last_loaded = now_eastern_str()
            self.parent_view.totals_line = new_totals
            # Update defaults
            for opt in self.options:
              opt.default = (opt.value == key)
            # Update page select options
            for child in self.parent_view.children:
              if isinstance(child, discord.ui.Select) and getattr(child, 'placeholder', '') == "Jump to page":
                child.options = [discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(self.parent_view.total_pages)]
            self.parent_view._sync_buttons()
            await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded, self.parent_view.totals_line), view=self.parent_view)

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
              new_rows, new_totals = await self.parent_view.fetch_rows(self.parent_view.dupe_mode, self.parent_view.sort_key, asc_flag)
            except Exception:
              new_rows, new_totals = self.parent_view.rows, self.parent_view.totals_line
            self.parent_view.direction_key = dirv
            self.parent_view.rows = new_rows
            self.parent_view.page_index = 0
            self.parent_view.total_pages = max(1, (len(new_rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
            self.parent_view.last_loaded = now_eastern_str()
            self.parent_view.totals_line = new_totals
            for opt in self.options:
              opt.default = (opt.value == dirv)
            # Update page select options
            for child in self.parent_view.children:
              if isinstance(child, discord.ui.Select) and getattr(child, 'placeholder', '') == "Jump to page":
                child.options = [discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(self.parent_view.total_pages)]
            self.parent_view._sync_buttons()
            await interaction.response.edit_message(content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded, self.parent_view.totals_line), view=self.parent_view)

        async def on_timeout(self) -> None:
          # Disable all controls when view times out
          for child in self.children:
            if isinstance(child, Select):
              child.disabled = True
          if self.message is not None:
            try:
              await self.message.edit(view=self)
            except Exception:
              pass

      view = PokedexView(owner_id=interaction.user.id, rows_data=rows, fetcher=fetch_rows, page_size=15, dupe_mode=duplicates, sort_key=sort_by, direction_key=direction, last_loaded=initial_last_loaded, totals=totals_line)
      await interaction.response.send_message(render_page(rows, view.page_index, view.page_size, initial_last_loaded, totals_line), view=view, ephemeral=True)
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

async def setup(bot: commands.Bot):
  await bot.add_cog(PokedexCog(bot))