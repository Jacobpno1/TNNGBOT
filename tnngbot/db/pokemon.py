from bson import ObjectId
from discord import User, Member
from datetime import datetime
from tnngbot.db.base import BaseService
from tnngbot.schemas.pokemon import PokemonDoc
from typing import NotRequired, Optional, List, Union

class PokemonService(BaseService):
    def create_pokemon(self, number: int, name: str, image_url: str, message_id: str, catch_count: int, level: int) -> None:
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

    def get_pokemon_by_message_id(self, message_id: str) -> Optional[PokemonDoc]:
        pokemon: PokemonDoc | None = self.col.find_one({"message_id": message_id})
        return pokemon

    def add_catch_attempt(self, message_id: str, user: User | Member, pokemon: PokemonDoc, attempt_count:int) -> bool:
        catch_attempts = pokemon["catch_attempts"]
        if attempt_count > 0:
            catch_attempts.extend([str(user.id)] * attempt_count)
        result = self.col.update_one(
            {"message_id": message_id, "_v": pokemon["_v"]},
            {"$set": {"catch_attempts": catch_attempts, "_v": pokemon["_v"] + 1}},
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
                    "_v": pokemon["_v"] + 1,
                }
            },
        )
        return result.matched_count == 1

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

