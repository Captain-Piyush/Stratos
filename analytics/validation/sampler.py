from typing import List

def generate_decision_points(start_lap: int, end_lap: int, interval: int) -> List[int]:
    """
    Generates decision points safely without future knowledge.
    """
    return list(range(start_lap, end_lap + 1, interval))
