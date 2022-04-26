import os
import requests
import json
from dotenv import load_dotenv
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
    
