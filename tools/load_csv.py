import pandas as pd
from django.conf import settings
from pathlib import Path

_cache = {}
DATA_PATH = Path(settings.BASE_DIR) / 'data' / 'data_small.csv'

def _get_data():
    if _cache:
        return _cache['data']
    
    data = pd.read_csv(DATA_PATH)
    _cache['data'] = data
    return _cache['data']

def load_csv():
    data = _get_data()
    return data