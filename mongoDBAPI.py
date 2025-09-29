import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

BASEURL = "https://data.mongodb-api.com/app/data-oisse/endpoint/data/beta/action/"
HEADERS = {
  'Content-Type': 'application/json',
  'Access-Control-Request-Headers': '*',
  'api-key': os.environ['mongoDBAPI']
}

DATABASE = os.environ['mongoDBDatabase']
DATA_SOURCE = os.environ['mongoDBUser']

def getPayload(collection=str, filter=dict|None, document=dict|None, update=dict|None): 
  payload = {
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE
  }
  if filter is not None:
    payload["filter"] = filter
  if document is not None:
    payload["document"] = document
  if update is not None:
    payload["update"] = update
  return payload

async def insertMessage(collection, database, datasource, message):  
  document = {
    "id" : message.id,
    "channel" : {
      "id": message.channel.name,
      "name": message.channel.id
    },
    "author" : {
      "id" :  message.author.id,
      "name" : message.author.name      
    },
    "content" : message.content,
    "created_at" : message.created_at       
  }
  
  url = BASEURL + "insertOne"
  payload = json.dumps(getPayload(collection=collection, document=document), indent=4, sort_keys=True, default=str)
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  print (response.text)

async def addReaction(collection, database, datasource, reaction_payload, user):
  url = BASEURL + "findOne"
  payload = json.dumps(getPayload(collection=collection, filter={ "id": reaction_payload.message_id }), indent=4, sort_keys=True, default=str)  
  message = requests.request("POST", url, headers=HEADERS, data=payload).json()
  
  if message['document'] is not None: 
    reaction = {
      "name": reaction_payload.emoji.name,
      "user_name": user.name
    }

    reactions = []
    if ('reactions' not in message['document']):
      reactions = [reaction]
    else: 
      reactions = message['document']['reactions']
      reactions.append(reaction)
    
    payload = json.dumps(getPayload(collection=collection, filter={ "id": reaction_payload.message_id }, update={
        "$set" : {
          "reactions" : reactions 
        }
      }), indent=4, sort_keys=True, default=str)        
    
    url = BASEURL + "updateOne"
    response = requests.request("POST", url, headers=HEADERS, data=payload)
    print (response.text)
  else:
    print("No Message Found")

async def removeReaction(collection, database, datasource, reaction_payload, user):
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "id": reaction_payload.message_id },
  }, indent=4, sort_keys=True, default=str)

  message = requests.request("POST", url, headers=HEADERS, data=payload).json()

  reaction = {
    "name": reaction_payload.emoji.name,
    "user_name": user.name
  }

  if message['document'] is not None and message['document']['reactions'] is not None and reaction in message['document']['reactions']:
    
    reactions = message['document']['reactions']    
    reactions.remove(reaction)

    payload = json.dumps({
      "collection": collection,
      "database": DATABASE,
      "dataSource": DATA_SOURCE,
      "filter": { "id": reaction_payload.message_id },
      "update": {
        "$set" : {
          "reactions" : reactions 
        }
      }
    }, indent=4, sort_keys=True, default=str)

    url = BASEURL + "updateOne"
    response = requests.request("POST", url, headers=HEADERS, data=payload)
    print (response.text)   
  else: 
    print("Cannot remove reaction: Message or Reactions Not found.")
  
async def createPokemon(collection, database, datasource, number, pokemon, message_id, catch_count):  
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
  
  url = BASEURL + "insertOne"
  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "document": document
  }, indent=4, sort_keys=True, default=str)
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  print("inserted Pokemon:", response.text)

async def userHasPokemon(collection, database, datasource, user_id, number):
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "caught_by": user_id, "number": number },
  }, indent=4, sort_keys=True, default=str)
  
  pokemon = requests.request("POST", url, headers=HEADERS, data=payload).json()
  if pokemon['document'] is not None: 
    return True
  else:
    return False


async def getPokemonByMessageID(collection, database, datasource, message_id):  
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "message_id": message_id },
  }, indent=4, sort_keys=True, default=str)
  
  pokemon = requests.request("POST", url, headers=HEADERS, data=payload).json()
  
  if pokemon['document'] is not None: 
    return pokemon['document']
  else:
    print("No Pokemon Found")
    return False

async def addCatchAttempt(collection, database, datasource, message_id, user, pokemon):  
  catch_attempts = pokemon["catch_attempts"]
  catch_attempts.append(str(user.id))

  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "message_id": message_id, "_v": pokemon["_v"] },
    "update": {
      "$set" : {
        "catch_attempts" : catch_attempts,
        "_v": pokemon["_v"] + 1
      }
    }
  }, indent=4, sort_keys=True, default=str)
  url = BASEURL + "updateOne"
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  result = response.json()  
  if result.get("matchedCount", 0) == 1:
    return True
  else:
    return False

async def catchPokemon(collection, database, datasource, message_id, pokemon, user):
  url = BASEURL + "findOne"   
  number = pokemon["number"]
  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "message_id": message_id, "_v": pokemon["_v"] },
    "update": {
      "$set" : {
        "caught" : True,
        "caught_by" : user.id,                      
        "caught_at": datetime.now().isoformat(),
        "_v": pokemon["_v"] + 1
      }
    }
  }, indent=4, sort_keys=True, default=str)
  
  url = BASEURL + "updateOne"
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  result = response.json()
  if result.get("matchedCount", 0) == 1:
    return True
  else:
    return False
  
async def getMyCaughtPokemon(collection, database, datasource, user):
  url = BASEURL + "find"
  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "caught_by": user.id },
  }, indent=4, sort_keys=True, default=str)
  caught_pokemon = requests.request("POST", url, headers=HEADERS, data=payload).json()
  if caught_pokemon['documents'] is not None and len(caught_pokemon['documents']) > 0:
    return caught_pokemon['documents']
  else:
    return False
  
async def getPokemon(collection, database, datasource, user, number):
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "number": number, "caught_by": user.id },
  }, indent=4, sort_keys=True, default=str)
  
  pokemon = requests.request("POST", url, headers=HEADERS, data=payload).json()
  
  if pokemon['document'] is not None and pokemon['document']['caught']: 
    return pokemon['document']
  else:
    print("No Caught Pokemon Found")
    return False
  
async def tradePokemon(collection, database, datasource, user1, user2, pokemon1, pokemon2):
  previous_owners1 = pokemon1["previous_owners"] if "previous_owners" in pokemon1 else []
  if user1.id not in previous_owners1:
    previous_owners1.append(str(user1.id)) 
  previous_owners2 = pokemon2["previous_owners"] if "previous_owners" in pokemon2 else []
  if user2.id not in previous_owners2:
    previous_owners2.append(str(user2.id))
  
  url = BASEURL + "findOne"   
  
  payload1 = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "caught_by": user1.id, "number": pokemon1["number"], "_v": { "$eq": pokemon1["_v"] } if "_v" in pokemon1 else {"$exists": False} },
    "update": {
      "$set" : {
        "caught_by" : user2.id,           
        "traded_at": datetime.now().isoformat(),          
        "previous_owners": previous_owners1,
        "_v": pokemon1["_v"] + 1 if "_v" in pokemon1 else 0
      }
    }
  }, indent=4, sort_keys=True, default=str)
  
  payload2 = json.dumps({
    "collection": collection,
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "caught_by": user2.id, "number": pokemon2["number"], "_v": { "$eq": pokemon2["_v"] } if "_v" in pokemon2 else {"$exists": False} },
    "update": {
      "$set" : {
        "caught_by" : user1.id,           
        "traded_at": datetime.now().isoformat(),     
        "previous_owners": previous_owners2,     
        "_v": pokemon2["_v"] + 1 if "_v" in pokemon2 else 0
      }
    }
  }, indent=4, sort_keys=True, default=str)
  
  url = BASEURL + "updateOne"
  response1 = requests.request("POST", url, headers=HEADERS, data=payload1)
  result1 = response1.json()
  if result1.get("matchedCount", 0) == 0:
    return False
  
  response2 = requests.request("POST", url, headers=HEADERS, data=payload2)
  result2 = response2.json()
  
  if result2.get("matchedCount", 0) == 1:
    return True
  else:
    # Revert the first update if the second fails
    revert_payload1 = json.dumps({
      "collection": collection,
      "database": DATABASE,
      "dataSource": DATA_SOURCE,
      "filter": { "caught_by": user1.id, "number": pokemon1, "_v": { "$eq": pokemon1["_v"] } },
      "update": {
        "$set" : pokemon1
      }
    }, indent=4, sort_keys=True, default=str)
    requests.request("POST", url, headers=HEADERS, data=revert_payload1)
    return False
  
async def createBattle(user1, user2, number_of_pokemon=int, thead_id=int):
  document = {
    # "user1": {
    #   "id": user1.id,
    #   "name": user1.name,
    #   "mention": str(user1.mention)
    # },
    # "user2": {
    #   "id": user2.id,
    #   "name": user2.name,
    #   "mention": str(user1.mention)
    # },
    "number_of_pokemon": number_of_pokemon,
    "active": True,
    "current_round": [
      {        
        "user_id": str(user1.id),
        "pokemon_message_id": None,
        "command": None
      },
      {        
        "user_id": str(user2.id),
        "pokemon_message_id": None,
        "command": None
      },
    ],
    "pokemon": [],    
    "winner": None,
    "created_at": datetime.now().isoformat(),
    "thread_id": str(thead_id),
    "_v": 0
  }
  payload = json.dumps(getPayload(collection="Battles", document=document), indent=4, sort_keys=True, default=str)
  url = BASEURL + "insertOne"
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  if response.status_code == 200:
    return True
  else:
    return False

async def getActiveBattleByThreadID(thread_id):
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": "Battles",
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "thread_id": str(thread_id), "active": True },
  }, indent=4, sort_keys=True, default=str)
  
  battle = requests.request("POST", url, headers=HEADERS, data=payload).json()
  
  if battle['document'] is not None: 
    return battle['document']
  else:
    print("No Active Battle Found")
    return False
  
async def summonPokemonToBattle(battle, pokemon, user):
  pokemon_arr = battle["pokemon"]
  stats_dict = {entry["stat"]["name"]: entry["base_stat"] for entry in pokemon["stats"]}
  moves = [
    entry["move"]["name"]
    for entry in pokemon["moves"]
    for detail in entry["version_group_details"]
    if detail["move_learn_method"]["name"] == "level-up"
    and detail["version_group"]["name"] == "red-blue"
  ]
  pokemon_arr.append({
    "number": pokemon["number"],
    "name": pokemon["name"],
    "image_url": pokemon["image_url"],
    "owner_id": user.id,
    "owner_name": user.name,    
    "status": "active", 
    "current_hp": stats_dict["hp"],
    "stats": stats_dict,  
    "moves": moves[:4]  # Limit to first 4 moves
  })
  # Get base stats from PokeAPI
  
  
  payload = json.dumps({
    "collection": "Battles",
    "database": DATABASE,
    "dataSource": DATA_SOURCE,
    "filter": { "thread_id": battle["thread_id"], "_v": battle["_v"] },
    "update": {
      "$set" : {
        "pokemon" : pokemon_arr,
        "_v": battle["_v"] + 1
      }
    }
  }, indent=4, sort_keys=True, default=str)
  
  url = BASEURL + "updateOne"
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  result = response.json()  
  if result.get("matchedCount", 0) == 1:
    return True
  else:
    return False
  