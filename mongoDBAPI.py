import os
from dotenv import load_dotenv
from datetime import datetime
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.environ["MONGO_URI"]  # Example: "mongodb+srv://user:pass@cluster0.mongodb.net"
client = MongoClient(MONGO_URI)

# Utility: get collection reference
def get_collection(database, collection):
    return client[database][collection]


# ---------------- MESSAGES ----------------

async def insertMessage(collection, database, datasource, message):
    col = get_collection(database, collection)
    document = {
        "id": message.id,
        "channel": {
            "id": message.channel.id,
            "name": message.channel.name
        },
        "author": {
            "id": message.author.id,
            "name": message.author.name
        },
        "content": message.content,
        "created_at": message.created_at
    }
    result = col.insert_one(document)
    print("Inserted Message:", result.inserted_id)


async def addReaction(collection, database, datasource, reaction_payload, user):
    col = get_collection(database, collection)
    message = col.find_one({"id": reaction_payload.message_id})

    if message:
        reaction = {"name": reaction_payload.emoji.name, "user_name": user.name}
        reactions = message.get("reactions", [])
        reactions.append(reaction)

        col.update_one(
            {"id": reaction_payload.message_id},
            {"$set": {"reactions": reactions}}
        )
        print("Reaction added")
    else:
        print("No Message Found")


async def removeReaction(collection, database, datasource, reaction_payload, user):
    col = get_collection(database, collection)
    message = col.find_one({"id": reaction_payload.message_id})

    if message and "reactions" in message:
        reaction = {"name": reaction_payload.emoji.name, "user_name": user.name}
        reactions = message["reactions"]

        if reaction in reactions:
            reactions.remove(reaction)
            col.update_one(
                {"id": reaction_payload.message_id},
                {"$set": {"reactions": reactions}}
            )
            print("Reaction removed")
            return
    print("Cannot remove reaction: Message or Reactions Not found.")


# ---------------- POKEMON ----------------

async def createPokemon(collection, database, datasource, number, pokemon, message_id, catch_count):
    col = get_collection(database, collection)
    document = {
        "number": number,
        "name": pokemon['name'],
        "image_url": pokemon['sprites']['front_default'],
        "message_id": message_id,
        "catch_count": catch_count,
        "catch_attempts": [],
        "caught": False,
        "caught_by": None,
        "created_at": datetime.now().isoformat(),
        "_v": 0
    }
    result = col.insert_one(document)
    print("Inserted Pokemon:", result.inserted_id)


async def userHasPokemon(collection, database, datasource, user_id, number):
    col = get_collection(database, collection)
    pokemon = col.find_one({"caught_by": user_id, "number": number})
    return pokemon is not None


async def getPokemonByMessageID(collection, database, datasource, message_id):
    col = get_collection(database, collection)
    pokemon = col.find_one({"message_id": message_id})
    if pokemon:
        return pokemon
    print("No Pokemon Found")
    return False


async def addCatchAttempt(collection, database, datasource, message_id, user, pokemon):
    col = get_collection(database, collection)
    catch_attempts = pokemon["catch_attempts"]
    catch_attempts.append(str(user.id))

    result = col.update_one(
        {"message_id": message_id, "_v": pokemon["_v"]},
        {"$set": {"catch_attempts": catch_attempts, "_v": pokemon["_v"] + 1}}
    )
    return result.matched_count == 1


async def catchPokemon(collection, database, datasource, message_id, pokemon, user):
    col = get_collection(database, collection)
    result = col.update_one(
        {"message_id": message_id, "_v": pokemon["_v"]},
        {"$set": {
            "caught": True,
            "caught_by": user.id,
            "caught_at": datetime.now().isoformat(),
            "_v": pokemon["_v"] + 1
        }}
    )
    return result.matched_count == 1


async def getMyCaughtPokemon(collection, database, datasource, user):
    col = get_collection(database, collection)
    caught_pokemon = list(col.find({"caught_by": user.id}))
    return caught_pokemon if caught_pokemon else False


async def getPokemon(collection, database, datasource, user, number):
    col = get_collection(database, collection)
    pokemon = col.find_one({"number": number, "caught_by": user.id})
    if pokemon and pokemon["caught"]:
        return pokemon
    print("No Caught Pokemon Found")
    return False


async def tradePokemon(collection, database, datasource, user1, user2, pokemon1, pokemon2):
    col = get_collection(database, collection)

    previous_owners1 = pokemon1.get("previous_owners", [])
    if str(user1.id) not in previous_owners1:
        previous_owners1.append(str(user1.id))

    previous_owners2 = pokemon2.get("previous_owners", [])
    if str(user2.id) not in previous_owners2:
        previous_owners2.append(str(user2.id))
        
    pokemone1_v = pokemon1["_v"] if "_v" in pokemon1 else 0
    pokemone2_v = pokemon2["_v"] if "_v" in pokemon2 else 0

    result1 = col.update_one(
        {"caught_by": user1.id, "number": pokemon1["number"], "_v": pokemone1_v},
        {"$set": {
            "caught_by": user2.id,
            "traded_at": datetime.now().isoformat(),
            "previous_owners": previous_owners1,
            "_v": pokemone1_v + 1
        }}
    )
    if result1.matched_count == 0:
        return False

    result2 = col.update_one(
        {"caught_by": user2.id, "number": pokemon2["number"], "_v": pokemone2_v},
        {"$set": {
            "caught_by": user1.id,
            "traded_at": datetime.now().isoformat(),
            "previous_owners": previous_owners2,
            "_v": pokemone2_v + 1
        }}
    )

    if result2.matched_count == 1:
        return True
    else:
        # Rollback first trade if second failed
        col.update_one({"_id": pokemon1["_id"]}, {"$set": pokemon1})
        return False
