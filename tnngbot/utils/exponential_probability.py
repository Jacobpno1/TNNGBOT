import math
import random

def exponential_probability(current_minutes: int,
                            max_minutes: int,
                            base_probability: float,
                            max_probability: float) -> bool:
    """
    Returns True/False based on exponentially increasing probability.

    Args:
        current_minutes (int): Minutes elapsed since start.
        max_minutes (int): Minutes elapsed to reach max_probability.
        base_probability (float): Starting probability at time 0 (0.0 - 1.0).
        max_probability (float): Ending probability at max_minutes (0.0 - 1.0).

    Returns:
        bool: True with the exponentially increased probability, otherwise False.
    """

    # Clamp time
    t = max(0, min(current_minutes, max_minutes))

    # If max_minutes is 0, probability is instantly max_probability
    if max_minutes <= 0:
        return random.random() < max_probability

    # Handle degenerate cases safely
    if base_probability <= 0:
        # Start at zero and ramp exponentially to max_probability
        # Equivalent to instant jump to max_probability when t == max_minutes
        probability = max_probability if t >= max_minutes else 0.0
    else:
        # Exponential base so that p(max_minutes) = max_probability
        a = (max_probability / base_probability) ** (1.0 / max_minutes)

        probability = base_probability * (a ** t)

    # Clamp numeric issues
    probability = max(0.0, min(max_probability, probability))

    return random.random() < probability
