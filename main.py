import piecash
import json
from pathlib import Path
import pandas as pd 


#### INPUTS
path_to_CSV = Path(r'c:\Somewhere')
path_to_Book = Path(r'c:\SomewhereElse')
path_to_translationJSON = Path.cwd() / 'translation.json'

with path_to_translationJSON.open() as translationjson:
    translation = json.load(translationjson)

csv = pd.read_csv(path_to_CSV)

book = piecash.open_book(path_to_Book)

transac_temp = {}
for index, row in csv.iterrows():
    transac_temp['description'] = row['Description']
    transac_temp['post_date'] = row['Date']
