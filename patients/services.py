import pandas as pd
import yaml
from django.conf import settings
from pathlib import Path
from tools import AttrDict

TARGET = ['CV', 'PER VAS', 'NEP', 'NEU', 'RET']

def calculate_diabetes_risk(row):
    with open(Path(settings.BASE_DIR) / 'configs' / 'weights.yaml', 'r', encoding='utf-8') as file:
        weights = yaml.safe_load(file)
        
    weights = AttrDict(weights)
    
    score = (row['CV'] * weights.CV + 
             row['PER VAS'] * weights.PER_VAS + 
             row['NEP'] * weights.NEP + 
             row['NEU'] * weights.NEU + 
             row['RET'] * weights.RET)
    
    if score == 0:
        return 'Thấp', 0
    elif 1 <= score <= 2:
        return 'Trung bình', 1
    elif 3 <= score <= 5:
        return 'Cao', 2
    else:
        return 'Rất cao', 3
    
    
def calculate_diabetes_risks(data):
    results = data[TARGET].apply(calculate_diabetes_risk, axis=1, result_type='expand')
    results.columns = ['LV', 'WAR']
    data = pd.concat([data, results], axis=1)
    return data