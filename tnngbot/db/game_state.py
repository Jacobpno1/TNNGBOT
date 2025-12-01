from datetime import datetime, timedelta
import os
import time

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
  
  def altar_sacrifice(self, type: str) -> AltarUpdateResult:
    for attempt in range(MAX_RETRIES):
      game_state = self.get_game_state()      
      if not game_state:
        return {"status": "error", "error": "Game state not found."}
      altar_state = game_state.get("pokemon_altar", None)
      
      # initialize altar_state if none
      if not altar_state:
        altar_state = {
          "type_buffs": [],
          "active_until": discord.utils.utcnow(),
          "altar_spawn": False
        }
      
      # if within alter_state active until, add type to type_buffs
      type_buffs = []     
      if not altar_state.get("active_until", None) and altar_state["active_until"] > discord.utils.utcnow():
        type_buffs = altar_state.get("type_buffs", [])   
        #if type buffs length is already 10, do not add more
        if len(type_buffs) >= 10:
          return {"status": "max_buffs_reached"}       
        type_buffs.append(type)          
      else:
        type_buffs = [type]
     
      
      # if type_buffs equals 5 or 10 types, set altar_spawn to True
      altar_spawn = False           
      if len(type_buffs) == 5 or len(type_buffs) == 10:
        altar_spawn = True      
      
      active_until = discord.utils.utcnow() + timedelta(hours=1)                       
      
      res = self.col.update_one(
        {"_id": GAME_STATE_ID, "_v": game_state["_v"]},
        {
          "$set": {
            "pokemon_altar": {
              "$push": {"type_buffs": type},
              "active_until": active_until,            
              "altar_spawn": altar_spawn
            }
          },
          "$inc": {"_v": 1}
        },
      )
      if res.matched_count == 1:
        fresh = self.get_altar_state()
        return {"pokemon_altar": fresh, "status": "updated"}
      else:
        time.sleep(RETRY_BACKOFF * (attempt + 1))
        continue 
    return {"status": "version_mismatch"}
  
  