import discord
from tnngbot.db.base import BaseService

class MessageService(BaseService):
    async def insert_message(self, message: discord.Message):
        if isinstance(message.channel, discord.TextChannel):
            channel_name = message.channel.name
        else:
            channel_name = "DM"  # or some placeholder
        document = {
            "id": message.id,
            "channel": {"id": message.channel.id, "name": channel_name},
            "author": {"id": message.author.id, "name": message.author.name},
            "content": message.content,
            "created_at": message.created_at,
        }
        result = self.col.insert_one(document)
        print("Inserted Message:", result.inserted_id)

    async def add_reaction(self, reaction_payload, user):
        message = self.col.find_one({"id": reaction_payload.message_id})
        if message:
            reaction = {"name": reaction_payload.emoji.name, "user_name": user.name}
            reactions = message.get("reactions", [])
            reactions.append(reaction)
            self.col.update_one(
                {"id": reaction_payload.message_id}, {"$set": {"reactions": reactions}}
            )
            print("Reaction added")
        else:
            print("No Message Found")

    def remove_reaction(self, reaction_payload, user):
        message = self.col.find_one({"id": reaction_payload.message_id})
        if message and "reactions" in message:
            reaction = {"name": reaction_payload.emoji.name, "user_name": user.name}
            reactions = message["reactions"]
            if reaction in reactions:
                reactions.remove(reaction)
                self.col.update_one(
                    {"id": reaction_payload.message_id},
                    {"$set": {"reactions": reactions}},
                )
                print("Reaction removed")
                return
        print("Cannot remove reaction: Message or Reactions Not found.")