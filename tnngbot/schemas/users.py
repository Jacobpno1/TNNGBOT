#type for a pokemon
from typing import TypedDict, Optional, List
from datetime import datetime
from typing_extensions import NotRequired

class BallCooldowns(TypedDict):    
  greatball: Optional[datetime]
  ultraball: Optional[datetime]

class UserDoc(TypedDict):
  _id: NotRequired[str] 
  user_id: int
  ball_cooldowns: BallCooldowns
  _v: int
    
