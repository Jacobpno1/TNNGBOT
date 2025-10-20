from dotenv import load_dotenv
from pymongo import MongoClient

class BaseService:
    def __init__(self, client: MongoClient, database: str, collection: str):
        self.client = client
        self.database = database
        self.collection = collection

    @property
    def col(self):
        return self.client[self.database][self.collection]