import discord
from tnngbot.db.base import BaseService
from tnngbot.schemas.game_state import GameState
from tnngbot.schemas.users import UserDoc
from bson import ObjectId

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
  
  def get_game_state(self) -> GameState | None:
    user: GameState | None = self.col.find_one({})
    return user