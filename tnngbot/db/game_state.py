import os
from tnngbot.db.base import BaseService
from tnngbot.schemas.game_state import GameState, LastPokemonSpawn
from bson import ObjectId

from tnngbot.schemas.pokemon import PokemonDoc


GAME_STATE_ID = ObjectId(os.environ['gameStateObjectId'])

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