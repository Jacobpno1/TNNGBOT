from bson import ObjectId
from discord import User, Member
from datetime import datetime
import re
from tnngbot.db.base import BaseService
from tnngbot.schemas.pokemon import PokemonCatchResult, PokemonDoc
from typing import Any, NotRequired, Optional, List, Union, Dict
import time 

MAX_RETRIES = 5
RETRY_BACKOFF = 0.05  # seconds base

class PokemonService(BaseService):
  def create_pokemon(self, number: int, name: str, image_url: str, message_id: str, catch_count: int, level: int) -> PokemonDoc:
    document: PokemonDoc = {
      "number": number,
      "name": name,
      "level": level,
      "image_url": image_url,
      "message_id": message_id,
      "catch_count": catch_count,
      "catch_attempts": [],
      "caught": False,
      "caught_by": None,
      "caught_at": None,
      "created_at": datetime.now().isoformat(),
      "_v": 0,
    }
    result = self.col.insert_one(document)
    print("Inserted Pokemon:", result.inserted_id)
    return document
  
  def update_pokemon(self, pokemon: PokemonDoc):
    _v = pokemon["_v"]
    pokemon["_v"] += 1
    result = self.col.update_one(
      {"message_id": pokemon["message_id"], "_v": _v},
      {"$set": pokemon}
    )
    print("Matched:", result.matched_count, "Modified:", result.modified_count)
    return result.matched_count == 1
  
  def delete_pokemon(self, pokemon: PokemonDoc):
    if "_id" in pokemon:
      result = self.col.delete_one({"_id": ObjectId(pokemon["_id"])})
      return result.deleted_count == 1
    else:
      return False

  def user_has_pokemon(self, user_id: int, number: int):
    pokemon: PokemonDoc | None = self.col.find_one({"caught_by": user_id, "number": number})
    return pokemon is not None

  # def get_pokemon_by_message_id(self, message_id: str) -> Optional[PokemonDoc]:
  #   pokemon: PokemonDoc | None = self.col.find_one({"message_id": message_id})
  #   return pokemon

  # def add_catch_attempt(self, message_id: str, user: User | Member, pokemon: PokemonDoc, attempt_count:int) -> bool:
  #   catch_attempts = pokemon["catch_attempts"]
  #   if attempt_count > 0:
  #   catch_attempts.extend([str(user.id)] * attempt_count)
  #   result = self.col.update_one(
  #   {"message_id": message_id, "_v": pokemon["_v"]},
  #   {"$set": {"catch_attempts": catch_attempts, "_v": pokemon["_v"] + 1}},
  #   )
  #   return result.matched_count == 1
  
  def add_catch_attempt(self, message_id: str, user: User | Member, pokemon: PokemonDoc, attempt_count:int) -> bool:
    if attempt_count <= 0:
      return True

    result = self.col.update_one(
      {"message_id": message_id, "_v": pokemon["_v"]},
      {
        "$push": {"catch_attempts": {"$each": [str(user.id)] * attempt_count}},
        "$inc": {"_v": 1},
      },
    )
    return result.matched_count == 1

  def catch_pokemon(self, message_id: str, pokemon: PokemonDoc, user: User | Member) -> bool:
    result = self.col.update_one(
      {"message_id": message_id, "_v": pokemon["_v"]},
      {
        "$set": {
          "caught": True,
          "caught_by": user.id,
          "caught_at": datetime.now().isoformat(),      
        },
        "$inc": {"_v": 1}
      },
    )
    return result.matched_count == 1

  def get_pokemon_by_id(self, pokemon_id) -> Optional[PokemonDoc]:
    obj_id = ObjectId(pokemon_id) if not isinstance(pokemon_id, ObjectId) else pokemon_id
    pokemon: Optional[PokemonDoc] = self.col.find_one({"_id": obj_id})
    return pokemon

  def get_caught_pokemon(self, user: User | Member, sort_by: str = "number", ascending: bool = True) -> List[PokemonDoc]:
    # Convert boolean into pymongo sort direction
    sort_direction = 1 if ascending else -1
    # Default to number if invalid sort_by passed
    if sort_by not in ["number", "name", "caught_at"]:
      sort_by = "number"
    pokemon_list: List[PokemonDoc] = list(self.col.find({"caught_by": user.id}).sort(sort_by, sort_direction)) or []
    return pokemon_list

  def get_pokemon(self, user: User | Member, number: int) -> PokemonDoc | None:
    pokemon: PokemonDoc | None = self.col.find_one({"number": number, "caught_by": user.id})
    return pokemon if pokemon and pokemon["caught"] else None
  
  def get_pokemon_lvl(self, user: Union[User, Member], number: int, level: int, exclude_id=None) -> Optional[PokemonDoc]:
    # If level == 1, allow matches where level == 1 or level doesn't exist
    if level == 1:
      level_query = {
        "$or": [
          {"level": 1},
          {"level": {"$exists": False}}
        ]
      }
    else:
      level_query = {"level": level}

    query = {
      "number": number,
      "caught_by": user.id,
      **level_query
    }

    if exclude_id is not None:
      query["_id"] = {"$ne": ObjectId(exclude_id)}

    pokemon: Optional[PokemonDoc] = self.col.find_one(query)

    return pokemon if pokemon and pokemon.get("caught", False) else None
  
  def get_pokemon_by_message_id(self, message_id: str) -> Optional[PokemonDoc]:
    return self.col.find_one({"message_id": message_id})

  def get_pokemon_by_number(self, number: int, sort_by: str = "caught_at", ascending: bool = True) -> List[PokemonDoc]:
    valid_fields = {"caught_at", "level", "name", "number"}
    sort_field = sort_by if sort_by in valid_fields else "caught_at"
    sort_direction = 1 if ascending else -1
    query = {"number": number, "caught": True}
    pokemon_list: List[PokemonDoc] = list(self.col.find(query).sort(sort_field, sort_direction)) or []
    return pokemon_list

  def get_pokemon_by_name(self, name: str, sort_by: str = "caught_at", ascending: bool = True, name_is_substring: bool = False) -> List[PokemonDoc]:
    if not name:
      return []
    valid_fields = {"caught_at", "level", "name", "number"}
    sort_field = sort_by if sort_by in valid_fields else "caught_at"
    sort_direction = 1 if ascending else -1
    target_name = f"{re.escape(name)}" if name_is_substring else f"^{re.escape(name)}$"
    pattern = re.compile(target_name, re.IGNORECASE)
    query = {"name": pattern, "caught": True}
    pokemon_list: List[PokemonDoc] = list(self.col.find(query).sort(sort_field, sort_direction)) or []
    return pokemon_list
  
  def add_catch_attempt_atomic(self, message_id: str, user_id: str, attempt_count: int, expected_v: int) -> dict:
    """
    Atomic push of attempt(s) and bump _v. Uses optimistic concurrency via expected_v.
    """
    if attempt_count <= 0:
      return {"status": "no_op"}

    res = self.col.update_one(
      {"message_id": message_id, "_v": expected_v, "caught": {"$ne": True}},
      {
        "$push": {"catch_attempts": {"$each": [user_id] * attempt_count}},
        "$inc": {"_v": 1},
      },
    )
    return {"matched_count": res.matched_count, "modified_count": res.modified_count}
  
  

  def try_catch(self, message_id: str, user_id: int, ball_bonus: int) -> PokemonCatchResult:
    """
    Try to catch the pokemon in an atomic, versioned way.

    Logic:
      - Re-read doc
      - If already caught -> return already_caught + fresh doc
      - If user has already attempted -> return already_attempted + fresh doc
      - Compute whether catchable
        - If not catchable -> attempt to $push catch_attempts and $inc _v (optimistic filter)
        - If catchable -> update doc to set caught=True, caught_by, caught_at and $inc _v (optimistic filter)
      - If update fails due to version mismatch, retry a few times
    """
    for attempt in range(MAX_RETRIES):
      doc = self.get_pokemon_by_message_id(message_id)
      if doc is None:
        return {"status": "error", "error": "not_found", "pokemon": None}

      # give a fresh view to caller
      current_v = doc.get("_v", 0)
      if doc.get("caught", False):
        return {"status": "already_caught", "pokemon": doc}

      # dedupe: if user already tried
      if str(user_id) in doc.get("catch_attempts", []):
        return {"status": "already_attempted", "pokemon": doc}

      # calculate catchable
      current_attempts = len(doc.get("catch_attempts", []))
      catch_count = int(doc.get("catch_count", 0))
      catchable = (current_attempts + ball_bonus) >= catch_count

      if not catchable:
        # Try to record the attempt atomically
        count = max(1, ball_bonus + 1)
        res = self.col.update_one(
          {"message_id": message_id, "_v": current_v, "caught": {"$ne": True}},
          {
            "$push": {"catch_attempts": {"$each": [str(user_id)] * count}},
            "$inc": {"_v": 1},
          },
        )
        if res.matched_count == 1:
          # success; return updated doc
          fresh = self.get_pokemon_by_message_id(message_id)
          return {"status": "attempted", "pokemon": fresh}
        else:
          # version mismatch -> retry
          time.sleep(RETRY_BACKOFF * (attempt + 1))
          continue

      else:
        # catchable -> attempt to mark as caught in one atomic update
        now = datetime.utcnow()
        res = self.col.update_one(
          {"message_id": message_id, "_v": current_v, "caught": {"$ne": True}},
          {
            "$set": {
              "caught": True,
              "caught_by": user_id,
              "caught_at": now,
            },
            "$inc": {"_v": 1},
          },
        )
        if res.matched_count == 1:
          fresh = self.get_pokemon_by_message_id(message_id)
          return {"status": "caught", "pokemon": fresh}
        else:
          time.sleep(RETRY_BACKOFF * (attempt + 1))
          continue

    # if we get here, we exhausted retries
    return {"status": "version_mismatch", "pokemon": self.get_pokemon_by_message_id(message_id)}
