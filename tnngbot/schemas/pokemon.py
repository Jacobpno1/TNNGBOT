#type for a pokemon
from typing import Literal, TypedDict, Optional, List
from datetime import datetime
from typing_extensions import NotRequired

class PokemonDoc(TypedDict):
    _id: NotRequired[str] 
    number: int
    name: str
    image_url: str
    message_id: str
    catch_count: int
    catch_attempts: List[str]
    caught: bool
    caught_by: Optional[int]
    caught_at: Optional[str]
    created_at: str
    _v: int

class BattlePokemon(TypedDict):    
    id: int
    user_id: int
    number: int
    name: str
    image_url: str
    hp: int
    attack: int
    defense: int
    speed: int
    current_hp: int
    skills: List[str]
    status_effects: List[str]
    fainted: bool
    active: bool

class TurnResult(TypedDict):
    target_pokemon_id: int
    damage: Optional[int]
    status_effect: Optional[str]
    is_critical: Optional[bool]
    missed: Optional[bool]
    new_pokemon_id: Optional[int]
    turn_action: Literal["attack", "switch", "surrender"]
    
    
class BattleTurn(TypedDict):
    round_number: int
    user_id: int
    pokemon_id: int
    skill: NotRequired[str]
    result: NotRequired[TurnResult]    
    timestamp: str
  
class PokeBattleDoc(TypedDict):
    _id: NotRequired[str]
    thread_id: str
    users: List[int]  # List of user IDs    
    battle_pokemon: List[BattlePokemon]  # List of Pokemon numbers 
    current_round: int   
    turns: List[BattleTurn]
    created_at: str
    updated_at: str
    _v: int

