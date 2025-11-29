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

class GameState(TypedDict):
  _id: NotRequired[ObjectId] 
  last_pokemon_spawn: Optional[LastPokemonSpawn]
  fleed_pokemon: Optional[List[PokemonDoc]]
  _v: int
    
