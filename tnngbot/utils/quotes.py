import json
import random

def get_random_quote(file: str) -> str:
  with open(file, "r") as f:
    quotes = json.load(f)
  return random.choice(quotes)