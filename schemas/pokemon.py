#type for a pokemon
from typing import TypedDict, Optional, List
from datetime import datetime

class PokemonDoc(TypedDict):
    number: int
    name: str
    image_url: str
    message_id: int
    catch_count: int
    catch_attempts: List[str]
    caught: bool
    caught_by: Optional[int]
    caught_at: Optional[str]
    created_at: str
    _v: int
    
