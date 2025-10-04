from discord import User, Member
from datetime import datetime
from db.base import BaseService
from schemas.pokemon import PokemonDoc
from typing import Optional, List

class PokemonService(BaseService):
    def create_pokemon(self, number: int, name: str, image_url: str, message_id: str, catch_count: int) -> None:
        document: PokemonDoc = {
            "number": number,
            "name": name,
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

    def user_has_pokemon(self, user_id: int, number: int):
        pokemon: PokemonDoc | None = self.col.find_one({"caught_by": user_id, "number": number})
        return pokemon is not None

    def get_pokemon_by_message_id(self, message_id: str) -> Optional[PokemonDoc]:
        pokemon: PokemonDoc | None = self.col.find_one({"message_id": message_id})
        return pokemon

    def add_catch_attempt(self, message_id: str, user: User | Member, pokemon: PokemonDoc) -> bool:
        catch_attempts = pokemon["catch_attempts"]
        catch_attempts.append(str(user.id))
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

    def get_my_caught_pokemon(self, user: User | Member) -> List[PokemonDoc]:
        pokemon_list: List[PokemonDoc] = list(self.col.find({"caught_by": user.id})) or []
        return pokemon_list

    def get_pokemon(self, user: User | Member, number: int) -> PokemonDoc | None:
        pokemon: PokemonDoc | None = self.col.find_one({"number": number, "caught_by": user.id})
        return pokemon if pokemon and pokemon["caught"] else None

    def trade_pokemon(self, user1: User | Member, user2: User | Member, pokemon1: PokemonDoc, pokemon2: PokemonDoc) -> bool:
        if "_id" not in pokemon1 or "_id" not in pokemon2:
            print("Trade failed: Missing _id in one of the pokemon documents.")
            return False
        prev1 = pokemon1.get("previous_owners", [])
        prev2 = pokemon2.get("previous_owners", [])

        if str(user1.id) not in prev1:
            prev1.append(str(user1.id))
        if str(user2.id) not in prev2:
            prev2.append(str(user2.id))

        result1 = self.col.update_one(
            {"caught_by": user1.id, "number": pokemon1["number"], "_v": pokemon1["_v"]},
            {
                "$set": {
                    "caught_by": user2.id,
                    "traded_at": datetime.now().isoformat(),
                    "previous_owners": prev1,
                    "_v": pokemon1["_v"] + 1,
                }
            },
        )
        if result1.matched_count == 0:
            return False

        result2 = self.col.update_one(
            {"caught_by": user2.id, "number": pokemon2["number"], "_v": pokemon2["_v"]},
            {
                "$set": {
                    "caught_by": user1.id,
                    "traded_at": datetime.now().isoformat(),
                    "previous_owners": prev2,
                    "_v": pokemon2["_v"] + 1,
                }
            },
        )
        if result2.matched_count == 1:
            return True

        # rollback
        self.col.update_one({"_id": pokemon1["_id"]}, {"$set": pokemon1})
        return False