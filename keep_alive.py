from flask import Flask, jsonify, request
from threading import Thread
from discord_interactions import verify_key_decorator, InteractionType, InteractionResponseType, InteractionResponseFlags
import random
import discord

app = Flask('')

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@app.route('/')
def home():
    return "Hello. I am alive!"

@app.route('/discord/', methods=['POST'])
@verify_key_decorator("164bd71aee6615816c207dc753803172ad77522a64cb6edc14059c492081a3ad")
def interactions():      
  if request.json['type'] == InteractionType.APPLICATION_COMMAND:
    message = ""    
    
    # /ROLL
    if request.json['data']['name'] == "roll":
      newList = request.json['data']['options']

      die = 0
      dNum = 1
      dMod = 0

      for item in newList:
        if (item["name"] == 'die'):
          die = int(item["value"])
        elif (item["name"] == 'number'):
          dNum = item["value"]
        elif (item["name"] == 'modifier'):
          dMod = item["value"]
      
      rolls = []
      rollTotal = 0
      for x in range(0, dNum):
        roll = random.randrange(1, die)
        rolls.append(str(roll))
        rollTotal = rollTotal + roll
      
      rollTotal = rollTotal + dMod

      dieStr = "d" + str(die)
      dModStr = ""
      if (dMod != 0):
        if (dMod >= 0):
          dModStr = "+" + str(dMod)
        else:
          dModStr = str(dMod)
      
      message = f"Rolled {str(dNum)}{dieStr}{dModStr} : "
      if (dNum == 1):
        message = message + f"**{str(rollTotal)}**"
      else: 
        message = message + f"({' + '.join(rolls)}){ dModStr} = **{rollTotal}**"
    
    # /SARCASM
    elif request.json['data']['name'] == "sarcasm":
      lst = []      
      lst.extend(request.json['data']['options'][0]['value'].lower())
      def sarcasm(char):  
        if bool(random.getrandbits(1)):
          char = char.capitalize()
        return char
      newstr = ''.join(list(map(sarcasm, lst)))
      message = "<:sarcasm:918677110997008395> " + newstr
    
    # /JINGLE
    elif request.json['data']['name'] == "jingle":
      message = "https://www.youtube.com/watch?v=3CWJNqyub3o"

    # DEFAULT
    else:
      message = "unknown command name"

      
    return jsonify({
        'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
        'data': {
            'content': message
        }
    })
  elif request.json['type'] == InteractionType.MESSAGE_COMPONENT:
      return jsonify({
          'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
          'data': {
              'content': 'Hello, you interacted with a component.',
              'flags': InteractionResponseFlags.EPHEMERAL
          }
      })

def run():
  app.run(host='0.0.0.0',port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()