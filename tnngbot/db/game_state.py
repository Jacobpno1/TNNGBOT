from datetime import datetime, timedelta
import os
import time
from datetime import timezone
import discord 
from tnngbot.db.base import BaseService
from tnngbot.schemas.game_state import AltarUpdateResult, GameState, LastPokemonSpawn, PokemonAltar
from bson import ObjectId

from tnngbot.schemas.pokemon import PokemonDoc


GAME_STATE_ID = ObjectId(os.environ['gameStateObjectId'])
MAX_RETRIES = 5
RETRY_BACKOFF = 0.05  # seconds base

class GameStateService(BaseService):
  
  def upsert_game_state(self, game_state: GameState):
    _v = game_state["_v"] if "_v" in game_state else 0
    game_state["_v"] += 1
    game_state["_id"] = game_state.get("_id", ObjectId())
    result = self.col.update_one(
        {"_id": game_state["_id"], "_v": _v},
        {"$set": game_state},
        upsert=True
    )
    print("Matched:", result.matched_count, "Modified:", result.modified_count)
    return result.matched_count == 1
  
  def set_last_pokemon_spawn(self, last_pokemon_spawn: LastPokemonSpawn) -> bool:
    result = self.col.update_one(
      {"_id": GAME_STATE_ID},
      {
        "$set": {
          "last_pokemon_spawn": last_pokemon_spawn
        },
        "$inc": {"_v": 1}
      },
    )
    return result.matched_count == 1
  
  def get_last_pokemon_spawn(self) -> LastPokemonSpawn | None:
    game_state: GameState | None = self.col.find_one({"_id": GAME_STATE_ID})
    if game_state and "last_pokemon_spawn" in game_state:
      return game_state["last_pokemon_spawn"]
    return None
  
  def add_fled_pokemon(self, pokemon: PokemonDoc) -> bool:
    result = self.col.update_one(
      {"_id": GAME_STATE_ID},
      {
        "$push": {"fled_pokemon": pokemon},
        "$inc": {"_v": 1}
      },
    )
    return result.matched_count == 1
  
  #get flex pokemon at index 0 of fled_pokemon list and remove it from the list
  def retrieve_fled_pokemon(self) -> PokemonDoc | None:
    
    game_state: GameState | None = self.col.find_one({"_id": GAME_STATE_ID})
    if game_state and "fled_pokemon" in game_state and len(game_state["fled_pokemon"]) > 0:
      fled_pokemon: PokemonDoc = game_state["fled_pokemon"].pop(0)
      self.col.update_one(
        {"_id": GAME_STATE_ID},
        {
          "$set": {"fled_pokemon": game_state["fled_pokemon"]},
          "$inc": {"_v": 1}
        },
      )
      return fled_pokemon
    return None
  
  def get_game_state(self) -> GameState | None:
    game_state: GameState | None = self.col.find_one({"_id": GAME_STATE_ID})
    return game_state
  
  def get_altar_state(self) -> PokemonAltar | None:
    game_state: GameState | None = self.col.find_one({"_id": GAME_STATE_ID})
    return game_state.get("pokemon_altar", None) if game_state else None
  
  def update_altar_state(self, altar_state: PokemonAltar) -> bool:
    result = self.col.update_one(
      {"_id": GAME_STATE_ID},
      {
        "$set": {
          "pokemon_altar": altar_state
        },
        "$inc": {"_v": 1}
      },
    )
    return result.matched_count == 1
  
  def altar_sacrifice(self, type: str, level: int) -> AltarUpdateResult:
    additions = max(1, level)  # ensure at least 1

    for attempt in range(MAX_RETRIES):
      game_state = self.get_game_state()
      if not game_state:
        return {"status": "error", "error": "Game state not found."}

      altar = game_state.get("pokemon_altar")
      now = discord.utils.utcnow()

      # Initialize altar on first use
      if not altar:
        current_buffs = []
        active_until = now
      else:
        active_until = altar.get("active_until", now)   
        # ensure DB timestamp is timezone-aware before subtracting
        if getattr(active_until, "tzinfo", None) is None:
          active_until = active_until.replace(tzinfo=timezone.utc)     
        current_buffs = altar.get("type_buffs", []) if active_until > now else []
                    
      # Determine how many buffs can be added
      remaining_slots = 10 - len(current_buffs)
      if remaining_slots <= 0 and active_until <= now:
        return {"status": "max_buffs_reached"}

      add_count = min(additions, remaining_slots)
      to_add = [type] * add_count
      new_total = len(current_buffs) + add_count
      old_total = len(current_buffs)

      # Determine altar_spawn
      altar_spawn = old_total < 5 and new_total >= 5 or old_total < 10 and new_total == 10

      # Renew active timer
      new_active_until = now + timedelta(hours=1)

      query = {"_id": GAME_STATE_ID, "_v": game_state["_v"]}
      set_fields = {
        "pokemon_altar.active_until": new_active_until,
        "pokemon_altar.altar_spawn": altar_spawn,
      }
      update_doc = {"$set": set_fields, "$inc": {"_v": 1}}

      # If altar expired → replace buffs, otherwise append
      if active_until <= now:
        set_fields["pokemon_altar.type_buffs"] = to_add
      else:
        if to_add:
          update_doc["$push"] = {"pokemon_altar.type_buffs": {"$each": to_add}}

      res = self.col.update_one(query, update_doc)

      if res.matched_count == 1:
        fresh = self.get_altar_state()
        return {"pokemon_altar": fresh, "status": "updated"}

      time.sleep(RETRY_BACKOFF * (attempt + 1))

    return {"status": "version_mismatch"}
  
  