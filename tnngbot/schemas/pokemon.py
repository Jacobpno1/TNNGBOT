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
    _v: int
    
