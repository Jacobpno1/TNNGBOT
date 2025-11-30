import json


def get_type_emoji_str(name: str) -> str:
    with open("tnngbot/static/pokemon_type.json", "r") as f:
        pokemon_type = json.load(f)
    with open("tnngbot/static/type_emoji.json", "r") as f:
        type_emoji = json.load(f)
    types = pokemon_type.get(name, [])
    emoji_types_str = " ".join([type_emoji.get(t, "") for t in types])
    return emoji_types_str
  