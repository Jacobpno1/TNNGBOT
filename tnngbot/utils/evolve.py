import random
import requests
import os



def can_pokemon_evolve(old_level: int, new_level: int) -> bool:
  """Return True if leveling up crosses or lands on a multiple of 5."""
  evolve_factor = int(os.environ['EVOLVE_FACTOR'])
  if new_level < old_level:
    return False  # No backward or invalid leveling

  # Check if any multiple of 5 lies between old_level and new_level (inclusive)
  return any(level % evolve_factor == 0 for level in range(old_level + 1, new_level + 1))

def get_next_evolution_number(pokemon_name: str, allow_trade: bool = False) -> int:
  """
  Returns the Pokédex number of the next evolution for the given Pokémon.
  Returns 0 if:
    - There is no next evolution,
    - The evolution does not match the trade evolution filter,
    - The next evolution's Pokédex number > 151,
    - Or the Pokémon itself is not within the first 151.

  Parameters:
    pokemon_name (str): Pokémon name (e.g. "charmander").
    allow_trade (bool): 
      - False → allow only non-trade evolutions (default)
      - True  → allow only trade-based evolutions
  """
  # Step 1: Get Pokémon species info
  species_url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_name.lower()}/"
  species_data = requests.get(species_url).json()

  # Step 2: Check current Pokémon's ID
  pokemon_id = species_data["id"]
  if pokemon_id > 151:
    return 0

  # Step 3: Get evolution chain
  evo_chain_url = species_data["evolution_chain"]["url"]
  evo_data = requests.get(evo_chain_url).json()
  chain = evo_data["chain"]

  # Step 4: Find where this Pokémon appears in the chain
  def find_chain_for(name, chain):
    if chain["species"]["name"] == name:
      return chain
    for evo in chain["evolves_to"]:
      result = find_chain_for(name, evo)
      if result:
        return result
    return None

  current_chain = find_chain_for(pokemon_name.lower(), chain)
  if not current_chain:
    return 0

  # Step 5: If no evolutions, return 0
  if not current_chain["evolves_to"]:
    return 0

  # Step 6: Filter valid evolutions
  valid_evolutions = []
  for evo in current_chain["evolves_to"]:
    evo_details = evo["evolution_details"]

    # Detect if this is a trade evolution
    is_trade = any(detail["trigger"]["name"] == "trade" for detail in evo_details)

    # Respect allow_trade flag
    if allow_trade and not is_trade:
      continue
    if not allow_trade and is_trade:
      continue

    # Get next species info
    evo_species_name = evo["species"]["name"]
    evo_species_url = f"https://pokeapi.co/api/v2/pokemon-species/{evo_species_name}/"
    evo_species_data = requests.get(evo_species_url).json()

    # Skip evolutions beyond Gen 1
    if evo_species_data["id"] > 151:
      continue

    valid_evolutions.append(evo_species_data["id"])

  # Step 7: If no valid evolutions, return 0
  if not valid_evolutions:
    return 0

  # Step 8: Choose one randomly
  return random.choice(valid_evolutions)