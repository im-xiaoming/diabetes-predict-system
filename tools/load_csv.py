import pandas as pd
from django.conf import settings
from pathlib import Path

_cache = {}
DATA_PATH = Path(settings.BASE_DIR) / 'data' / 'data_small.csv'

def _get_data():
    if _cache:
        return _cache['data']
    
    data = pd.read_csv(DATA_PATH)
    data.rename({'SL.NO': 'SL_NO'}, axis=1, inplace=True)
    
    _cache['data'] = data
    return _cache['data']

def load_csv():
    data = _get_data()
    return data


def load_csv_with_columns(columns: list[str]):
    data = _get_data()
    return data[columns]