import numpy as np

def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def smooth_coords(current, previous, factor):
    """
    Apply exponential smoothing.
    current: tuple (x, y)
    previous: tuple (x, y)
    factor: float 0-1 (higher = more smoothing)
    """
    if previous == (0, 0):
        return current
    
    x = previous[0] * factor + current[0] * (1 - factor)
    y = previous[1] * factor + current[1] * (1 - factor)
    return (int(x), int(y))
