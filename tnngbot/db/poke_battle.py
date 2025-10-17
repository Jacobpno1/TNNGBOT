from discord import User, Member
from datetime import datetime
from tnngbot.db.base import BaseService
from tnngbot.schemas.pokemon import PokeBattleDoc, PokemonDoc
from typing import Optional, List

class BattleService(BaseService):
    def create_battle(self, battle: PokeBattleDoc) -> None:        
        result = self.col.insert_one(battle)
        print("Inserted Battle:", result.inserted_id)
        
    def get_battle_by_thread_id(self, thread_id: str) -> Optional[PokeBattleDoc]:
        battle: PokeBattleDoc | None = self.col.find_one({"thread_id": thread_id})
        return battle
    
    def update_battle(self, battle: PokeBattleDoc) -> bool:
        if "_id" not in battle:
            return False
        
        _v = battle["_v"]
        battle["_v"] = _v + 1
        result = self.col.update_one(
            {
                "_id": battle["_id"],
                "_v": _v
            },
            {"$set": battle}
        )
        return result.matched_count == 1