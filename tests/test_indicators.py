import pandas as pd
from app.indicators.ta import last_cross

def test_last_cross():
    fast = pd.Series([1,2,3,4])
    slow = pd.Series([2,2,2,3])
    assert last_cross(fast, slow) == 1
    fast = pd.Series([4,3,2,1])
    slow = pd.Series([2,2,2,2])
    assert last_cross(fast, slow) == -1