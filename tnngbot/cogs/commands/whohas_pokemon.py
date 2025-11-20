import os
from datetime import datetime
from typing import Dict, List, Optional

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

  @app_commands.command(name="whohas", description="Show who owns a specific Pokémon")
  @app_commands.describe(
    pokemon_name="Pokémon name (case-insensitive)",
    pokemon_number="Pokédex number (1-151)",
  )
  async def whohaspokemon(
    self,
    interaction: discord.Interaction,
    pokemon_name: Optional[str] = None,
    pokemon_number: Optional[int] = None,
  ):
    search_name: Optional[str] = None
    if pokemon_name:
      trimmed_name = pokemon_name.strip()
      if not trimmed_name:
        pokemon_name = None
      else:
        if not trimmed_name.isalpha():
          await interaction.response.send_message("Pokémon names must only include letters.", ephemeral=True)
          return
        if len(trimmed_name) > 10:
          await interaction.response.send_message("Pokémon names must be 10 characters or fewer.", ephemeral=True)
          return
        search_name = trimmed_name.lower()

    if pokemon_number is None and search_name is None:
      await interaction.response.send_message("Provide a Pokédex number or Pokémon name.", ephemeral=True)
      return

    if pokemon_number is not None and (pokemon_number < 1 or pokemon_number > 151):
      await interaction.response.send_message("Please provide a Pokédex number between 1 and 151.", ephemeral=True)
      return

    guild = interaction.guild
    client = interaction.client
    local_tz = pytz.timezone("US/Eastern")
    pokemon_title: Optional[str] = None

    def now_eastern_str() -> str:
      now_local = datetime.now(local_tz)
      return now_local.strftime("%m/%d/%y %I:%M %p") + " ET"

    async def fetch_rows():
      nonlocal pokemon_title, pokemon_number
      sort_args = {"sort_by": "caught_at", "ascending": True}
      if pokemon_number is not None:
        fresh = db.pokemon.get_pokemon_by_number(pokemon_number, **sort_args)
      elif search_name is not None:
        fresh = db.pokemon.get_pokemon_by_name(search_name, **sort_args)
      else:
        return [], "Total captures: `0`"
      if not fresh:
        return [], "Total captures: `0`"

      first_entry = fresh[0]
      resolved_name = first_entry.get("name") or (search_name or "Unknown")
      resolved_number = first_entry.get("number")
      if resolved_number is not None:
        try:
          pokemon_number = int(resolved_number)
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
        for item in entries:
          owner_id = item.get("caught_by")
          owner_display = resolve_name(owner_id)
          number = item.get("number", pokemon_number)
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
              "level": level,
              "count": 1,
              "caught_at": caught_at,
            }
          else:
            bucket["count"] += 1
            if caught_at > bucket["caught_at"]:
              bucket["caught_at"] = caught_at
        return list(grouped.values())

      aggregated = aggregate_entries(fresh)

      aggregated.sort(
        key=lambda entry: (
          entry["owner_key"],
          entry["number"],
          -entry["level"],
          entry["name"].lower(),
        )
      )

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

    rows, totals_line = await fetch_rows()
    if not rows:
      await interaction.response.send_message("No one has caught that Pokémon yet!", ephemeral=True)
      return

    header = (
      f"{'User':<15}  {'No.':>3}  {'Name':<10}  {'Lvl':>3}  {'Count':>5}\n"
      + ("-" * 48)
      + "\n"
    )
    last_loaded = now_eastern_str()
    def build_prefix() -> str:
      display_number: str | int = pokemon_number if pokemon_number is not None else "?"
      display_name = pokemon_title or (search_name.capitalize() if search_name else "Unknown")
      return f"**Who Has #{display_number} {display_name}?**\n"

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
          new_rows, new_totals = await self.fetch_rows()
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
          if isinstance(child, discord.ui.Button):
            child.disabled = True
        if self.message is not None:
          try:
            await self.message.edit(view=self)
          except Exception:
            pass

    view = WhoHasPokemonView(
      owner_id=interaction.user.id,
      rows_data=rows,
      fetcher=fetch_rows,
      page_size=15,
      last_loaded_display=last_loaded,
      totals=totals_line,
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
