#type for a pokemon
from typing import TypedDict, Optional, List
from datetime import datetime
from typing_extensions import NotRequired
from bson import ObjectId

from tnngbot.schemas.pokemon import PokemonDoc

# class BallCooldowns(TypedDict):    
#   greatball: Optional[datetime]
#   ultraball: Optional[datetime]

class LastPokemonSpawn(TypedDict):
  last_pokemon_spawn_datetime: Optional[datetime]
  pokemon: PokemonDoc

class PokemonAltar(TypedDict):
  type_buffs: List[str]
  active_until: datetime
  altar_spawn: bool  
  
class GameState(TypedDict):
  _id: NotRequired[ObjectId] 
  last_pokemon_spawn: Optional[LastPokemonSpawn]
  fled_pokemon: Optional[List[PokemonDoc]]
  pokemon_altar: Optional[PokemonAltar]
  _v: int
    
class AltarUpdateResult(TypedDict):
    status: str 
    pokemon_altar: NotRequired[PokemonAltar | None]
    error: NotRequired[str]