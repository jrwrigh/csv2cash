import piecash
from json import load as jsonload
from pathlib import Path
import pandas as pd
from datetime import datetime
from IPython.core.debugger import set_trace


# TODO
# # Add Log file functionality
# # Add date distance tolerance to the internal transactions determination
# # # # ie. do not combine two transactions unless they are within two days of each other

#### INPUTS
# path_to_CSV = Path(r'c:\Somewhere')
path_to_CSV = Path.cwd() / 'transactions_test.csv'
path_to_Book = Path(r'c:\SomewhereElse')
path_to_translationJSON = Path.cwd() / 'translations.json'

#### READ IN DATA

# Open and make translations dictionary
with path_to_translationJSON.open() as translationjson:
    translation = jsonload(translationjson)

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

# Add a checkmark column to the data. If True, then the data has been transferred to the transactions_compiled DataFrame
csv['is_claimed'] = False


def externalTransactions_append(current_transaction, raw_data,
                                transactions_compiled):
    """
    Function to append the external transaction data to the compiled DataFrame
    
    Parameters
    ----------
    current_transaction : DataFrame
        The row that holds the transaction to be compiled
    raw_data : DataFrame
        The df that holds the initial data collected (csv)
    transactions_compiled : DataFrame
        The df that holds the compiled transaction data
    Returns
    -------
    DataFrame
        The transactions_compiled df with the data from current_transaction appended to it
    """

    split1, split2, temp = {}, {}, {}
    temp['description'] = current_transaction['Description']
    temp['post_date'] = current_transaction['Date']
    temp['note'] = str(current_transaction['Notes']
                      ) + current_transaction['Original Description']
    split1['account'] = current_transaction['account_mod']
    split1['value'] = current_transaction['amount_mod']
    split2['account'] = current_transaction['category_mod']
    split2['value'] = -current_transaction['amount_mod']

    temp['split1'] = split1
    temp['split2'] = split2

    transactions_compiled = transactions_compiled.append(
        temp, ignore_index=True)
    raw_data.at[index, 'is_claimed'] = True
    return (transactions_compiled)


def internalTransaction_append(current_transaction, nearest_duplicate, raw_data,
                               transactions_compiled):
    split1, split2, temp = {}, {}, {}
    # set_trace()
    temp[
        'description'] = current_transaction['Description'] + ' ' + nearest_duplicate['Description']
    temp['post_date'] = max(current_transaction['Date'],
                            nearest_duplicate['Date'])
    temp['note'] = str(current_transaction['Notes']
                      ) + current_transaction['Original Description']
    split1['account'] = current_transaction['account_mod']
    split1['value'] = current_transaction['amount_mod']
    split2['account'] = nearest_duplicate['category_mod']
    split2['value'] = nearest_duplicate['amount_mod']

    temp['split1'] = split1
    temp['split2'] = split2

    transactions_compiled = transactions_compiled.append(
        temp, ignore_index=True)
    raw_data.at[index, 'is_claimed'] = True
    raw_data.at[nearest_duplicate['raw_dataindex'], 'is_claimed'] = True
    return(transactions_compiled)


def determine_internalTransactions(current_transaction, raw_data):
    # Find all transactions that have the inverse amount and haven't been transferred
    identical_duplicates = raw_data.loc[
        (raw_data['amount_mod'] == -current_transaction['amount_mod']) &
        (raw_data['is_claimed'] != True)]

    # Note that this assumes that there won't be an identical inverse transaction on the same day
    nearest_duplicate = min(
        identical_duplicates.iterrows(),
        key=lambda x: abs(x[1]['Date'] - current_transaction['Date']))
    
    # Add the index value of the raw_data. This is to mark it in the 'is_claimed' column of raw_data
    raw_dataindex = nearest_duplicate[0]
    nearest_duplicate = nearest_duplicate[1]
    nearest_duplicate['raw_dataindex'] = raw_dataindex
    return (nearest_duplicate)


def is_internalTransaction(current_transaction, raw_data):

    if not current_transaction['duplicatetf']:
        return (False)

    elif current_transaction['duplicatetf']:
        # Find all transactions that have the inverse amount and haven't been transferred
        identical_duplicates = raw_data.loc[
            (raw_data['amount_mod'] == -current_transaction['amount_mod']) &
            (raw_data['is_claimed'] != True)]
        if len(identical_duplicates) != 0:
            return (True)


transactions_compiled = pd.DataFrame(
    columns=['description', 'post_date', 'note', 'split1', 'split2'])

for index, current_transaction in csv.iterrows():
    if csv.at[index, 'is_claimed'] == False:
        split1, split2, temp = {}, {}, {}
        # Separating the external transactions from internal. Duplicate indicates internal transaction
        internalTrans_tf = is_internalTransaction(current_transaction, csv)
        if not internalTrans_tf:
            transactions_compiled = externalTransactions_append(
                current_transaction, csv, transactions_compiled)

        # Work on Internal transactions
        elif internalTrans_tf:
            nearest_duplicate = determine_internalTransactions(
                current_transaction, csv)

            transactions_compiled = internalTransaction_append(
                current_transaction, nearest_duplicate, csv,
                transactions_compiled)
