import math
import random

def exponential_probability(current_minutes: int, max_minutes: int, base_probability: float) -> bool:
    """
    Returns True/False based on exponentially increasing probability.
    
    Args:
        current_minutes (int): Minutes elapsed since start.
        max_minutes (int): Minutes elapsed to reach 100% probability.
        base_probability (float): Starting probability at time 0 (0.0 - 1.0).
        
    Returns:
        bool: True with the exponentially increased probability, otherwise False.
    """

    # Clamp time between 0 and max_minutes
    t = max(0, min(current_minutes, max_minutes))

    # If max_minutes is 0, immediate success
    if max_minutes <= 0:
        return True

    # Exponential model:
    # p(t) = base_probability * a^t
    # such that p(max_minutes) = 1
    # => a = (1 / base_probability)^(1/max_minutes)
    if base_probability <= 0:
        a = float('inf')  # instantly ramps to 1
    else:
        a = (1.0 / base_probability) ** (1.0 / max_minutes)

    # Compute probability at time t
    probability = base_probability * (a ** t)

    # Clamp numerically to 1
    probability = min(1.0, probability)

    # Roll RNG
    return random.random() < probability
