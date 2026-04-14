import json
import random
from typing import List

def get_tier1_pokemon(poke_number_cap: int) -> List[int]:
    with open("tnngbot/static/pokemon_type_tiers.json", "r") as f:
        pokemon_type_tiers = json.load(f)
    result: List[int] = []
    for type_entry in pokemon_type_tiers.values():
        tier1 = type_entry.get("tier1", [])
        for val in tier1:
            try:
                n = int(val)
            except Exception:
                continue
            if n <= poke_number_cap:
                result.append(n)
    # deduplicate and shuffle for randomness
    result = list(set(result))
    random.shuffle(result)
    return result
