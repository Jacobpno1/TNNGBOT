import discord
from tnngbot.db.base import BaseService
from tnngbot.schemas.users import UserDoc

class UserService(BaseService):
  
  def upsert_user(self, user: UserDoc):
    _v = user["_v"] if "_v" in user else 0
    user["_v"] += 1
    result = self.col.update_one(
        {"user_id": user["user_id"], "_v": _v},
        {"$set": user},
        upsert=True
    )
    print("Matched:", result.matched_count, "Modified:", result.modified_count)
    return result.matched_count == 1
  
  def get_user(self, user_id: int) -> UserDoc:
    user: UserDoc | None = self.col.find_one({"user_id": user_id})
    if user is None:
      return {
        "user_id": user_id,
        "ball_cooldowns": {
          "greatball": None,
          "ultraball": None
        },
        "_v": 0
      }
    return user