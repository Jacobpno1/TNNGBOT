import os
from datetime import datetime
from typing import Dict, List, Optional
from functools import cmp_to_key

import discord
import pytz
from discord import app_commands
from discord.ext import commands

from tnngbot.db.manager import MongoDBManager

MONGO_DBNAME = os.environ["MONGO_DBNAME"]
MONGO_URI = os.environ["MONGO_URI"]
db = MongoDBManager(MONGO_DBNAME, MONGO_URI)


class WhoHasPokemonCog(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(name="whohas", description="Show who owns a specific Pokémon. Search by name OR number.")
  @app_commands.describe(
    pokemon_name="Pokémon name (case-insensitive)",
    name_match_mode="Whether or not the specified Pokémon name is the exact name or only part of it [default: Exact]",
    pokemon_number="Pokédex number (1-251)",
    sort_by="Choose how to sort the results",
    direction="Choose ascending or descending order",
  )
  @app_commands.choices(
      name_match_mode=[
          app_commands.Choice(name="Partial", value='partial'),
          app_commands.Choice(name="Exact", value='exact'),
      ],
      sort_by=[
          app_commands.Choice(name="User", value="user"),
          app_commands.Choice(name="Pokémon Number", value="number"),
          app_commands.Choice(name="Pokémon Name", value="pokemon"),
          app_commands.Choice(name="Level", value="level"),
          app_commands.Choice(name="Count", value="count"),
      ],
      direction=[
          app_commands.Choice(name="Ascending", value="asc"),
          app_commands.Choice(name="Descending", value="desc"),
      ],
  )
  async def whohaspokemon(
    self,
    interaction: discord.Interaction,
    pokemon_name: Optional[str] = None,
    name_match_mode: Optional[str] = None,
    pokemon_number: Optional[int] = None,
    sort_by: Optional[str] = None,
    direction: str = "asc",
  ):
    search_name: Optional[str] = None
    search_label: Optional[str] = None
    if pokemon_name:
      trimmed_name = pokemon_name.strip()
      if not trimmed_name:
        pokemon_name = None
      else:
        if not all(ch.isalpha() or ch == '-' for ch in trimmed_name):
          await interaction.response.send_message("Pokémon names must only include letters or dashes.", ephemeral=True)
          return
        if len(trimmed_name) > 10:
          await interaction.response.send_message("Pokémon names must be 10 characters or fewer.", ephemeral=True)
          return
        search_label = trimmed_name
        search_name = trimmed_name.lower()

    if pokemon_number is None and search_name is None:
      await interaction.response.send_message("Provide a Pokédex number or Pokémon name.", ephemeral=True)
      return

    if pokemon_number is not None and (pokemon_number < 1 or pokemon_number > 251):
      await interaction.response.send_message("Please provide a Pokédex number between 1 and 251.", ephemeral=True)
      return
    
    if pokemon_number is not None and name_match_mode is not None:
      await interaction.response.send_message("The 'pokemon_number' parameter cannot be used with 'name_match_mode'.", ephemeral=True)
      return

    guild = interaction.guild
    client = interaction.client
    local_tz = pytz.timezone("US/Eastern")
    pokemon_title: Optional[str] = None
    display_number: Optional[int] = pokemon_number
    name_is_substring = True if name_match_mode == 'partial' else False
    valid_sort_keys = {"user", "number", "pokemon", "level", "count"}
    valid_directions = {"asc", "desc"}
    def default_direction_for_sort(key: str) -> str:
      return "desc" if key in {"level", "count"} else "asc"
    active_sort = sort_by if sort_by in valid_sort_keys else "user"
    active_direction = direction if direction in valid_directions else default_direction_for_sort(active_sort)

    def now_eastern_str() -> str:
      now_local = datetime.now(local_tz)
      return now_local.strftime("%m/%d/%y %I:%M %p") + " ET"

    async def fetch_rows(sort_override: Optional[str] = None, direction_override: Optional[str] = None):
      nonlocal pokemon_title, display_number
      selected_sort = sort_override if sort_override in valid_sort_keys else active_sort
      selected_direction = direction_override if direction_override in valid_directions else active_direction
      sort_args = {"sort_by": "caught_at", "ascending": True}
      if pokemon_number is not None:
        fresh = db.pokemon.get_pokemon_by_number(pokemon_number, **sort_args)
      elif search_name is not None:
        fresh = db.pokemon.get_pokemon_by_name(search_name, name_is_substring=name_is_substring, **sort_args)
      else:
        return [], "Total captures: `0`"
      if not fresh:
        return [], "Total captures: `0`"

      first_entry = fresh[0]
      resolved_name = first_entry.get("name") or (search_name or "Unknown")
      resolved_number = first_entry.get("number")
      if resolved_number is not None:
        try:
          display_number = int(resolved_number)
        except (TypeError, ValueError):
          pass
      pokemon_title = resolved_name.capitalize()

      owner_names: Dict[int, str] = {}

      def resolve_name(user_id: Optional[int]) -> str:
        if user_id is None:
          return "Unknown"
        if user_id in owner_names:
          return owner_names[user_id]
        display = None
        if guild is not None:
          member = guild.get_member(user_id)
          if member is not None:
            display = member.display_name
        if display is None and client is not None:
          user_obj = client.get_user(user_id)
          if user_obj is not None:
            display = getattr(user_obj, "display_name", None) or user_obj.name
        if display is None:
          display = f"User {user_id}"
        owner_names[user_id] = display
        return display

      default_name = resolved_name

      def aggregate_entries(entries: List[dict]) -> List[dict]:
        grouped: Dict[tuple, dict] = {}
        fallback_number = display_number if display_number is not None else pokemon_number
        for item in entries:
          owner_id = item.get("caught_by")
          owner_display = resolve_name(owner_id)
          number = item.get("number", fallback_number)
          level = item.get("level", 1)
          poke_name = item.get("name", default_name).capitalize()
          caught_at = item.get("caught_at") or ""
          key = (owner_display.lower(), number, poke_name.lower(), level)
          bucket = grouped.get(key)
          if bucket is None:
            grouped[key] = {
              "owner_name": owner_display,
              "owner_key": owner_display.lower(),
              "owner_id": owner_id,
              "number": number,
              "name": poke_name,
              "name_key": poke_name.lower(),
              "level": level,
              "count": 1,
              "caught_at": caught_at,
            }
          else:
            bucket["count"] += 1
            if caught_at > bucket["caught_at"]:
              bucket["caught_at"] = caught_at
        return list(grouped.values())

      def compare_values(a, b):
        if a < b:
          return -1
        if a > b:
          return 1
        return 0

      def sort_entries(entries: List[dict], key_name: str, direction: str) -> List[dict]:
        ascending = (direction == "asc")

        def cmp_user(a, b):
          cmp_owner = compare_values(a["owner_key"], b["owner_key"])
          if cmp_owner:
            return cmp_owner if ascending else -cmp_owner
          cmp_name = compare_values(a["name_key"], b["name_key"])
          if cmp_name:
            return cmp_name
          cmp_number = compare_values(a["number"], b["number"])
          if cmp_number:
            return cmp_number
          cmp_level = compare_values(b["level"], a["level"])
          if cmp_level:
            return cmp_level
          return compare_values(b["count"], a["count"])

        def cmp_pokemon(a, b):
          cmp_name = compare_values(a["name_key"], b["name_key"])
          if cmp_name:
            return cmp_name if ascending else -cmp_name
          cmp_owner = compare_values(a["owner_key"], b["owner_key"])
          if cmp_owner:
            return cmp_owner
          cmp_level = compare_values(b["level"], a["level"])
          if cmp_level:
            return cmp_level
          return compare_values(b["count"], a["count"])

        def cmp_level(a, b):
          cmp_level_val = compare_values(a["level"], b["level"])
          if cmp_level_val:
            return cmp_level_val if ascending else -cmp_level_val
          cmp_owner = compare_values(a["owner_key"], b["owner_key"])
          if cmp_owner:
            return cmp_owner
          cmp_name = compare_values(a["name_key"], b["name_key"])
          if cmp_name:
            return cmp_name
          return compare_values(b["count"], a["count"])

        def cmp_count(a, b):
          cmp_count_val = compare_values(a["count"], b["count"])
          if cmp_count_val:
            return cmp_count_val if ascending else -cmp_count_val
          cmp_owner = compare_values(a["owner_key"], b["owner_key"])
          if cmp_owner:
            return cmp_owner
          cmp_name = compare_values(a["name_key"], b["name_key"])
          if cmp_name:
            return cmp_name
          return compare_values(b["level"], a["level"])

        def cmp_number(a, b):
          cmp_number_val = compare_values(a["number"], b["number"])
          if cmp_number_val:
            return cmp_number_val if ascending else -cmp_number_val
          cmp_name = compare_values(a["name_key"], b["name_key"])
          if cmp_name:
            return cmp_name
          cmp_owner = compare_values(a["owner_key"], b["owner_key"])
          if cmp_owner:
            return cmp_owner
          return compare_values(b["level"], a["level"])

        comparator = cmp_user
        if key_name == "pokemon":
          comparator = cmp_pokemon
        elif key_name == "level":
          comparator = cmp_level
        elif key_name == "count":
          comparator = cmp_count
        elif key_name == "number":
          comparator = cmp_number
        return sorted(entries, key=cmp_to_key(comparator))

      aggregated = sort_entries(aggregate_entries(fresh), selected_sort, selected_direction)

      rows_local: List[str] = []
      for entry in aggregated:
        owner_full = entry["owner_name"]
        owner = owner_full[:15]
        number = entry["number"]
        raw_name = entry["name"]
        poke_name = raw_name if len(raw_name) <= 10 else f"{raw_name[:7]}..."
        level = entry["level"]
        count = entry["count"]
        rows_local.append(
          f"{owner:<15}  {number:>3}  {poke_name:<10}  {level:>3}  {count:>5}\n"
        )

      totals_line = f"Total captures: `{len(fresh)}`"
      return rows_local, totals_line

    rows, totals_line = await fetch_rows(active_sort, active_direction)
    if not rows:
      if pokemon_number is not None:
        msg = f"No one has caught Pokémon #{pokemon_number}."
      elif search_label:
        safe_label_simple = search_label.replace("`", "")
        if name_is_substring:
          msg = f"No one has caught a Pokémon with '{safe_label_simple}' in its name."
        else:
          msg = f"No one has caught a Pokémon named '{safe_label_simple}'."
      else:
        msg = "No matching Pokémon were found."
      await interaction.response.send_message(msg, ephemeral=True)
      return

    header = (
      f"{'User':<15}  {'No.':>3}  {'Name':<10}  {'Lvl':>3}  {'Count':>5}\n"
      + ("-" * 48)
      + "\n"
    )
    last_loaded = now_eastern_str()

    def build_prefix() -> str:
      if search_label and name_is_substring:
        safe_label = search_label.replace("`", "")
        return f"**Who Has A Pokémon With '{safe_label}' In Its Name?**\n"
      display_number_value: str | int = display_number if display_number is not None else (pokemon_number if pokemon_number is not None else "?")
      display_name = pokemon_title or (search_name.capitalize() if search_name else "Unknown")
      return f"**Who Has #{display_number_value} {display_name}?**\n"

    def render_page(
      current_rows: List[str],
      page_index: int,
      page_size: int,
      last_loaded_display: str,
      totals: str,
    ) -> str:
      start = page_index * page_size
      end = start + page_size
      page_rows = current_rows[start:end]
      total_pages = max(1, (len(current_rows) + page_size - 1) // page_size)
      if not page_rows:
        page_rows = ["(no data)\n"]
      footer = f"\nLast loaded: {last_loaded_display}\nPage {page_index + 1}/{total_pages}\n"
      return build_prefix() + totals + "\n" + "```" + header + "".join(page_rows) + footer + "```"

    class WhoHasPokemonView(discord.ui.View):
      def __init__(
        self,
        owner_id: int,
        rows_data: List[str],
        fetcher,
        page_size: int = 15,
        page_index: int = 0,
        last_loaded_display: str = "",
        totals: str = "Total captures: `0`",
        sort_key: str = "user",
        direction_key: str = "asc",
      ):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.page_size = page_size
        self.page_index = page_index
        self.rows: List[str] = rows_data
        self.fetch_rows = fetcher
        self.last_loaded = last_loaded_display
        self.totals_line = totals
        self.message: Optional[discord.Message] = None
        self.sort_key = sort_key if sort_key in valid_sort_keys else "user"
        default_dir = default_direction_for_sort(self.sort_key)
        self.direction_key = direction_key if direction_key in valid_directions else default_dir
        self.add_item(self.SortSelect(self))
        self.add_item(self.DirectionSelect(self))
        self._sync_buttons()

      def _sync_buttons(self):
        total_pages = max(1, (len(self.rows) + self.page_size - 1) // self.page_size)
        for child in self.children:
          if isinstance(child, discord.ui.Button):
            if child.custom_id == "prev":
              child.disabled = (self.page_index == 0)
            elif child.custom_id == "next":
              child.disabled = (self.page_index >= total_pages - 1)

      async def _ensure_owner(self, action_interaction: discord.Interaction) -> bool:
        if action_interaction.user.id != self.owner_id:
          await action_interaction.response.send_message("You cannot interact with someone else's command.", ephemeral=True)
          return False
        return True

      @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, custom_id="prev")
      async def prev(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(button_interaction):
          return
        if self.page_index > 0:
          self.page_index -= 1
        self._sync_buttons()
        await button_interaction.response.edit_message(
          content=render_page(self.rows, self.page_index, self.page_size, self.last_loaded, self.totals_line),
          view=self,
        )

      @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, custom_id="next")
      async def next(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(button_interaction):
          return
        total_pages = max(1, (len(self.rows) + self.page_size - 1) // self.page_size)
        if self.page_index < total_pages - 1:
          self.page_index += 1
        self._sync_buttons()
        await button_interaction.response.edit_message(
          content=render_page(self.rows, self.page_index, self.page_size, self.last_loaded, self.totals_line),
          view=self,
        )

      @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, custom_id="refresh")
      async def refresh(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(button_interaction):
          return
        try:
          new_rows, new_totals = await self.fetch_rows(self.sort_key, self.direction_key)
        except Exception:
          new_rows, new_totals = self.rows, self.totals_line
        self.rows = new_rows or ["(no data)\n"]
        self.totals_line = new_totals
        self.last_loaded = now_eastern_str()
        total_pages = max(1, (len(self.rows) + self.page_size - 1) // self.page_size)
        self.page_index = min(self.page_index, total_pages - 1)
        self._sync_buttons()
        await button_interaction.response.edit_message(
          content=render_page(self.rows, self.page_index, self.page_size, self.last_loaded, self.totals_line),
          view=self,
        )

      async def on_timeout(self) -> None:
        for child in self.children:
          if isinstance(child, discord.ui.Button) or isinstance(child, discord.ui.Select):
            child.disabled = True
        if self.message is not None:
          try:
            await self.message.edit(view=self)
          except Exception:
            pass

      class SortSelect(discord.ui.Select):
        def __init__(self, parent_view: "WhoHasPokemonView"):
          options = [
            discord.SelectOption(label="Sort: User", value="user"),
            discord.SelectOption(label="Sort: Pokémon Number", value="number"),
            discord.SelectOption(label="Sort: Pokémon Name", value="pokemon"),
            discord.SelectOption(label="Sort: Level", value="level"),
            discord.SelectOption(label="Sort: Count", value="count"),
          ]
          super().__init__(placeholder="Sort By", min_values=1, max_values=1, options=options)
          self.parent_view = parent_view
          for opt in self.options:
            opt.default = (opt.value == self.parent_view.sort_key)

        async def callback(self, interaction: discord.Interaction):
          if not await self.parent_view._ensure_owner(interaction):
            return
          new_key = self.values[0]
          try:
            new_rows, new_totals = await self.parent_view.fetch_rows(new_key, self.parent_view.direction_key)
          except Exception:
            new_rows, new_totals = self.parent_view.rows, self.parent_view.totals_line
          self.parent_view.sort_key = new_key
          self.parent_view.rows = new_rows or ["(no data)\n"]
          self.parent_view.totals_line = new_totals
          self.parent_view.page_index = 0
          total_pages = max(1, (len(self.parent_view.rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
          self.parent_view._sync_buttons()
          self.parent_view.last_loaded = now_eastern_str()
          for opt in self.options:
            opt.default = (opt.value == new_key)
          await interaction.response.edit_message(
            content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded, self.parent_view.totals_line),
            view=self.parent_view,
          )

      class DirectionSelect(discord.ui.Select):
        def __init__(self, parent_view: "WhoHasPokemonView"):
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
          new_direction = self.values[0]
          try:
            new_rows, new_totals = await self.parent_view.fetch_rows(self.parent_view.sort_key, new_direction)
          except Exception:
            new_rows, new_totals = self.parent_view.rows, self.parent_view.totals_line
          self.parent_view.direction_key = new_direction
          self.parent_view.rows = new_rows or ["(no data)\n"]
          self.parent_view.totals_line = new_totals
          self.parent_view.page_index = 0
          self.parent_view.last_loaded = now_eastern_str()
          total_pages = max(1, (len(self.parent_view.rows) + self.parent_view.page_size - 1) // self.parent_view.page_size)
          self.parent_view._sync_buttons()
          for opt in self.options:
            opt.default = (opt.value == new_direction)
          await interaction.response.edit_message(
            content=render_page(self.parent_view.rows, self.parent_view.page_index, self.parent_view.page_size, self.parent_view.last_loaded, self.parent_view.totals_line),
            view=self.parent_view,
          )

    view = WhoHasPokemonView(
      owner_id=interaction.user.id,
      rows_data=rows,
      fetcher=fetch_rows,
      page_size=15,
      last_loaded_display=last_loaded,
      totals=totals_line,
      sort_key=active_sort,
      direction_key=active_direction,
    )
    await interaction.response.send_message(
      render_page(rows, view.page_index, view.page_size, last_loaded, totals_line),
      view=view,
      ephemeral=True,
    )
    try:
      sent = await interaction.original_response()
      view.message = sent
    except Exception:
      pass


async def setup(bot: commands.Bot):
  await bot.add_cog(WhoHasPokemonCog(bot))
