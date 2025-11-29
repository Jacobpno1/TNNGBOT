from pymongo import MongoClient
from tnngbot.db.game_state import GameStateService
from tnngbot.db.pokemon import PokemonService
from tnngbot.db.messages import MessageService
from tnngbot.db.users import UserService

class MongoDBManager:
    def __init__(self, database: str, uri: str):
        self.uri = uri
        self.client = MongoClient(self.uri)
        self.database = database

        # Attach services
        self.messages = MessageService(self.client, database, "Messages")
        self.pokemon = PokemonService(self.client, database, "Pokemon")
        self.users = UserService(self.client, database, "Users")
        self.game_state = GameStateService(self.client, database, "GameState")
