#type for a pokemon
from typing import TypedDict, Optional, List
from datetime import datetime
from typing_extensions import NotRequired

class PokemonDoc(TypedDict):
    _id: NotRequired[str] 
    number: int
    name: str
    level: NotRequired[int]
    image_url: str
    message_id: str
    catch_count: int
    catch_attempts: List[str]
    caught: bool
    caught_by: Optional[int]
    caught_at: Optional[str]
    created_at: str    
    traded_at: NotRequired[str]
    previous_owners: NotRequired[List[str]]
    flees: NotRequired[bool]
    fled: NotRequired[bool]
    _v: int
    
class PokemonCatchResult(TypedDict):
    status: str  # "caught", "escaped", "already_caught", "error"
    pokemon: Optional[PokemonDoc]
    error: NotRequired[str]