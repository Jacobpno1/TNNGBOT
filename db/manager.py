from pymongo import MongoClient
from db.pokemon import PokemonService
from db.messages import MessageService

class MongoDBManager:
    def __init__(self, database: str, uri: str):
        self.uri = uri
        self.client = MongoClient(self.uri)
        self.database = database

        # Attach services
        self.messages = MessageService(self.client, database, "Messages")
        self.pokemon = PokemonService(self.client, database, "Pokemon")
