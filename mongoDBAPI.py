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
  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
    "document": document
  }, indent=4, sort_keys=True, default=str)
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  print (response.text)

async def addReaction(collection, database, datasource, reaction_payload, user):
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
    "filter": { "id": reaction_payload.message_id },
  }, indent=4, sort_keys=True, default=str)
  
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
    
    payload = json.dumps({
      "collection": collection,
      "database": database,
      "dataSource": datasource,
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
    print("No Message Found")

async def removeReaction(collection, database, datasource, reaction_payload, user):
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
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
      "database": database,
      "dataSource": datasource,
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
    "created_at": datetime.now().isoformat()
  }
  
  url = BASEURL + "insertOne"
  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
    "document": document
  }, indent=4, sort_keys=True, default=str)
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  print("inserted Pokemon:", response.text)

async def userHasPokemon(collection, database, datasource, user_id, number):
  url = BASEURL + "findOne"
  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
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
    "database": database,
    "dataSource": datasource,
    "filter": { "message_id": message_id },
  }, indent=4, sort_keys=True, default=str)
  
  pokemon = requests.request("POST", url, headers=HEADERS, data=payload).json()
  
  if pokemon['document'] is not None: 
    return pokemon['document']
  else:
    print("No Pokemon Found")
    return False

async def addCatchAttempt(collection, database, datasource, message_id, user, catch_attempts):  
  catch_attempts.append(str(user.id))

  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
    "filter": { "message_id": message_id},
    "update": {
      "$set" : {
        "catch_attempts" : catch_attempts 
      }
    }
  }, indent=4, sort_keys=True, default=str)
  url = BASEURL + "updateOne"
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  print (response.text)
  return True

async def catchPokemon(collection, database, datasource, message_id, number, user):
  url = BASEURL + "findOne"   
  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
    "filter": { "message_id": message_id, "number": number },
    "update": {
      "$set" : {
        "caught" : True,
        "caught_by" : user.id,                      
        "caught_at": datetime.now().isoformat()
      }
    }
  }, indent=4, sort_keys=True, default=str)
  
  url = BASEURL + "updateOne"
  response = requests.request("POST", url, headers=HEADERS, data=payload)
  print (response.text)
  return True
  
async def getMyCaughtPokemon(collection, database, datasource, user):
  url = BASEURL + "find"
  payload = json.dumps({
    "collection": collection,
    "database": database,
    "dataSource": datasource,
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
    "database": database,
    "dataSource": datasource,
    "filter": { "number": number, "caught_by": user.id },
  }, indent=4, sort_keys=True, default=str)
  
  pokemon = requests.request("POST", url, headers=HEADERS, data=payload).json()
  
  if pokemon['document'] is not None and pokemon['document']['caught']: 
    return pokemon['document']
  else:
    print("No Caught Pokemon Found")
    return False