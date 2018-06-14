import piecash
import json
from pathlib import Path
import pandas as pd
from datetime import datetime
from IPython.core.debugger import set_trace

#### INPUTS
# path_to_CSV = Path(r'c:\Somewhere')
path_to_CSV = Path.cwd() / 'transactions_test.csv'
path_to_Book = Path(r'c:\SomewhereElse')
path_to_translationJSON = Path.cwd() / 'translations.json'

#### READ IN DATA

# Open and make translations dictionary
with path_to_translationJSON.open() as translationjson:
    translation = json.load(translationjson)

csv = pd.read_csv(path_to_CSV)

# book = piecash.open_book(path_to_Book)

#### ACTUAL PROGRAMMING

amount_mod = []
account_mod = []
category_mod = []
for index, row in csv.iterrows():
    # Make list of transaction values with negatives
    if row['Transaction Type'] == 'debit':
        amount_mod.append(-row['Amount'])
    else:
        amount_mod.append(row['Amount'])

    # Make list of translated Accounts
    if row['Account Name'] in translation['Accounts'].keys():
        account_mod.append(translation['Accounts'][row['Account Name']])
    else:
        account_mod.append(None)

    # Make list of translated Categories
    if row['Category'] in translation['Categories'].keys():
        category_mod.append(translation['Categories'][row['Category']])
    else:
        category_mod.append(None)
csv['amount_mod'] = amount_mod
csv['account_mod'] = account_mod
csv['category_mod'] = category_mod

# Convert Date column to datetime object
csv['Date'] = csv['Date'].apply(lambda x: datetime.strptime(x, '%m/%d/%Y'))

# See if any duplicates exist. This is to track transfers between equity accounts (ie. internal transactions)
csv['duplicatetf'] = csv.duplicated(subset='Amount', keep=False)

transactions_compiled = pd.DataFrame(
    columns=['description', 'post_date', 'note', 'split1', 'split2'])
for index, row in csv.iterrows():
    split1, split2, temp = {}, {}, {}
    # Seperating the external transactions from internal. Duplicate indicates internal transaction
    if not row['duplicatetf']:
        temp['description'] = row['Description']
        temp['post_date'] = row['Date']
        temp['note'] = str(row['Notes']) + row['Original Description']
        split1['account'] = row['account_mod']
        split1['value'] = row['amount_mod']
        split2['account'] = row['category_mod']
        split2['value'] = -row['amount_mod']

        temp['split1'] = split1
        temp['split2'] = split2

    # Work on Internal transactions
    else:
        pass
    # set_trace()
    if temp:
        transactions_compiled = transactions_compiled.append(
            temp, ignore_index=True)
